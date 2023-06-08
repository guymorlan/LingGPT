from LingGPT import app

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8000)
