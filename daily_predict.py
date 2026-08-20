#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Actions 專用 - 每日自動預測並發送結果（除錯版）
"""

import os
import subprocess
import requests
import pandas as pd
import sys
import traceback

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("缺少 TELEGRAM_TOKEN 或 CHAT_ID 環境變數")
    sys.exit(1)

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={'chat_id': CHAT_ID, 'text': text}, timeout=30)
        print(f"發送結果：{response.status_code}")
    except Exception as e:
        print(f"發送失敗：{e}")

def run_prediction():
    print("開始執行預測...")
    send_message("🏇 開始執行預測...")
    
    try:
        print(f"當前工作目錄: {os.getcwd()}")
        print(f"目錄內容: {os.listdir('.')}")
        
        # 執行預測腳本，捕捉所有輸出
        result = subprocess.run(
            ['python', 'predict_race_card.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"返回碼: {result.returncode}")
        print(f"stdout: {result.stdout}")
        
        if result.stderr:
            print(f"stderr: {result.stderr}")
        
        if result.returncode != 0:
            error_msg = f"預測失敗 (exit code {result.returncode})\n"
            if result.stderr:
                error_msg += result.stderr[:500]
            else:
                error_msg += result.stdout[-500:]
            send_message(f"❌ {error_msg}")
            return False
        
        # 讀取結果
        csv_path = 'prediction_result.csv'
        if not os.path.exists(csv_path):
            send_message("找不到 prediction_result.csv")
            return False
        
        df = pd.read_csv(csv_path)
        if df.empty:
            send_message("預測結果為空")
            return False
        
        # 製作 TOP 5 訊息
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
        
    except subprocess.TimeoutExpired:
        send_message("預測超時（超過 5 分鐘）")
        return False
    except Exception as e:
        send_message(f"預測失敗：{str(e)}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_prediction()
    sys.exit(0 if success else 1)
