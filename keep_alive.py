from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "I am alive! Bot is working."

def run():
    # Render требует, чтобы мы слушали порт 0.0.0.0
    # И порт, который выдает сам Render (обычно 10000)
    port = int(os.environ.get("PORT", 10000)) 
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Error starting server: {e}")

def keep_alive():
    t = Thread(target=run)
    t.start()
