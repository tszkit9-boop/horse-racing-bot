#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Bot - 賽馬預測完整版（支援所有即時指令）
"""

import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import subprocess
import pandas as pd
import time
import json
from datetime import datetime

# ============================================================
# 🔐 設定（從環境變數讀取）
# ============================================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID', '7988559873')

if not TOKEN:
    print("❌ 缺少 TELEGRAM_TOKEN 環境變數")
    sys.exit(1)

# ============================================================
# 📨 發送訊息
# ============================================================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        print(f"發送失敗：{e}")

# ============================================================
# 🔧 執行指令
# ============================================================
def run_script(script_name):
    """執行 Python 腳本，回傳輸出"""
    os.chdir('/home/runner/work/horse-racing-bot/horse-racing-bot')  # Render 路徑
    my_env = os.environ.copy()
    my_env['PYTHONIOENCODING'] = 'utf-8'
    my_env['PYTHONUTF8'] = '1'
    
    result = subprocess.run(
        ['python', script_name],
        capture_output=True,
        text=True,
        timeout=300,
        env=my_env
    )
    return result

# ============================================================
# 🏇 所有指令功能
# ============================================================

# 1. 預測
def cmd_predict(chat_id):
    send_message(chat_id, "🏇 開始執行預測...")
    result = run_script('predict_race_card.py')
    if result.returncode != 0:
        send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
        return
    # 讀取並發送結果
    try:
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
    except Exception as e:
        send_message(chat_id, f"❌ 讀取結果失敗：{str(e)}")

# 2. 更新排位表
def cmd_update(chat_id):
    send_message(chat_id, "🔄 正在更新排位表...")
    result = run_script('scrape_racecard_with_odds.py')
    if result.returncode != 0:
        send_message(chat_id, f"❌ 更新失敗：\n{result.stderr[:500]}")
        return
    send_message(chat_id, "✅ 排位表已更新！")
    # 自動執行預測
    cmd_predict(chat_id)

# 3. 今日賽程
def cmd_schedule(chat_id):
    send_message(chat_id, "📅 正在查詢今日賽程...")
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv')
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
        today = datetime.now().date()
        today_races = df[df['race_date'].dt.date == today]
        if today_races.empty:
            send_message(chat_id, "📅 今日沒有賽事")
        else:
            courses = today_races['race_course'].unique()
            msg = f"📅 今日賽程 ({today})\n\n"
            for course in courses:
                races = today_races[today_races['race_course'] == course]['race_no'].unique()
                msg += f"🏟️ {course}: 第 {', '.join(map(str, sorted(races)))} 場\n"
            send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# 4. 馬匹查詢
def cmd_horse(chat_id, horse_id):
    send_message(chat_id, f"🔍 正在查詢馬匹 {horse_id}...")
    try:
        df = pd.read_csv('ALL_DATA_MERGED.csv')
        horse_data = df[df['horse_id'] == horse_id]
        if horse_data.empty:
            send_message(chat_id, f"❌ 找不到馬匹 {horse_id}")
            return
        total = len(horse_data)
        wins = (horse_data['finish_position'] == 1).sum() if 'finish_position' in horse_data.columns else 0
        win_rate = wins / total * 100 if total > 0 else 0
        recent = horse_data.sort_values('race_date').tail(3)['finish_position'].tolist()
        msg = f"🐴 馬匹 {horse_id}\n\n總出賽：{total}\n頭馬：{wins}\n勝率：{win_rate:.1f}%\n近3場名次：{', '.join(map(str, recent))}"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# 5. 騎師查詢
def cmd_jockey(chat_id, jockey_name):
    send_message(chat_id, f"🔍 正在查詢騎師 {jockey_name}...")
    try:
        df = pd.read_csv('ALL_DATA_MERGED.csv')
        jockey_data = df[df['jockey'] == jockey_name]
        if jockey_data.empty:
            send_message(chat_id, f"❌ 找不到騎師 {jockey_name}")
            return
        total = len(jockey_data)
        wins = (jockey_data['finish_position'] == 1).sum() if 'finish_position' in jockey_data.columns else 0
        win_rate = wins / total * 100 if total > 0 else 0
        msg = f"🏇 騎師 {jockey_name}\n\n總出賽：{total}\n頭馬：{wins}\n勝率：{win_rate:.1f}%"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# 6. 幫助
def cmd_help(chat_id):
    help_text = """
🤖 賽馬預測 Bot 指令列表

🏇 預測類：
/預測 - 預測最新賽日第9場

📊 查詢類：
/賽程 - 顯示今日賽程
/馬匹 G123 - 查詢馬匹歷史戰績
/騎師 潘頓 - 查詢騎師近績

🔄 更新類：
/更新 - 更新排位表 + 自動預測

❓ 其他：
/help - 顯示呢個幫助
    """
    send_message(chat_id, help_text)

# ============================================================
# 📨 訊息處理
# ============================================================
def handle_message(chat_id, text):
    if text in ['/predict', '/預測']:
        cmd_predict(chat_id)
    elif text in ['/update', '/更新']:
        cmd_update(chat_id)
    elif text in ['/schedule', '/賽程']:
        cmd_schedule(chat_id)
    elif text.startswith('/horse') or text.startswith('/馬匹'):
        parts = text.split()
        if len(parts) > 1:
            cmd_horse(chat_id, parts[1])
        else:
            send_message(chat_id, "請輸入馬匹編號，例如：/馬匹 G123")
    elif text.startswith('/jockey') or text.startswith('/騎師'):
        parts = text.split()
        if len(parts) > 1:
            cmd_jockey(chat_id, ' '.join(parts[1:]))
        else:
            send_message(chat_id, "請輸入騎師名，例如：/騎師 潘頓")
    elif text in ['/help', '/幫助']:
        cmd_help(chat_id)
    else:
        # 非指令訊息，可以忽略或提示
        pass

# ============================================================
# 🚀 主程式
# ============================================================
def main():
    send_message(CHAT_ID, "✅ Bot 已啟動！傳送 /help 查看所有指令")
    last_update_id = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            response = requests.get(url, params={'offset': last_update_id + 1, 'timeout': 30}, timeout=35)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    last_update_id = update['update_id']
                    if 'message' in update and 'text' in update['message']:
                        chat_id = str(update['message']['chat']['id'])
                        text = update['message']['text'].strip()
                        print(f"📩 收到訊息：{text} 來自 {chat_id}")
                        handle_message(chat_id, text)
        except Exception as e:
            print(f"監聽錯誤：{e}")
            time.sleep(5)
        time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Bot 已停止")
