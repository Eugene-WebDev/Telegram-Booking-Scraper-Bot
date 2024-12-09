from flask import Flask
import threading

# Create a Flask application
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Function to run the server
def run_server():
    app.run(host="0.0.0.0", port=8080)

# Function to start the server in a thread
def keep_alive():
    server = threading.Thread(target=run_server)
    server.daemon = True
    server.start()
