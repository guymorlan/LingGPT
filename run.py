from LingGPT.app import app, socketio

def main():
    socketio.run(app, debug=True, port=8000)

if __name__ == '__main__':
    main()
