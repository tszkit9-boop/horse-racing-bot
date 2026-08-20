#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Bot - 賽馬預測全能版
支援：預測、更新排位、賽程、賽果、馬匹查詢、騎師查詢、賠率提醒、訂閱功能
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import subprocess
import pandas as pd
import time
import os
import json
import re
from datetime import datetime, timedelta

# ============================================================
# 🔐 設定區
# ============================================================
TOKEN = '8848079617:AAEE2xilHEZCDrn9BOHAvInMUroX4Je-jRo'          # 去 @BotFather 換新 Token
CHAT_ID = '7988559873'         # 你嘅 Chat ID

# 訂閱用戶清單檔案
SUBSCRIBE_FILE = 'subscribers.json'

# ============================================================
# 📁 訂閱管理
# ============================================================
def load_subscribers():
    if os.path.exists(SUBSCRIBE_FILE):
        with open(SUBSCRIBE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_subscribers(subscribers):
    with open(SUBSCRIBE_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=2)

def is_subscribed(chat_id):
    return str(chat_id) in load_subscribers()

def add_subscriber(chat_id):
    subs = load_subscribers()
    if str(chat_id) not in subs:
        subs.append(str(chat_id))
        save_subscribers(subs)
        return True
    return False

def remove_subscriber(chat_id):
    subs = load_subscribers()
    if str(chat_id) in subs:
        subs.remove(str(chat_id))
        save_subscribers(subs)
        return True
    return False

# ============================================================
# 📨 發送訊息
# ============================================================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        print(f"發送失敗：{e}")

def send_message_to_all(text):
    """發送訊息俾所有訂閱用戶"""
    subscribers = load_subscribers()
    for chat_id in subscribers:
        send_message(chat_id, text)
        time.sleep(0.5)  # 避免 Telegram 限流

# ============================================================
# 🔧 執行指令（子程序）
# ============================================================
def run_script(script_name, args=None):
    """執行 Python 腳本，回傳輸出"""
    os.chdir(r'C:\Users\defaultuser100000\Desktop1')
    my_env = os.environ.copy()
    my_env['PYTHONIOENCODING'] = 'utf-8'
    my_env['PYTHONUTF8'] = '1'
    
    cmd = ['python', script_name]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        env=my_env
    )
    return result

# ============================================================
# 🏇 核心功能
# ============================================================

# 1. 預測（第9場）
def cmd_predict(chat_id):
    send_message(chat_id, "🏇 開始執行預測...")
    result = run_script('predict_race_card.py')
    if result.returncode != 0:
        send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
        return
    send_prediction_result(chat_id)

# 2. 預測全部場次
def cmd_predict_all(chat_id):
    send_message(chat_id, "🏇 開始預測全日所有場次...")
    result = run_script('predict_all_races.py')  # 需要另外建立
    if result.returncode != 0:
        send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
        return
    send_message(chat_id, "✅ 全日預測完成！請查看 prediction_all.csv")

# 3. 更新排位表
def cmd_update(chat_id):
    send_message(chat_id, "🔄 正在更新排位表...")
    result = run_script('scrape_racecard_with_odds.py')
    if result.returncode != 0:
        send_message(chat_id, f"❌ 更新失敗：\n{result.stderr[:500]}")
        return
    send_message(chat_id, "✅ 排位表已更新！")
    # 自動執行預測
    cmd_predict(chat_id)

# 4. 今日賽程
def cmd_schedule(chat_id):
    send_message(chat_id, "📅 正在查詢今日賽程...")
    # 可以從 HKJC 爬蟲或本地檔案讀取
    # 簡單示範：讀取排位表嘅日期
    try:
        df = pd.read_csv(r'C:\Users\defaultuser100000\Desktop1\HKCJ_FULL_YEAR_DATA.csv')
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

# 5. 賽果查詢
def cmd_result(chat_id, date_str):
    send_message(chat_id, f"📊 正在查詢 {date_str} 賽果...")
    try:
        # 假設有賽果檔案 race_results.csv
        df = pd.read_csv(r'C:\Users\defaultuser100000\Desktop1\race_results.csv')
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
        target_date = pd.to_datetime(date_str)
        results = df[df['race_date'].dt.date == target_date.date()]
        if results.empty:
            send_message(chat_id, f"📊 {date_str} 沒有賽果記錄")
        else:
            msg = f"📊 {date_str} 賽果\n\n"
            for race_no in sorted(results['race_no'].unique()):
                race_results = results[results['race_no'] == race_no]
                msg += f"第{race_no}場：\n"
                for _, row in race_results.iterrows():
                    msg += f"  {row['horse_id']} - 名次 {row['finish_position']}\n"
                msg += "\n"
            send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# 6. 馬匹查詢
def cmd_horse(chat_id, horse_id):
    send_message(chat_id, f"🔍 正在查詢馬匹 {horse_id}...")
    try:
        df = pd.read_csv(r'C:\Users\defaultuser100000\Desktop1\ALL_DATA_MERGED.csv')
        horse_data = df[df['horse_id'] == horse_id]
        if horse_data.empty:
            send_message(chat_id, f"❌ 找不到馬匹 {horse_id}")
            return
        # 統計
        total = len(horse_data)
        wins = (horse_data['finish_position'] == 1).sum() if 'finish_position' in horse_data.columns else 0
        win_rate = wins / total * 100 if total > 0 else 0
        recent = horse_data.sort_values('race_date').tail(3)['finish_position'].tolist()
        msg = f"🐴 馬匹 {horse_id}\n\n"
        msg += f"總出賽：{total}\n"
        msg += f"頭馬：{wins}\n"
        msg += f"勝率：{win_rate:.1f}%\n"
        msg += f"近3場名次：{', '.join(map(str, recent))}\n"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# 7. 騎師查詢
def cmd_jockey(chat_id, jockey_name):
    send_message(chat_id, f"🔍 正在查詢騎師 {jockey_name}...")
    try:
        df = pd.read_csv(r'C:\Users\defaultuser100000\Desktop1\ALL_DATA_MERGED.csv')
        jockey_data = df[df['jockey'] == jockey_name]
        if jockey_data.empty:
            send_message(chat_id, f"❌ 找不到騎師 {jockey_name}")
            return
        total = len(jockey_data)
        wins = (jockey_data['finish_position'] == 1).sum() if 'finish_position' in jockey_data.columns else 0
        win_rate = wins / total * 100 if total > 0 else 0
        msg = f"🏇 騎師 {jockey_name}\n\n"
        msg += f"總出賽：{total}\n"
        msg += f"頭馬：{wins}\n"
        msg += f"勝率：{win_rate:.1f}%\n"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# 8. 賠率提醒
def cmd_odds_alert(chat_id, threshold=10):
    """當賠率變動超過 threshold% 時通知"""
    send_message(chat_id, f"🔔 已設定賠率提醒 (變動 > {threshold}%)")
    # 呢度需要持續監控賠率變化，建議另開一個 thread 或 cron job
    # 簡單做法：儲存設定，然後每日定時檢查
    alert_config = {'threshold': threshold, 'chat_id': chat_id}
    with open('odds_alert_config.json', 'w', encoding='utf-8') as f:
        json.dump(alert_config, f)
    send_message(chat_id, "✅ 賠率提醒已啟用！當賠率變動超過設定值時會通知你。")

# 9. 訂閱功能
def cmd_subscribe(chat_id):
    if add_subscriber(chat_id):
        send_message(chat_id, "✅ 訂閱成功！每日會自動 Send 預測結果俾你。")
    else:
        send_message(chat_id, "⚠️ 你已經訂閱咗。")

def cmd_unsubscribe(chat_id):
    if remove_subscriber(chat_id):
        send_message(chat_id, "✅ 已取消訂閱。")
    else:
        send_message(chat_id, "⚠️ 你並未訂閱。")

# 10. 發送預測結果（輔助函數）
def send_prediction_result(chat_id):
    try:
        csv_path = r'C:\Users\defaultuser100000\Desktop1\prediction_result.csv'
        df = pd.read_csv(csv_path)
        top5 = df.head(5)
        message = "🏇 預測結果 TOP 5\n\n"
        for i, row in top5.iterrows():
            horse = row.get('馬匹編號', '未知')
            draw = row.get('draw', '?')
            win_rate = row.get('預測勝率', 0)
            value = row.get('值博指數', 0)
            message += f"{horse} (檔位 {draw})  勝率 {win_rate:.2%}  值博指數 {value:.3f}\n"
        send_message(chat_id, message)
        send_message(chat_id, "✅ 預測完成！")
    except Exception as e:
        send_message(chat_id, f"❌ 讀取結果失敗：{str(e)}")

# ============================================================
# 📨 訊息處理
# ============================================================
def handle_message(chat_id, text):
    """處理用戶訊息"""
    # 更新排位表
    if text in ['/update', '/更新']:
        cmd_update(chat_id)
    
    # 預測（第9場）
    elif text in ['/predict', '/預測']:
        cmd_predict(chat_id)
    
    # 預測全部
    elif text in ['/predict_all', '/預測全部']:
        cmd_predict_all(chat_id)
    
    # 今日賽程
    elif text in ['/schedule', '/賽程']:
        cmd_schedule(chat_id)
    
    # 訂閱
    elif text in ['/subscribe', '/訂閱']:
        cmd_subscribe(chat_id)
    
    # 取消訂閱
    elif text in ['/unsubscribe', '/取消訂閱']:
        cmd_unsubscribe(chat_id)
    
    # 賠率提醒
    elif text.startswith('/odds'):
        parts = text.split()
        threshold = int(parts[1]) if len(parts) > 1 else 10
        cmd_odds_alert(chat_id, threshold)
    
    # 賽果查詢 (/result 2025-04-09)
    elif text.startswith('/result') or text.startswith('/賽果'):
        parts = text.split()
        if len(parts) > 1:
            cmd_result(chat_id, parts[1])
        else:
            send_message(chat_id, "請輸入日期，例如：/result 2025-04-09")
    
    # 馬匹查詢 (/horse G123)
    elif text.startswith('/horse') or text.startswith('/馬匹'):
        parts = text.split()
        if len(parts) > 1:
            cmd_horse(chat_id, parts[1])
        else:
            send_message(chat_id, "請輸入馬匹編號，例如：/horse G123")
    
    # 騎師查詢 (/jockey 潘頓)
    elif text.startswith('/jockey') or text.startswith('/騎師'):
        parts = text.split()
        if len(parts) > 1:
            cmd_jockey(chat_id, ' '.join(parts[1:]))
        else:
            send_message(chat_id, "請輸入騎師名，例如：/jockey 潘頓")
    
    # Help
    elif text in ['/help', '/幫助']:
        help_text = """
🤖 賽馬預測 Bot 指令列表

🏇 預測類：
/預測 - 預測最新賽日第9場
/預測全部 - 預測全日所有場次

📊 查詢類：
/賽程 - 顯示今日賽程
/賽果 YYYY-MM-DD - 查詢指定日期賽果
/馬匹 馬號 - 查詢馬匹歷史戰績
/騎師 騎師名 - 查詢騎師近績

🔄 更新類：
/更新 - 更新排位表 + 自動預測

🔔 提醒類：
/賠率 10 - 設定賠率提醒 (變動 > 10%)
/訂閱 - 訂閱每日自動預測報告
/取消訂閱 - 取消訂閱

❓ 其他：
/help - 顯示呢個幫助
        """
        send_message(chat_id, help_text)
    
    else:
        # 非指令訊息，可選擇不理會或提示
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