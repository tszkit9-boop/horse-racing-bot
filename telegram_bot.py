#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Bot - 賽馬預測系統（本地運行版）
"""

import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
from logging.handlers import RotatingFileHandler
import requests
import subprocess
import pandas as pd
import time
import json
from datetime import datetime

# ============================================================
# 🔐 設定 Logging
# ============================================================
LOG_FILE = 'bot.log'
LOG_MAX_SIZE = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

logger = logging.getLogger('TelegramBot')
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_SIZE,
    backupCount=LOG_BACKUP_COUNT,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ============================================================
# 🔐 設定（請填你嘅資料）
# ============================================================
TOKEN = '8848079617:AAGaWmM9IJa7raA2qBoErlRYPuddGlYHaJA'          # 去 @BotFather 換新 Token
ADMIN_ID = '7988559873'          # 你嘅 Telegram ID

if TOKEN == '你的Bot Token':
    logger.error("❌ 請先設定 TELEGRAM_TOKEN！")
    sys.exit(1)

logger.info("=" * 50)
logger.info("🚀 Bot 啟動中...")
logger.info(f"📅 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info("=" * 50)

# ============================================================
# 📨 發送訊息
# ============================================================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
        logger.info(f"📤 發送訊息到 {chat_id}：{text[:30]}...")
        return response
    except Exception as e:
        logger.error(f"❌ 發送失敗：{e}")
        return None

# ============================================================
# 🏇 預測指令
# ============================================================
def cmd_predict(chat_id):
    logger.info(f"🏇 用戶 {chat_id} 觸發預測")
    send_message(chat_id, "🏇 開始執行預測...")
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ['python', 'predict_race_card.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
            return
        df = pd.read_csv('prediction_result.csv')
        top5 = df.head(5)
        msg = "🏇 預測結果 TOP 5\n\n"
        for i, row in top5.iterrows():
            horse = row.get('馬匹編號', '未知')
            draw = row.get('draw', '?')
            win_rate = row.get('預測勝率', 0)
            value = row.get('值博指數', 0)
            msg += f"{horse} (檔位 {draw})  勝率 {win_rate:.2%}  值博指數 {value:.3f}\n"
        send_message(chat_id, msg)
        send_message(chat_id, "✅ 預測完成！")
        logger.info(f"✅ 預測完成，已發送結果給 {chat_id}")
    except Exception as e:
        logger.error(f"❌ 預測失敗：{e}")
        send_message(chat_id, f"❌ 預測失敗：{str(e)}")

# ============================================================
# 📨 訊息處理（簡化版，只支援 /預測 和 /help）
# ============================================================
def handle_message(chat_id, text):
    logger.info(f"📩 收到訊息：{text} 來自 {chat_id}")
    if text in ['/predict', '/預測']:
        cmd_predict(chat_id)
    elif text in ['/help', '/幫助']:
        send_message(chat_id, "🤖 可用指令：/預測 或 /help")
    else:
        send_message(chat_id, "🤖 請使用 /預測 或 /help")

# ============================================================
# 🚀 主程式
# ============================================================
def main():
    send_message(ADMIN_ID, "✅ Bot 已啟動！")
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            response = requests.get(
                url,
                params={'offset': last_update_id + 1, 'timeout': 30},
                timeout=35
            )
            data = response.json()
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    last_update_id = update['update_id']
                    if 'message' in update and 'text' in update['message']:
                        chat_id = str(update['message']['chat']['id'])
                        text = update['message']['text'].strip()
                        handle_message(chat_id, text)
        except Exception as e:
            logger.error(f"❌ 監聽錯誤：{e}")
            time.sleep(5)
        time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Bot 已停止")