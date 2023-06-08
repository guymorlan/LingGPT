from .linggpt import app, socketio

def main():
    print("Starting server at http://localhost:8000")
    socketio.run(app, debug=True, port=8000, use_reloader=False)
