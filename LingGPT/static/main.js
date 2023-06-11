const recordButton = document.getElementById("recordButton");
const socket = io();
// Global variable for unique id
let translateRequestId = 0;
let chatgptMessage = null;

function sendMessage() {

		$("#text_form").on("submit", function (event) {
				event.preventDefault();
				let apiKey = $("#apiKey").val();
				let modelName = $("#modelSelector option:selected").val();
				let userText = $("#user_text").val();
				let languageName = $("#languageSelector option:selected").text();
				let character = $("#characterSelector option:selected").text();
				let chatPartnerDescription = $("#chatPartnerDescription").val();
				let maxTokens = $("#tokenCount").val();

				$("#messages").append('<div class="message user">' + userText + '</div>');
				$("#user_text").val('');
				socket.emit('text submitted', {text: userText, apikey: apiKey, model: modelName, language: languageName, character: character, characterDescription: chatPartnerDescription, maxTokens: maxTokens});
				chatgptMessage = $('<div class="message chatgpt"><div class="message-content"></div></div>');
				$("#messages").append(chatgptMessage);
		});

		socket.on('chatresponse', function (msg) {
				if (msg.done) {

						let speakButton = $('<button class="speak-btn"><i class="fa-solid fa-volume-high"></i></button>');

						speakButton.click(function() {
								let parentText = $(this).closest('.message.chatgpt').find('.message-content').text();
								textToSpeech(parentText, $("#languageSelector").val());
						});

						let translateButton = $('<button class="translate-btn"><i class="fa-solid fa-language"></i></button>');
						let buttonsDiv = $('<div class="buttons"></div>').append(speakButton, translateButton);

						let buttonsWrapper = $('<div class="buttons-wrapper"></div>').append(buttonsDiv); // New wrapper div

						chatgptMessage.append(buttonsWrapper);

						chatgptMessage.append('<div class="message-content"></div>');
						chatgptMessage.find(".message-content").attr("data-original", chatgptMessage.find(".message-content").text());
						chatgptMessage = null;
				} else {
						let formattedData = msg.data.replace(/\n/g, '<br>'); // Replace '\n' with '<br>'
						chatgptMessage.find(".message-content").append(formattedData);
				}
				$("#messages").scrollTop($("#messages")[0].scrollHeight);
		});

		// Add the following event listener
		$("#user_text").on("keydown", function (event) {
				if (event.key === 'Enter' && !event.shiftKey) {
						event.preventDefault();
						$("#text_form").submit();
				}
		});
}

sendMessage();
const transcript = document.getElementById("user_text");

let isRecording = false;
let recognition;

if (window.SpeechRecognition || window.webkitSpeechRecognition) {
		const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
		recognition = new SpeechRecognition();
		recognition.continuous = true;
		recognition.interimResults = false;
		// set according to value of languageSelector selector element 

		languageSelector.addEventListener("change", (event) => {
				const selectedLocale = event.target.value;
				recognition.lang = selectedLocale;
				console.log("Selected language locale:", selectedLocale);

		});

		recognition.onresult = (event) => {
				let current = event.resultIndex;
				let transcriptText = event.results[current][0].transcript;
				transcript.value += transcriptText;
		};

		recognition.onerror = (event) => {
				console.error("Error occurred in recognition: " + event.error);
		};
} else {
		console.warn("SpeechRecognition is not supported in this browser.");
		recordButton.disabled = true;
}

recordButton.addEventListener("click", () => {
		if (!isRecording) {
				recognition.start();
				recordButton.innerHTML = '<i class="fa-solid fa-stop"></i>';
				// change background color to red
				recordButton.style.backgroundColor = "red";
		} else {
				recognition.stop();
				recordButton.innerHTML = "<i class='fa-solid fa-microphone'></i>";
				recordButton.style.backgroundColor = "#4CAF50";
		}
		isRecording = !isRecording;
});


$("#getSuggestionButton").on("click", function () {

		btn = $(this);
		btn.html('<i class="fa-solid fa-spinner fa-spin-pulse"></i>');
		const socket = io();

		let apiKey = $("#apiKey").val();
		let modelName = $("#modelSelector option:selected").val();
		let languageName = $("#languageSelector option:selected").text();

		socket.emit('get suggestion', {apikey: apiKey, model: modelName, language: languageName});
		socket.on('suggestresponse', function (msg) {
				if (!msg.done) {
						let formattedData = msg.data.replace(/\n/g, ' ');  // Replace '\n' with ' '
						// append formattedData to text area with id user_text
						$('#user_text')[0].value += formattedData;

				} else {
						btn.html('<i class="fa-regular fa-lightbulb"></i>');
				}
		});
});

$("#messages").on("click", ".translate-btn", function () {
		translateMessage(this);
});


function textToSpeech(text, language) {
		const socket = io();
		socket.emit('get tts', {text: text, language: language});
		socket.on('ttsresponse', function(msg) {
				let audio = new Audio('/tts/' + msg.data);
				audio.play();
		});
}



function translateMessage(btn) {
	const messageDiv = $(btn).closest('.message.chatgpt')[0];
	const originalText = messageDiv.querySelector(".message-content").getAttribute("data-original");
	const translation = btn.getAttribute("data-translation");
	let thisRequestId = ++translateRequestId;

	if (!translation) {
		// Request the translation from the server
		const socket = io();
		socket.emit("translate to english", {text: originalText, requestId: thisRequestId});
		btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin-pulse"></i>';

		// Listen for the response from the server
		socket.on("translationresponse", function (msg) {
			// Only use the translation if it matches the most recent request
			if (msg.requestId === thisRequestId) {
				// Store the translation in the button's data- attribute
				btn.setAttribute("data-translation", msg.data);

				// Swap the message text with the translation
				messageDiv.querySelector(".message-content").innerText = msg.data;

				// Change the button text
				btn.innerHTML = '<i class="fa-solid fa-rotate-left"></i>';
			}
		});
	} else {
		// Swap the message text and the button text
		if (btn.innerHTML === '<i class="fa-solid fa-rotate-left"></i>') {
			messageDiv.querySelector(".message-content").innerText = originalText;
			btn.innerHTML = '<i class="fa-solid fa-language"></i>';
		} else {
			messageDiv.querySelector(".message-content").innerText = translation;
			btn.innerHTML = '<i class="fa-solid fa-rotate-left"></i>';
		}
	}
}

function getSelectedText() {
		var sel = rangy.getSelection();
		if (sel.rangeCount) {
				var range = sel.getRangeAt(0).cloneRange();
				range.expand("word");
				sel.setSingleRange(range);  // This line makes the selection visually snap to word boundaries
				return range.toString();
		}
		return '';
}

// obsolete
function getWordAtPoint(evt) {
		var range = rangy.createRange();
		range.selectNode(document.elementFromPoint(evt.clientX, evt.clientY));
		range.expand("word");
		return range.toString();
}

// should handle RTL text better
function getArabicWordAtPoint(evt) {
		var range = rangy.createRange();
		var node = document.elementFromPoint(evt.clientX, evt.clientY);
		range.selectNode(node);
		if (node.nodeType == Node.TEXT_NODE) {
				var text = node.textContent;
				var rect = node.getBoundingClientRect();
				var xPercent = (evt.clientX - rect.left) / rect.width;
				var clickPos = Math.round(text.length * xPercent);
				var wordStart = text.lastIndexOf(' ', clickPos - 1) + 1;
				var wordEnd = text.indexOf(' ', clickPos);
				if (wordEnd == -1) {
						wordEnd = text.length;
				}
				range.setStart(node, wordStart);
				range.setEnd(node, wordEnd);
		}
		return range.toString();
}


document.addEventListener('mouseup', function(e) {
		if (e.target.closest(".message") && !e.target.closest(".span-btn") && !e.target.closest(".translate-btn")) {
				var text = getSelectedText();
				if (!text) {
						text = getArabicWordAtPoint(e);
				}
				
				// if text is selected and its length is more than 3 characters
				if (text && text.length > 1) {
						// send text to server for translation
						socket.emit('translate word to english', {text: text});

						socket.on('hovertranslationresponse', function(msg) {
								// Show the hovering box with the translation
								var hoveringBox = document.getElementById('hoveringBox');
								var translationText = document.getElementById('translationText');
								translationText.innerText = msg.data;
								hoveringBox.style.display = 'block';
								hoveringBox.style.left = e.pageX + 'px';
								hoveringBox.style.top = e.pageY + 'px';
						});
				} else {
						// Hide the hovering box if no text is selected
						document.getElementById('hoveringBox').style.display = 'none';
				}
		}
});

const hoveringBox = document.getElementById('hoveringBox');
hoveringBox.addEventListener('mouseleave', function() {
		this.style.display = 'none';
});


function resetChatPartnerDescription() {
    document.getElementById("chatPartnerDescription").value = "";
}

