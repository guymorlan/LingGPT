from .linggpt import app, socketio

def main():
    socketio.run(app, debug=True, port=8000)
    print("Server running on port 8000")
    print("Open http://localhost:8000 in your browser")

