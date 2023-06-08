from .linggpt import app, socketio

def main():
    socketio.run(app, debug=True, port=8000)
