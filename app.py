import os
import threading
from flask import Flask
from telegram_bot import main as bot_main

app = Flask(__name__)

@app.route('/')
def home():
    return "賽馬預測 Bot 運行中！"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    bot_main()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
