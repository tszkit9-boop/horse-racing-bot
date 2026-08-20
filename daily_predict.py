#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Actions 專用 - 每日自動預測並發送結果
"""

import os
import subprocess
import requests
import pandas as pd
import sys

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 缺少 TELEGRAM_TOKEN 或 CHAT_ID 環境變數")
    sys.exit(1)

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=30)
        print(f"📤 發送結果：{response.status_code}")
    except Exception as e:
        print(f"❌ 發送失敗：{e}")

def run_prediction():
    print("🏇 開始執行預測...")
    try:
        result = subprocess.run(
            ['python', 'predict_race_card.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            send_message(f"❌ 預測失敗：\n{result.stderr[:500]}")
            return False
        
        csv_path = 'prediction_result.csv'
        if not os.path.exists(csv_path):
            send_message("❌ 找不到 prediction_result.csv")
            return False
        
        df = pd.read_csv(csv_path)
        top5 = df.head(5)
        message = "🏇 每日賽馬預測 TOP 5\n\n"
        for i, row in top5.iterrows():
            horse = row.get('馬匹編號', '未知')
            draw = row.get('draw', '?')
            win_rate = row.get('預測勝率', 0)
            value = row.get('值博指數', 0)
            message += f"{horse} (檔位 {draw})  勝率 {win_rate:.2%}  值博指數 {value:.3f}\n"
        
        send_message(message)
        send_message("✅ 預測完成！")
        return True
    except Exception as e:
        send_message(f"❌ 預測失敗：{str(e)}")
        return False

if __name__ == '__main__':
    success = run_prediction()
    sys.exit(0 if success else 1)
