#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Bot - 賽馬預測完整版（冇頻道限制，顯示中文馬名）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
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
# 🔐 設定（請改為你嘅資料）
# ============================================================
TOKEN = '8848079617:AAGa3u5IZbPtMtbFleEGxIHqV9BuNK5nv3g'          # 去 @BotFather 換新 Token
ADMIN_ID = '7988559873'          # 你嘅 Telegram ID

SUBSCRIBE_FILE = 'subscribers.json'
BLOCK_FILE = 'blocked_users.json'

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

# ============================================================
# 🚫 封鎖管理
# ============================================================
def load_blocked():
    if os.path.exists(BLOCK_FILE):
        with open(BLOCK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_blocked(blocked):
    with open(BLOCK_FILE, 'w', encoding='utf-8') as f:
        json.dump(blocked, f, ensure_ascii=False, indent=2)

def is_blocked(chat_id):
    return str(chat_id) in load_blocked()

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_ID)

# ============================================================
# 📨 發送訊息
# ============================================================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
        logger.info(f"發送訊息到 {chat_id}：{text[:30]}...")
    except Exception as e:
        logger.error(f"發送失敗：{e}")

def send_message_to_all(text):
    subscribers = load_subscribers()
    for chat_id in subscribers:
        send_message(chat_id, text)
        time.sleep(0.5)

# ============================================================
# 🔧 執行指令
# ============================================================
def run_script(script_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
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
# 🏇 一般用戶指令
# ============================================================

def cmd_predict(chat_id):
    logger.info(f"用戶 {chat_id} 觸發預測")
    send_message(chat_id, "🏇 開始執行預測...")
    result = run_script('predict_race_card.py')
    if result.returncode != 0:
        send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
        return
    try:
        df = pd.read_csv('prediction_result.csv')
        # 自動偵測欄位名
        name_col = '馬匹名稱' if '馬匹名稱' in df.columns else 'horse_id'
        draw_col = '檔位' if '檔位' in df.columns else 'draw'
        win_col = '預測勝率' if '預測勝率' in df.columns else 'prob'
        value_col = '值博指數' if '值博指數' in df.columns else 'value'
        
        top5 = df.head(5)
        msg = "🏇 預測結果 TOP 5\n\n"
        for i, row in top5.iterrows():
            horse = row.get(name_col, '未知')
            draw = row.get(draw_col, '?')
            win_rate = row.get(win_col, 0)
            value = row.get(value_col, 0)
            msg += f"{horse} (檔位 {draw})  勝率 {win_rate:.2%}  值博指數 {value:.3f}\n"
        send_message(chat_id, msg)
        send_message(chat_id, "✅ 預測完成！")
        logger.info(f"預測完成，已發送結果給 {chat_id}")
    except Exception as e:
        logger.error(f"讀取結果失敗：{e}")
        send_message(chat_id, f"❌ 讀取結果失敗：{str(e)}")

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

def cmd_subscribe(chat_id):
    subscribers = load_subscribers()
    if str(chat_id) not in subscribers:
        subscribers.append(str(chat_id))
        save_subscribers(subscribers)
        send_message(chat_id, "✅ 訂閱成功！每日會自動收到預測報告。")
    else:
        send_message(chat_id, "⚠️ 你已經訂閱咗。")

def cmd_unsubscribe(chat_id):
    subscribers = load_subscribers()
    if str(chat_id) in subscribers:
        subscribers.remove(str(chat_id))
        save_subscribers(subscribers)
        send_message(chat_id, "✅ 已取消訂閱。")
    else:
        send_message(chat_id, "⚠️ 你並未訂閱。")

# ============================================================
# 🔐 管理員指令（只限你）
# ============================================================

def cmd_status(chat_id):
    status = "📊 系統狀態報告\n"
    status += "─" * 30 + "\n"
    status += f"🕐 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    status += f"👥 訂閱用戶：{len(load_subscribers())} 人\n"
    status += f"🚫 被封鎖用戶：{len(load_blocked())} 人\n"
    files = ['ALL_DATA_MERGED.csv', 'HKCJ_FULL_YEAR_DATA.csv', 'hk_racing_model.pkl']
    for f in files:
        exists = os.path.exists(f)
        size = os.path.getsize(f) if exists else 0
        status += f"{'✅' if exists else '❌'} {f}: {size/1024/1024:.1f}MB\n"
    send_message(chat_id, status)

def cmd_update(chat_id):
    send_message(chat_id, "🔄 正在更新排位表...")
    result = run_script('scrape_racecard_with_odds.py')
    if result.returncode != 0:
        send_message(chat_id, f"❌ 更新失敗：\n{result.stderr[:500]}")
        return
    send_message(chat_id, "✅ 排位表已更新！")
    cmd_predict(chat_id)

def cmd_logs(chat_id):
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-30:] if len(lines) > 30 else lines
                msg = "📋 最近日誌：\n" + "".join(last_lines)
                if len(msg) > 4000:
                    for i in range(0, len(msg), 4000):
                        send_message(chat_id, msg[i:i+4000])
                else:
                    send_message(chat_id, msg)
        else:
            send_message(chat_id, "⚠️ 未有日誌檔案")
    except Exception as e:
        send_message(chat_id, f"❌ 讀取日誌失敗：{str(e)}")

def cmd_broadcast(chat_id, message):
    subscribers = load_subscribers()
    if not subscribers:
        send_message(chat_id, "⚠️ 未有訂閱用戶")
        return
    send_message(chat_id, f"📢 開始廣播俾 {len(subscribers)} 位用戶...")
    for sub in subscribers:
        send_message(sub, f"📢 廣播：{message}")
        time.sleep(0.5)
    send_message(chat_id, "✅ 廣播完成！")

def cmd_restart(chat_id):
    send_message(chat_id, "🔄 正在重新啟動 Bot...")
    subprocess.Popen(['python', 'telegram_bot.py'])
    sys.exit(0)

def cmd_block(chat_id, target_id):
    blocked = load_blocked()
    if str(target_id) not in blocked:
        blocked.append(str(target_id))
        save_blocked(blocked)
        send_message(chat_id, f"✅ 已封鎖用戶 {target_id}")

def cmd_unblock(chat_id, target_id):
    blocked = load_blocked()
    if str(target_id) in blocked:
        blocked.remove(str(target_id))
        save_blocked(blocked)
        send_message(chat_id, f"✅ 已解鎖用戶 {target_id}")

def cmd_blocklist(chat_id):
    blocked = load_blocked()
    if blocked:
        send_message(chat_id, "🚫 被封鎖用戶列表：\n" + "\n".join(blocked))
    else:
        send_message(chat_id, "✅ 目前沒有被封鎖嘅用戶")

def cmd_check(chat_id, target_id):
    blocked = load_blocked()
    if str(target_id) in blocked:
        send_message(chat_id, f"🔴 用戶 {target_id} 已被封鎖")
    else:
        send_message(chat_id, f"🟢 用戶 {target_id} 未被封鎖")

# ============================================================
# 📨 訊息處理
# ============================================================
def handle_message(chat_id, text):
    logger.info(f"收到訊息：{text} 來自 {chat_id}")
    
    # 檢查封鎖（管理員除外）
    if not is_admin(chat_id) and is_blocked(chat_id):
        send_message(chat_id, "🚫 你已被封鎖，無法使用此 Bot")
        return
    
    cmd = text.lower().strip()
    admin_user = is_admin(chat_id)
    
    # 管理員指令
    if admin_user:
        if cmd in ['/status', '/狀態']:
            cmd_status(chat_id)
            return
        elif cmd in ['/update', '/更新']:
            cmd_update(chat_id)
            return
        elif cmd in ['/logs', '/日誌']:
            cmd_logs(chat_id)
            return
        elif cmd.startswith('/broadcast') or cmd.startswith('/廣播'):
            parts = text.split(' ', 1)
            if len(parts) > 1:
                cmd_broadcast(chat_id, parts[1])
            else:
                send_message(chat_id, "請輸入要廣播嘅訊息")
            return
        elif cmd in ['/restart', '/重啟']:
            cmd_restart(chat_id)
            return
        elif cmd.startswith('/block') and not cmd.startswith('/blocklist'):
            parts = text.split()
            if len(parts) > 1:
                cmd_block(chat_id, parts[1])
            else:
                send_message(chat_id, "請輸入要封鎖嘅用戶 ID")
            return
        elif cmd.startswith('/unblock'):
            parts = text.split()
            if len(parts) > 1:
                cmd_unblock(chat_id, parts[1])
            else:
                send_message(chat_id, "請輸入要解鎖嘅用戶 ID")
            return
        elif cmd in ['/blocklist', '/封鎖列表']:
            cmd_blocklist(chat_id)
            return
        elif cmd.startswith('/check'):
            parts = text.split()
            if len(parts) > 1:
                cmd_check(chat_id, parts[1])
            else:
                send_message(chat_id, "請輸入要檢查嘅用戶 ID")
            return
    
    # 一般用戶指令
    if cmd in ['/predict', '/預測']:
        cmd_predict(chat_id)
    elif cmd in ['/schedule', '/賽程']:
        cmd_schedule(chat_id)
    elif cmd.startswith('/horse') or cmd.startswith('/馬匹'):
        parts = text.split()
        if len(parts) > 1:
            cmd_horse(chat_id, parts[1])
        else:
            send_message(chat_id, "請輸入馬匹編號，例如：/馬匹 G123")
    elif cmd.startswith('/jockey') or cmd.startswith('/騎師'):
        parts = text.split()
        if len(parts) > 1:
            cmd_jockey(chat_id, ' '.join(parts[1:]))
        else:
            send_message(chat_id, "請輸入騎師名，例如：/騎師 潘頓")
    elif cmd in ['/subscribe', '/訂閱']:
        cmd_subscribe(chat_id)
    elif cmd in ['/unsubscribe', '/取消訂閱']:
        cmd_unsubscribe(chat_id)
    elif cmd in ['/help', '/幫助']:
        help_text = """
🤖 賽馬預測 Bot 指令列表

🏇 預測類：
/預測 - 預測最新賽日第9場

📊 查詢類：
/賽程 - 顯示今日賽程
/馬匹 G123 - 查詢馬匹歷史戰績
/騎師 潘頓 - 查詢騎師近績

📋 訂閱類：
/訂閱 - 訂閱每日自動預測報告
/取消訂閱 - 取消訂閱

🔐 管理員指令（只限你）：
/status - 查看系統狀態
/更新 - 更新排位表 + 自動預測
/logs - 顯示最近日誌
/broadcast 訊息 - 向所有訂閱用戶廣播
/restart - 重新啟動 Bot

🚫 封鎖指令（只限你）：
/block 用戶ID - 封鎖用戶
/unblock 用戶ID - 解鎖用戶
/blocklist - 顯示被封鎖列表
/check 用戶ID - 檢查用戶狀態
        """
        send_message(chat_id, help_text)
    else:
        send_message(chat_id, "請使用 /help 查看所有可用指令")

# ============================================================
# 🚀 主程式
# ============================================================
def main():
    logger.info("=" * 50)
    logger.info("Bot 啟動中...")
    logger.info(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    send_message(ADMIN_ID, "✅ Bot 已啟動！傳送 /help 查看所有指令")
    
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
            logger.error(f"監聽錯誤：{e}")
            time.sleep(5)
        time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot 已停止")