import os
import openai
import gtts
import googletrans
from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
import re
import tiktoken
import tempfile

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")


# Maintain the conversation history in memory
conversation = []
translator = googletrans.Translator()

langid2google = {"es-ES": "es-ES",
                 "fr-FR": "fr",
                 "it-IT": "it",
                 "pt-PT": "pt-PT",
                 "de-DE": "de", 
                 "sv-SE": "sv",
                 "nl-NL": "nl",
                 "zh-CN": "zh-CN",
                 "ja-JP": "ja",
                 "ar-SA": "ar"}

characterDict = {"Friend": "a friend named Ralph, 25 years old, a university student studying art and computer science, likes hiking and playing video games",
                 "Grocery store clerk": "a grocery store clerk named Maria, 30 years old, a mother of two, likes to cook and watch movies",
                 "Storyteller": "a storyteller named John, 40 years old, a father of three, likes to read and play the guitar",
                 "History Professor": "a history professor named Dr. Smith, 50 years old, a father of two, likes to play tennis and watch movies",
                 "Painter": "a painter named Sarah, 35 years old, a mother of one, likes to paint and play the piano"}



@app.route('/tts/<path:path>')
def send_js(path):
    """Serve a file from the temporary directory."""
    temp_dir = pathlib.Path(tempfile.gettempdir())
    return send_from_directory(temp_dir, path)


@app.route('/')
def index():
    """Serve the index page."""
    return render_template('index.html')


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    # from https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print("Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def prune_messages(messages, max_tokens, model="gpt-3.5-turbo"):
    """Prunes messages to fit within the max_tokens limit. 
    Removes messages from the second to last until the total number of tokens is less than max_tokens."""


    while num_tokens_from_messages(messages, model) > max_tokens:
        messages.pop(1)

    return messages


def perform_request_with_streaming(messages, apikey, model, max_tokens, temperature, socket, name="chatresponse"):
    """Performs a request to the OpenAI API with streaming enabled."""

    if openai.api_key != apikey:
        openai.api_key = apikey

    msg = []
    for resp in openai.ChatCompletion.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    ):
        if 'content' in resp.choices[0]['delta']:
            token = resp.choices[0]['delta']['content']
            socket.emit(name, {"data": token, "done": False})
            msg.append(token)
            socketio.sleep(0)

    msg = ''.join(msg)
    if msg:
        conversation.append({'role': 'assistant', 'content': msg})

    socket.emit(name, {"done": True})


@socketio.on('text submitted')
def handle_text_submitted(json):
    """Respond to a text submission from the user."""

    user_text = json['text']
    api_key = json['apikey']
    model = json['model']
    language = json['language']
    character = json['character']
    characterDescription = json['characterDescription']
    max_tokens = int(json['maxTokens'])

    temperature = 0.0

    if characterDescription:
        used_char = characterDescription
    else:
        used_char = characterDict[character]

    prompt = f"You are a helpful language practice assistant for {language}, respond by roleplaying as {used_char}. If there are any grammar mistakes or if you have any important suggestions for improvement on the user's language use, fix them using English explanations inside square brackets. Any corrections or suggestions should appear only at the end of your entire response to the user. Your correction must be preceded by two linebreaks. Do not break character in your response. Avoid unnecessary comments or compliments to the user. Always roleplay and never identify as an 'assistant'."

    # Get the conversation history for this session, or start a new one
    global conversation
    if len(conversation) == 0:
        conversation = [{'role': 'system', 'content': prompt}]
    else:
        conversation[0] = {'role': 'system', 'content': prompt}

    # Append the user's message to the conversation
    conversation.append({'role': 'user', 'content': user_text})

    # Prune the conversation if necessary
    conversation = prune_messages(conversation, max_tokens, model)

    # Perform the request  
    perform_request_with_streaming(conversation, api_key, model, 300, temperature, socketio)


@socketio.on('get suggestion')
def handle_get_suggestion(json):
    """Suggest a response to the user."""

    api_key = json['apikey']
    model = json['model']
    language = json['language']

    temperature = 0.7

    # only suggest if there is an existing conversation
    if len(conversation) != 0:
        suggest_conversation = conversation.copy()
        suggest_conversation[0]['content'] = f"You are a helpful language learning assistant for {language}, suggest to the user a possible response they may write to continue the conversation."
        suggest_conversation.append({'role': 'user', 'content': 'Suggest to the user a possible response to continue the conversation.'})

        perform_request_with_streaming(suggest_conversation, api_key, model, 300, temperature, socketio, name = "suggestresponse")


@socketio.on('get tts')
def handle_get_tts(json):
    """Get a text-to-speech audio file for the user's text."""

    text = json['text']
    language = json['language']
    language = langid2google[language]

    # remove any text in square brackets
    text = re.sub(r'\[.*?\]', '', text)

    tts = gtts.gTTS(text=text, lang=language)
    filename = f"{language}_{hash(text)}.mp3"
    file_path = os.path.join(tempfile.gettempdir(), filename)
    tts.save(file_path)
    socketio.emit("ttsresponse", {"data": filename})


@socketio.on('translate word to english')
def handle_translate_word_to_english(json):
    """Translate a word to English."""

    user_text = json['text']
    result = translator.translate(user_text, dest='en')
    translation = result.text
    socketio.emit("hovertranslationresponse", {"data": translation, "done": True})


@socketio.on('translate to english')
def handle_translate_to_english(json):
    """ Translate a message to English. """

    user_text = json['text']
    request_id = json['requestId']

    # replace whitespace after dots, question marks, exclamation marks with a newline
    user_text = user_text.replace('. ', '.\n').replace('? ', '?\n').replace('! ', '!\n')

    # Use Google Translate for translation
    result = translator.translate(user_text, dest='en')

    translation = result.text
    # replace newlines with whitespace
    translation = translation.replace('\n', ' ')

    # Send the translation back to the client
    socketio.emit("translationresponse", {"data": translation, "requestId": request_id, "done": True})


if __name__ == '__main__':
    print("Starting server at http://localhost:8000")
    socketio.run(app, debug=True, port=8000, use_reloader=False)

