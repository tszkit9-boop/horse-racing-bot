#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Bot - 賽馬預測最終完整版
- 所有功能齊全
- 動態 help（管理員／普通用戶分開）
- 騎師中英文對照
- 馬匹中文名顯示
- 賽果對比（全部場次 / 單一場次）
- 全日預測（全部場次）
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
import re
from datetime import datetime, timedelta

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
TOKEN = '8848079617:AAGa3u5IZbPtMtbFleEGxIHqV9BuNK5nv3g'          # 去 @BotFather 換新 Token
ADMIN_ID = '7988559873'          # 你嘅 Telegram ID

SUBSCRIBE_FILE = 'subscribers.json'
BLOCK_FILE = 'blocked_users.json'
NAME_MAP_FILE = 'horse_name_mapping.csv'

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
# 🔧 執行指令（支援參數）
# ============================================================
def run_script(script_name, args=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
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
        timeout=600,  # 延長 timeout，因為全部場次可能需要較長時間
        env=my_env
    )
    return result

# ============================================================
# 🔍 輔助函數（自動偵測欄位）
# ============================================================
def get_finish_column(df):
    """偵測名次欄位"""
    candidates = ['finish_position', '名次', 'Position', 'pos', 'Rank', 'rank', '最終名次']
    for col in candidates:
        if col in df.columns:
            return col
    return None

def get_name_columns(df):
    """偵測馬名欄位"""
    candidates = ['馬名', 'horse_name', '中文名', 'Name', 'name']
    for col in candidates:
        if col in df.columns:
            return col
    return None

# ============================================================
# 🏇 一般用戶指令
# ============================================================

def cmd_predict(chat_id, args_text=None):
    """執行預測（支援日期 + 場次）"""
    date_str = None
    race_no = None
    
    if args_text:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', args_text)
        if date_match:
            date_str = date_match.group(1)
            remaining = re.sub(r'\d{4}-\d{2}-\d{2}', '', args_text).strip()
        else:
            remaining = args_text.strip()
        if remaining:
            num_match = re.search(r'(\d+)', remaining)
            if num_match:
                race_no = int(num_match.group(1))
    
    cmd_args = []
    if date_str:
        cmd_args.extend(['--date', date_str])
    if race_no:
        cmd_args.extend(['--race', str(race_no)])
    
    if cmd_args:
        logger.info(f"用戶 {chat_id} 觸發預測：{cmd_args}")
        send_message(chat_id, f"🏇 開始執行預測 {' '.join(cmd_args)}...")
    else:
        logger.info(f"用戶 {chat_id} 觸發預測（自動）")
        send_message(chat_id, "🏇 開始執行預測...")
    
    result = run_script('predict_race_card.py', cmd_args)
    
    if result.returncode != 0:
        send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
        return
    try:
        df = pd.read_csv('prediction_result.csv')
        race_date = df['比賽日期'].iloc[0] if '比賽日期' in df.columns else '未知日期'
        race_no_display = df['場次'].iloc[0] if '場次' in df.columns else '?'
        name_col = '馬匹名稱' if '馬匹名稱' in df.columns else 'horse_id'
        draw_col = '檔位' if '檔位' in df.columns else 'draw'
        win_col = '預測勝率' if '預測勝率' in df.columns else 'prob'
        value_col = '值博指數' if '值博指數' in df.columns else 'value'
        
        top5 = df.head(5)
        msg = f"🏇 {race_date} 第 {race_no_display} 場 預測 TOP 5\n\n"
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

# ============================================================
# 1. /賽程 指令
# ============================================================
def cmd_schedule(chat_id, target_date=None):
    """顯示指定日期或今日嘅賽程"""
    if target_date:
        try:
            date_obj = pd.to_datetime(target_date)
            display_date = date_obj.strftime('%Y-%m-%d')
        except:
            send_message(chat_id, "❌ 日期格式錯誤，請使用 YYYY-MM-DD")
            return
    else:
        date_obj = datetime.now()
        display_date = date_obj.strftime('%Y-%m-%d')
    
    send_message(chat_id, f"📅 正在查詢 {display_date} 嘅賽程...")
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv')
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
        # 過濾指定日期
        day_races = df[df['race_date'].dt.date == date_obj.date()]
        if day_races.empty:
            send_message(chat_id, f"📅 {display_date} 沒有賽事")
            return
        
        courses = day_races['race_course'].unique()
        msg = f"📅 {display_date} 賽程\n\n"
        for course in courses:
            races = day_races[day_races['race_course'] == course]
            race_nos = sorted(races['race_no'].unique())
            msg += f"🏟️ {course}：第 {', '.join(map(str, race_nos))} 場\n"
        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"查詢賽程失敗：{e}")
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# ============================================================
# 2. /馬匹 指令
# ============================================================
def cmd_horse(chat_id, horse_name_or_id):
    send_message(chat_id, f"🔍 正在查詢馬匹 {horse_name_or_id}...")
    try:
        df = pd.read_csv('ALL_DATA_MERGED.csv')
        # 先直接查 horse_id
        horse_data = df[df['horse_id'] == horse_name_or_id]
        # 如果冇，嘗試用中文名
        if horse_data.empty:
            name_col = get_name_columns(df)
            if name_col:
                horse_data = df[df[name_col] == horse_name_or_id]
        # 再試對照表
        if horse_data.empty and os.path.exists(NAME_MAP_FILE):
            try:
                name_map = pd.read_csv(NAME_MAP_FILE)
                matched = name_map[name_map['馬名'] == horse_name_or_id]
                if not matched.empty:
                    horse_id = matched.iloc[0]['horse_id']
                    horse_data = df[df['horse_id'] == horse_id]
            except:
                pass
        
        if horse_data.empty:
            send_message(chat_id, f"❌ 找不到馬匹 {horse_name_or_id}")
            return
        
        total = len(horse_data)
        
        # ---- 讀取馬名（處理 NaN） ----
        if '馬名' in horse_data.columns:
            horse_name_val = horse_data['馬名'].iloc[0]
            if pd.isna(horse_name_val) or horse_name_val == '':
                horse_name = horse_data['horse_id'].iloc[0]
            else:
                horse_name = horse_name_val
        else:
            horse_name = horse_data['horse_id'].iloc[0]
        
        # ---- 名次統計 ----
        finish_col = get_finish_column(horse_data)
        if finish_col:
            valid_rank = horse_data[finish_col].dropna()
            total_valid = len(valid_rank)
            wins = (valid_rank == 1).sum() if total_valid > 0 else 0
            win_rate = wins / total_valid * 100 if total_valid > 0 else 0
            recent = horse_data.sort_values('race_date', ascending=False)[finish_col].dropna().head(3).tolist()
            recent_str = ', '.join([str(int(r)) for r in recent]) if recent else '無紀錄'
        else:
            wins = 0
            win_rate = 0
            recent_str = '無名次欄位'
        
        msg = f"🐴 馬匹：{horse_name}\n"
        msg += f"馬匹編號：{horse_data.iloc[0]['horse_id']}\n"
        msg += f"總出賽：{total}\n"
        if finish_col:
            msg += f"頭馬：{wins}\n"
            msg += f"勝率：{win_rate:.1f}%\n"
            msg += f"近3場名次：{recent_str}"
        else:
            msg += "（無名次紀錄）"
        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"查詢馬匹失敗：{e}")
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# ============================================================
# 3. /騎師 指令（中英文對照）
# ============================================================
def cmd_jockey(chat_id, jockey_name):
    send_message(chat_id, f"🔍 正在查詢騎師 {jockey_name}...")
    try:
        df = pd.read_csv('ALL_DATA_MERGED.csv')
        
        # ---- 中英文騎師對照表 ----
        jockey_mapping = {
            '潘頓': ['Z Purton', 'Purton'],
            '莫雷拉': ['J Moreira', 'Moreira'],
            '田泰安': ['K Teetan', 'Teetan'],
            '梁家俊': ['K C Leung', 'Leung'],
            '周俊樂': ['C L Chau', 'Chau'],
            '布文': ['H Bowman', 'Bowman'],
            '蔡明紹': ['M Chadwick', 'Chadwick'],
            '潘明輝': ['M F Poon', 'Poon'],
            '鍾易禮': ['Y L Chung', 'Chung'],
            '湯森': ['B Thompson', 'Thompson'],
            '奧文': ['J Orman', 'Orman'],
            '賀銘年': ['A Hamelin', 'Hamelin'],
            '班德禮': ['H Bentley', 'Bentley'],
            '狄莫羅': ['K De Melo', 'De Melo'],
            '艾兆禮': ['A Atzeni', 'Atzeni'],
            '陳嘉熙': ['K H Chan', 'Chan'],
            '巫顯東': ['H T Mo', 'Mo'],
            '李富': ['L Ferraris', 'Ferraris'],
            '黃智弘': ['E C W Wong', 'Wong'],
            '希威森': ['L Currie', 'Currie'],
            '霍宏聲': ['L Hewitson', 'Hewitson'],
            '嘉里': ['J Kah', 'Kah'],
            '馬雅': ['R Maia', 'Maia'],
            '楊明綸': ['M L Yeung', 'Yeung'],
            '何澤堯': ['C Y Ho', 'Ho'],
            '巴度': ['A Badel', 'Badel'],
            '蘇兆輝': ['S de Sousa', 'de Sousa'],
            '韋達': ['D Whyte', 'Whyte'],
            '薛恩': ['B Shinn', 'Shinn'],
        }
        
        # 直接查
        jockey_data = pd.DataFrame()
        if '騎師' in df.columns:
            jockey_data = df[df['騎師'].astype(str).str.contains(jockey_name, na=False, case=False)]
        if jockey_data.empty and 'jockey' in df.columns:
            jockey_data = df[df['jockey'].astype(str).str.contains(jockey_name, na=False, case=False)]
        
        # 對照表轉換
        if jockey_data.empty and jockey_name in jockey_mapping:
            for eng_name in jockey_mapping[jockey_name]:
                if '騎師' in df.columns:
                    temp = df[df['騎師'].astype(str).str.contains(eng_name, na=False, case=False)]
                    if not temp.empty:
                        jockey_data = temp
                        break
                if 'jockey' in df.columns:
                    temp = df[df['jockey'].astype(str).str.contains(eng_name, na=False, case=False)]
                    if not temp.empty:
                        jockey_data = temp
                        break
        
        if jockey_data.empty:
            send_message(chat_id, f"❌ 找不到騎師 {jockey_name}")
            return
        
        total = len(jockey_data)
        finish_col = get_finish_column(jockey_data)
        if finish_col:
            valid_rank = jockey_data[finish_col].dropna()
            wins = (valid_rank == 1).sum() if len(valid_rank) > 0 else 0
            win_rate = wins / total * 100 if total > 0 else 0
            msg = f"🏇 騎師：{jockey_name}\n"
            msg += f"總出賽：{total}\n"
            msg += f"頭馬：{wins}\n"
            msg += f"勝率：{win_rate:.1f}%"
        else:
            msg = f"🏇 騎師：{jockey_name}\n"
            msg += f"總出賽：{total}\n"
            msg += "（無名次紀錄）"
        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"查詢騎師失敗：{e}")
        send_message(chat_id, f"❌ 查詢失敗：{str(e)}")

# ============================================================
# 🆕 4. /對比 賽果對比指令（全部場次 / 單一場次）
# ============================================================
def cmd_compare(chat_id, args_text=None):
    """賽果對比：預測 vs 實際（全部場次或單一場次）"""
    date_str = None
    race_no = None
    
    if args_text:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', args_text)
        if date_match:
            date_str = date_match.group(1)
            remaining = re.sub(r'\d{4}-\d{2}-\d{2}', '', args_text).strip()
        else:
            remaining = args_text.strip()
        if remaining:
            num_match = re.search(r'(\d+)', remaining)
            if num_match:
                race_no = int(num_match.group(1))
    
    if not date_str:
        # 預設尋日
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        send_message(chat_id, f"📅 未指定日期，自動使用 {date_str}")
    
    send_message(chat_id, f"📊 正在對比 {date_str}" + (f" 第{race_no}場" if race_no else " 全部場次") + "...")
    
    # 執行對比腳本
    cmd_args = ['--date', date_str]
    if race_no:
        cmd_args.extend(['--race', str(race_no)])
    
    result = run_script('compare_results.py', cmd_args)
    
    if result.returncode != 0:
        send_message(chat_id, f"❌ 對比失敗：\n{result.stderr[:500]}")
        return
    
    # 讀取報告
    try:
        with open('compare_report.txt', 'r', encoding='utf-8') as f:
            report = f.read()
        # 如果報告太長，分段發送
        if len(report) > 4000:
            for i in range(0, len(report), 4000):
                send_message(chat_id, report[i:i+4000])
        else:
            send_message(chat_id, report)
    except Exception as e:
        send_message(chat_id, f"❌ 讀取報告失敗：{str(e)}")

# ============================================================
# 🆕 5. /預測全部 全日所有場次
# ============================================================
def cmd_predict_all(chat_id, date_str=None):
    """預測全日所有場次"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    send_message(chat_id, f"📊 開始預測 {date_str} 全日所有場次...")
    
    result = run_script('predict_all_races.py', ['--date', date_str])
    
    if result.returncode != 0:
        send_message(chat_id, f"❌ 預測失敗：\n{result.stderr[:500]}")
        return
    
    # 讀取結果
    output_file = f'prediction_all_{date_str}.csv'
    try:
        df = pd.read_csv(output_file)
        if df.empty:
            send_message(chat_id, f"❌ 無預測結果")
            return
        
        # 按場次分組顯示
        race_nos = sorted(df['場次'].unique())
        msg = f"🏇 {date_str} 全日預測結果\n\n"
        for race_no in race_nos:
            race_data = df[df['場次'] == race_no]
            if not race_data.empty:
                winner = race_data.iloc[0]['馬匹名稱']
                win_rate = race_data.iloc[0]['預測勝率']
                msg += f"第{race_no}場：{winner}（勝率 {win_rate:.2%}）\n"
        msg += f"\n📁 詳細資料已儲存至 {output_file}"
        send_message(chat_id, msg)
    except FileNotFoundError:
        send_message(chat_id, f"❌ 找不到結果檔案 {output_file}")
    except Exception as e:
        send_message(chat_id, f"❌ 讀取結果失敗：{str(e)}")

# ============================================================
# 🔐 管理員指令
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

def cmd_subscribe(chat_id):
    subscribers = load_subscribers()
    if str(chat_id) not in subscribers:
        subscribers.append(str(chat_id))
        save_subscribers(subscribers)
        send_message(chat_id, "✅ 訂閱成功！")
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
# 🆕 動態 help（根據權限顯示）
# ============================================================
def cmd_help(chat_id):
    admin_user = is_admin(chat_id)
    
    if admin_user:
        help_text = """
🤖 賽馬預測 Bot 指令列表（管理員完整版）

🏇 預測類：
/預測 - 自動預測最新賽日第9場
/預測 5 - 預測最新賽日第5場
/預測 2026-07-15 - 預測指定日期第9場
/預測 2026-07-15 5 - 預測指定日期第5場
/預測全部 2026-07-15 - 預測全日所有場次

📊 查詢類：
/賽程 - 顯示今日賽程
/賽程 2026-07-15 - 顯示指定日期賽程
/馬匹 金發盛世 - 查詢馬匹歷史戰績（支援中文名或編號）
/騎師 潘頓 - 查詢騎師近績

📊 對比類：
/對比 2026-07-15 - 對比全日預測 vs 賽果
/對比 2026-07-15 5 - 只對比第5場
/對比 - 自動對比尋日

📋 訂閱類：
/訂閱 - 訂閱每日自動預測報告
/取消訂閱 - 取消訂閱

🔐 管理員指令：
/status - 查看系統狀態
/更新 - 更新排位表 + 自動預測
/logs - 顯示最近日誌
/broadcast 訊息 - 向所有訂閱用戶廣播
/restart - 重新啟動 Bot
/block 用戶ID - 封鎖用戶
/unblock 用戶ID - 解鎖用戶
/blocklist - 顯示被封鎖列表
/check 用戶ID - 檢查用戶狀態
        """
    else:
        help_text = """
🤖 賽馬預測 Bot 指令列表

🏇 預測類：
/預測 - 自動預測最新賽日第9場
/預測 5 - 預測最新賽日第5場
/預測 2026-07-15 - 預測指定日期第9場
/預測 2026-07-15 5 - 預測指定日期第5場
/預測全部 2026-07-15 - 預測全日所有場次

📊 查詢類：
/賽程 - 顯示今日賽程
/賽程 2026-07-15 - 顯示指定日期賽程
/馬匹 金發盛世 - 查詢馬匹歷史戰績（支援中文名或編號）
/騎師 潘頓 - 查詢騎師近績

📊 對比類：
/對比 2026-07-15 - 對比全日預測 vs 賽果
/對比 2026-07-15 5 - 只對比第5場
/對比 - 自動對比尋日

📋 訂閱類：
/訂閱 - 訂閱每日自動預測報告
/取消訂閱 - 取消訂閱
        """
    
    send_message(chat_id, help_text)

# ============================================================
# 📨 訊息處理（路由）
# ============================================================
def handle_message(chat_id, text):
    logger.info(f"收到訊息：{text} 來自 {chat_id}")
    
    if not is_admin(chat_id) and is_blocked(chat_id):
        send_message(chat_id, "🚫 你已被封鎖，無法使用此 Bot")
        return
    
    cmd = text.lower().strip()
    admin_user = is_admin(chat_id)
    
    # ---------- 管理員指令 ----------
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
    
    # ---------- 一般用戶指令 ----------
    if cmd.startswith('/predict') or cmd.startswith('/預測'):
        parts = text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else ''
        cmd_predict(chat_id, args)
    
    elif cmd.startswith('/schedule') or cmd.startswith('/賽程'):
        parts = text.split(maxsplit=1)
        date_arg = parts[1] if len(parts) > 1 else None
        cmd_schedule(chat_id, date_arg)
    
    elif cmd.startswith('/horse') or cmd.startswith('/馬匹'):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            cmd_horse(chat_id, parts[1].strip())
        else:
            send_message(chat_id, "請輸入馬匹名稱或編號，例如：/馬匹 金發盛世 或 /馬匹 G209")
    
    elif cmd.startswith('/jockey') or cmd.startswith('/騎師'):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            cmd_jockey(chat_id, parts[1].strip())
        else:
            send_message(chat_id, "請輸入騎師名，例如：/騎師 潘頓")
    
    elif cmd.startswith('/compare') or cmd.startswith('/對比'):
        parts = text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else ''
        cmd_compare(chat_id, args)
    
    elif cmd.startswith('/predictall') or cmd.startswith('/預測全部'):
        parts = text.split(maxsplit=1)
        date_arg = parts[1] if len(parts) > 1 else None
        cmd_predict_all(chat_id, date_arg)
    
    elif cmd in ['/subscribe', '/訂閱']:
        cmd_subscribe(chat_id)
    elif cmd in ['/unsubscribe', '/取消訂閱']:
        cmd_unsubscribe(chat_id)
    elif cmd in ['/help', '/幫助']:
        cmd_help(chat_id)
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