#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整版
整合所有功能：預測、投注、用戶管理、後台、活動日誌
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import json
import re
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier
import plotly.express as px
import plotly.graph_objects as go
import random
from PIL import Image

# ============================================================
# 🔒 隱藏 Streamlit 平台 UI
# ============================================================
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

st.markdown("""
<style>
    div[data-testid="stToolbar"] { display: none !important; }
    .stAppDeployButton { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    button[kind="share"] { display: none !important; }
    a[href*="streamlit.io"] { display: none !important; }
    .st-emotion-cache-1r6slb0 { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    .stApp > header { display: none !important; }
    section[data-testid="stSidebar"] { display: block !important; visibility: visible !important; opacity: 1 !important; width: 300px !important; }
    section[data-testid="stSidebar"] * { display: block !important; visibility: visible !important; opacity: 1 !important; }
    .stApp > header + div { padding-top: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔐 系統設定
# ============================================================
CONFIG_FILE = 'system_config.json'
DEFAULT_CONFIG = {
    "enable_registration": True, "enable_payment": True, "enable_admin": True,
    "currency": "HKD", "free_limit": 2, "admin_password": "z54060437K",
    "price_day": 18, "price_month": 128, "price_quarter": 328,
    "verification_expiry": 5, "enable_vip_content": True, "enable_daily_free_tip": True,
    "enable_invite_reward": True, "invite_reward_inviter": 1, "invite_reward_invitee": 1,
    "xgb_weight": 25, "cat_weight": 1, "last_weight_update": "", "last_hit_rate": 0.0,
    "module_user_management": True, "module_analytics": True, "module_finance": True,
    "module_monitoring": True, "module_content": True, "module_automation": True,
    "module_security": True, "module_promo": True, "daily_virtual_coin": 1000,
    "virtual_coin_enabled": True,
}

def load_system_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except:
            return DEFAULT_CONFIG.copy()
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_CONFIG.copy()

def save_system_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

CONFIG = load_system_config()

# ============================================================
# 基本 JSON 讀寫
# ============================================================
def load_json(file_path, default=None):
    if default is None:
        default = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# ============================================================
# 檔案路徑常數
# ============================================================
USER_DATA_FILE = 'users.json'
FINANCE_FILE = 'finance.json'
PROMO_FILE = 'promo_codes.json'
LOG_FILE = 'admin_log.json'
ACCURACY_FILE = 'accuracy.json'
CONTENT_FILE = 'content.json'
AUTOMATION_FILE = 'automation.json'
PAYMENT_PROOFS_FILE = 'payment_proofs.json'
ACTIVITY_LOG_FILE = 'user_activity_log.json'

if not os.path.exists('payment_proofs'):
    os.makedirs('payment_proofs')

if 'payment_requests' not in st.session_state:
    st.session_state.payment_requests = {"requests": []}

# ============================================================
# 用戶活動日誌
# ============================================================
def log_user_activity(username, action, details=""):
    log = load_json(ACTIVITY_LOG_FILE)
    if 'logs' not in log:
        log['logs'] = []
    log['logs'].append({
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'action': action,
        'details': details
    })
    if len(log['logs']) > 10000:
        log['logs'] = log['logs'][-10000:]
    save_json(ACTIVITY_LOG_FILE, log)

def get_user_activity_logs(username=None, days=30, action=None):
    log = load_json(ACTIVITY_LOG_FILE)
    logs = log.get('logs', [])
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for entry in logs:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            if dt < cutoff:
                continue
            if username and entry.get('username') != username:
                continue
            if action and entry.get('action') != action:
                continue
            filtered.append(entry)
        except:
            continue
    return filtered

# ============================================================
# 用戶等級/勳章系統
# ============================================================
def get_level_info(exp):
    levels = [(0, "🥉 銅牌會員"), (100, "🥈 銀牌會員"), (500, "🥇 金牌會員"),
              (1500, "💎 鑽石會員"), (5000, "👑 傳說會員")]
    current_level = levels[0][1]
    next_level_exp = None
    for threshold, level_name in levels:
        if exp >= threshold:
            current_level = level_name
        else:
            next_level_exp = threshold
            break
    return current_level, next_level_exp

def check_badges(username, hit_rate=None):
    users = load_users()
    if username not in users:
        return
    user = users[username]
    history = user.get('history', [])
    badges = user.get('badges', [])
    total_predictions = len(history)
    hits = sum(1 for h in history if h.get('is_hit') is True)
    hit_rate = hits / total_predictions if total_predictions > 0 else 0
    consecutive_hits = 0
    max_consecutive = 0
    for h in history:
        if h.get('is_hit') is True:
            consecutive_hits += 1
            max_consecutive = max(max_consecutive, consecutive_hits)
        else:
            consecutive_hits = 0
    badge_conditions = {
        "🏆 首勝": (total_predictions >= 1 and hits >= 1, ""),
        "🔥 三連勝": (max_consecutive >= 3, ""),
        "⚡ 五連勝": (max_consecutive >= 5, ""),
        "💯 百場預測": (total_predictions >= 100, ""),
        "🎯 命中大師": (total_predictions >= 20 and hit_rate >= 0.5, ""),
        "👥 社交達人": (user.get('invite_count', 0) >= 5, ""),
        "💰 付費會員": (user.get('is_paid', False) or user.get('group') == 'VIP', ""),
        "🏇 馬匹專家": (len(set(h.get('horse') for h in history)) >= 5, ""),
    }
    new_badges = []
    for badge_name, (condition, description) in badge_conditions.items():
        if condition and badge_name not in badges:
            new_badges.append(badge_name)
    if new_badges:
        badges.extend(new_badges)
        user['badges'] = badges
        save_users(users)
    return badges

def update_user_exp(username, is_hit=False):
    users = load_users()
    if username not in users:
        return
    user = users[username]
    exp = user.get('exp', 0) + 10
    if is_hit:
        exp += 20
    user['exp'] = exp
    new_level, next_exp = get_level_info(exp)
    if new_level != user.get('level', ''):
        old_level = user.get('level', '')
        user['level'] = new_level
        if old_level != new_level:
            log_admin_action("system", f"{username} 升級：{old_level} → {new_level}")
    save_users(users)
    check_badges(username)

# ============================================================
# 虛擬幣系統
# ============================================================
def claim_daily_virtual_coin(username):
    if not CONFIG.get("virtual_coin_enabled", True):
        return 0, "虛擬幣功能已關閉"
    users = load_users()
    if username not in users:
        return 0, "用戶不存在"
    user = users[username]
    today = datetime.now().strftime('%Y-%m-%d')
    if user.get('last_claim_date', '') == today:
        return 0, "今日已領取"
    daily_amount = CONFIG.get("daily_virtual_coin", 1000)
    user['virtual_balance'] = user.get('virtual_balance', 0) + daily_amount
    user['last_claim_date'] = today
    save_users(users)
    return daily_amount, f"已領取 ${daily_amount} 虛擬幣"

def get_virtual_balance(username):
    users = load_users()
    if username not in users:
        return 0
    return users[username].get('virtual_balance', 0)

# ============================================================
# 用戶系統
# ============================================================
def load_users():
    users = load_json(USER_DATA_FILE)
    if not users or "admin" not in users:
        users = {
            "admin": {
                "username": "admin", "password": CONFIG["admin_password"],
                "is_paid": False, "paid_date": None, "expiry_date": None,
                "free_usage": 0, "total_usage": 0,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "note": "系統超級管理員", "group": "super_admin", "phone": "",
                "plan": None, "predictions_limit": -1, "history": [],
                "terms_agreed": datetime.now().isoformat(), "invite_code": "ADMIN001",
                "invited_by": None, "invite_rewards": 0, "invite_count": 0,
                "level": "👑 超級管理員", "exp": 0, "badges": [],
                "virtual_balance": 10000, "last_claim_date": "", "bets": []
            }
        }
        save_users(users)
    else:
        if "admin" in users:
            users["admin"]["group"] = "super_admin"
            users["admin"]["predictions_limit"] = -1
            if "level" not in users["admin"]:
                users["admin"]["level"] = "👑 超級管理員"
                users["admin"]["exp"] = 0
                users["admin"]["badges"] = []
            if "virtual_balance" not in users["admin"]:
                users["admin"]["virtual_balance"] = 10000
            if "last_claim_date" not in users["admin"]:
                users["admin"]["last_claim_date"] = ""
            if "bets" not in users["admin"]:
                users["admin"]["bets"] = []
        for uid, u in users.items():
            if 'plan' not in u: u['plan'] = None
            if 'paid_date' not in u: u['paid_date'] = None
            if 'expiry_date' not in u: u['expiry_date'] = None
            if 'phone' not in u: u['phone'] = ''
            if 'note' not in u: u['note'] = ''
            if 'history' not in u: u['history'] = []
            if 'free_usage' not in u: u['free_usage'] = 0
            if 'total_usage' not in u: u['total_usage'] = 0
            if 'terms_agreed' not in u: u['terms_agreed'] = None
            if 'invite_code' not in u:
                u['invite_code'] = uid.upper() + str(random.randint(100, 999))
            if 'invited_by' not in u: u['invited_by'] = None
            if 'invite_rewards' not in u: u['invite_rewards'] = 0
            if 'invite_count' not in u: u['invite_count'] = 0
            if 'predictions_limit' not in u:
                if u.get('group') in ['super_admin', 'VIP', 'paid']:
                    u['predictions_limit'] = -1
                else:
                    u['predictions_limit'] = CONFIG["free_limit"]
            if 'level' not in u: u['level'] = '🥉 銅牌會員'
            if 'exp' not in u: u['exp'] = 0
            if 'badges' not in u: u['badges'] = []
            if 'virtual_balance' not in u: u['virtual_balance'] = 1000
            if 'last_claim_date' not in u: u['last_claim_date'] = ''
            if 'bets' not in u: u['bets'] = []
        save_users(users)
    return users

def save_users(users):
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return users[username]
    return None

def get_user(username):
    users = load_users()
    return users.get(username)

def get_remaining_predictions(username):
    user = get_user(username)
    if not user:
        return 0
    if user.get('group') in ['VIP', 'paid', 'super_admin']:
        return 9999
    limit = user.get('predictions_limit', CONFIG['free_limit'])
    used = user.get('free_usage', 0)
    return max(0, limit - used)

def update_user(username, updates):
    users = load_users()
    if username in users:
        users[username].update(updates)
        return save_users(users)
    return False

def log_admin_action(admin, action):
    logs = load_logs()
    if 'logs' not in logs: logs['logs'] = []
    logs['logs'].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'admin': admin, 'action': action
    })
    save_logs(logs)

def load_finance(): return load_json(FINANCE_FILE)
def save_finance(finance): return save_json(FINANCE_FILE, finance)
def load_promos(): return load_json(PROMO_FILE)
def save_promos(promos): return save_json(PROMO_FILE, promos)
def load_logs(): return load_json(LOG_FILE)
def save_logs(logs): return save_json(LOG_FILE, logs)
def load_accuracy(): return load_json(ACCURACY_FILE)
def save_accuracy(acc): return save_json(ACCURACY_FILE, acc)
def load_payment_proofs(): return load_json(PAYMENT_PROOFS_FILE)
def save_payment_proofs(data): return save_json(PAYMENT_PROOFS_FILE, data)

def generate_promo_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))

def generate_verification_code():
    return ''.join(random.choices('0123456789', k=6))

def get_plan_days(plan):
    if plan == 'day': return 1
    elif plan == 'month': return 30
    elif plan == 'quarter': return 90
    return 0

def get_plan_name(plan):
    return {'day': '日費', 'month': '月費', 'quarter': '季費'}.get(plan, '未知')

def get_plan_price(plan):
    if plan == 'day': return CONFIG['price_day']
    elif plan == 'month': return CONFIG['price_month']
    elif plan == 'quarter': return CONFIG['price_quarter']
    return 0

# ============================================================
# 付款功能
# ============================================================
def submit_payment_request(username, plan, final_price, discount_desc, promo_code_used):
    proof = load_payment_proofs()
    if 'proof_records' not in proof:
        proof['proof_records'] = []
    new_id = len(proof['proof_records']) + 1
    new_request = {
        "id": new_id, "username": username, "plan": plan,
        "plan_name": get_plan_name(plan), "final_price": final_price,
        "discount_desc": discount_desc, "promo_code": promo_code_used,
        "submitted_at": datetime.now().isoformat(), "status": "pending"
    }
    proof['proof_records'].append(new_request)
    save_payment_proofs(proof)
    log_user_activity(username, 'payment_submit', f"{get_plan_name(plan)} 金額${final_price}")
    return True, "申請已提交"

def get_all_pending_requests():
    proof = load_payment_proofs()
    return [{"username": req.get('username', ''), "request": req}
            for req in proof.get('proof_records', []) if req.get('status') == 'pending']

def approve_payment_request(username, request_id, admin_username):
    proof = load_payment_proofs()
    for req in proof.get('proof_records', []):
        if req.get('id') == request_id and req.get('status') == 'pending':
            users = load_users()
            if username in users:
                plan = req.get('plan', 'month')
                days = get_plan_days(plan) or 30
                expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
                users[username]['is_paid'] = True
                users[username]['group'] = 'VIP'
                users[username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                users[username]['expiry_date'] = expiry
                users[username]['plan'] = plan
                users[username]['predictions_limit'] = -1
                save_users(users)
                req['status'] = 'approved'
                req['approved_by'] = admin_username
                req['approved_at'] = datetime.now().isoformat()
                save_payment_proofs(proof)
                log_admin_action(admin_username, f"批准付款並升級 {username} 為 VIP（{plan}）")
                return True, f"已批准 {username} 的付款，到期日 {expiry}"
            return False, "用戶不存在"
    return False, "找不到該申請"

def reject_payment_request(username, request_id, admin_username):
    proof = load_payment_proofs()
    for req in proof.get('proof_records', []):
        if req.get('id') == request_id and req.get('status') == 'pending':
            req['status'] = 'rejected'
            req['rejected_by'] = admin_username
            req['rejected_at'] = datetime.now().isoformat()
            save_payment_proofs(proof)
            log_admin_action(admin_username, f"拒絕 {username} 的付款申請")
            return True, "已拒絕該申請"
    return False, "找不到該申請"

# ============================================================
# 付款牆
# ============================================================
def show_paywall():
    st.subheader("💳 選擇你嘅方案")
    plan_options = {
        "day": f"☀️ 日費  ${CONFIG['price_day']}   (1天)",
        "month": f"📆 月費  ${CONFIG['price_month']}  (30天)",
        "quarter": f"📅 季費  ${CONFIG['price_quarter']} (90天)"
    }
    if st.session_state.get('payment_just_submitted', False):
        st.success("✅ 付款申請已成功提交！管理員將盡快審核。")
        st.info("📩 提交後請 Telegram 通知管理員（可加快審核）")
        st.markdown("💬 Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**")
        if 'payment_detail' in st.session_state:
            st.write(st.session_state['payment_detail'])
        if st.button("返回主頁"):
            for key in ['payment_just_submitted', 'payment_detail']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.stop()
    with st.form(key="payment_form"):
        plan_choice = st.radio("請選擇付費方案：", options=list(plan_options.keys()),
                              format_func=lambda x: plan_options[x], horizontal=True, key="plan_radio")
        if plan_choice:
            st.info(f"💰 價格：${get_plan_price(plan_choice)}")
        promo_input = st.text_input("優惠碼（如有）", key="promo_input")
        st.divider()
        st.markdown("""
        **📤 付款方式：FPS 轉數快 `12345678`（SHTSN SYSTEM）**  
        💬 過數後請將截圖發送 Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**
        """)
        submitted = st.form_submit_button("📩 提交付款申請")
        if submitted:
            if not plan_choice:
                st.error("❌ 請選擇方案")
                return
            if not st.session_state.get('logged_in'):
                st.error("❌ 請先登入")
                return
            username = st.session_state.username
            final_price = get_plan_price(plan_choice)
            discount_desc = ""
            promo_code_used = None
            if promo_input:
                try:
                    promos = load_promos()
                    promo_data = promos.get(promo_input.strip())
                    if promo_data and not promo_data.get('used', False):
                        expiry = promo_data.get('expiry')
                        if expiry and datetime.fromisoformat(expiry) >= datetime.now():
                            discount_type = promo_data.get('discount_type', 'percentage')
                            discount_value = promo_data.get('discount_value', 0)
                            if discount_type == 'percentage':
                                final_price = final_price * (1 - discount_value / 100)
                                discount_desc = f"{discount_value}% 折扣"
                            elif discount_type == 'fixed':
                                final_price = max(0, final_price - discount_value)
                                discount_desc = f"減 ${discount_value}"
                            elif discount_type == 'free':
                                final_price = 0
                                discount_desc = "全免！"
                            final_price = round(final_price, 2)
                            promo_code_used = promo_input.strip()
                            st.success(f"✅ 優惠碼已套用！折扣後價格：${final_price}")
                except Exception as e:
                    st.warning(f"優惠碼處理出錯：{e}")
            success, msg = submit_payment_request(username, plan_choice, final_price, discount_desc, promo_code_used)
            if success:
                st.session_state['payment_just_submitted'] = True
                st.session_state['payment_detail'] = f"方案：{get_plan_name(plan_choice)}，金額：${final_price}"
                st.rerun()
            else:
                st.error(msg)

# ============================================================
# AI 自我學習
# ============================================================
def update_accuracy_with_results():
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        return 0, "沒有預測記錄"
    try:
        results_df = pd.read_csv('race_results_clean.csv', encoding='utf-8-sig')
        required = ['race_date', 'race_no', 'horse_name', 'finish_position']
        for col in required:
            if col not in results_df.columns:
                return 0, f"賽果檔案缺少必要欄位：{col}"
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
        results_df = results_df.dropna(subset=['race_date'])
        updated = 0
        for rec in records:
            if rec.get('actual_result') is not None:
                continue
            date_str = rec.get('date')
            race_no = rec.get('race')
            horse = rec.get('horse')
            if not date_str or not race_no or not horse:
                continue
            mask = (results_df['race_date'].dt.strftime('%Y-%m-%d') == date_str) & \
                   (results_df['race_no'] == race_no) & \
                   (results_df['horse_name'] == horse)
            matched = results_df.loc[mask]
            if not matched.empty:
                pos = matched.iloc[0]['finish_position']
                rec['actual_result'] = int(pos) if pd.notna(pos) else None
                rec['is_hit'] = (rec['actual_result'] == 1) if rec['actual_result'] is not None else None
                updated += 1
                if rec.get('is_hit') == True:
                    username = rec.get('username')
                    if username:
                        users = load_users()
                        if username in users:
                            for h in users[username].get('history', []):
                                if h.get('date') == rec.get('date') and h.get('race') == rec.get('race'):
                                    h['is_hit'] = True
                                    break
                            save_users(users)
                        update_user_exp(username, is_hit=True)
                    check_badges(username)
                    settle_bets(username, date_str, rec.get('race'), results_df)
        if updated > 0:
            save_accuracy(acc)
        return updated, f"成功比對 {updated} 條記錄"
    except Exception as e:
        return 0, f"比對失敗：{str(e)}"

# ============================================================
# 投注模擬器（完整版）
# ============================================================
def place_bet(username, race_date, race_no, horse_name, bet_amount, bet_type="win"):
    """
    投注：扣錢並寫入 users.json
    結果存入 st.session_state.bet_result
    """
    file_path = USER_DATA_FILE

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users = json.load(f)

        if username not in users:
            st.session_state.bet_result = ('error', "❌ 用戶不存在")
            return

        user = users[username]
        balance = user.get('virtual_balance', 0)

        if bet_amount <= 0:
            st.session_state.bet_result = ('error', "❌ 投注金額必須大於 0")
            return

        if bet_amount > balance:
            st.session_state.bet_result = ('error', f"❌ 餘額不足（餘額：${balance}）")
            return

        # 扣錢
        new_balance = balance - bet_amount
        user['virtual_balance'] = new_balance

        # 記錄投注
        if 'bets' not in user:
            user['bets'] = []
        user['bets'].append({
            "date": race_date,
            "race": race_no,
            "horse": horse_name,
            "amount": bet_amount,
            "bet_type": bet_type,
            "placed_at": datetime.now().isoformat(),
            "result": None,
            "payout": 0,
            "odds": None,
            "settled": False
        })

        # 寫入檔案
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

        # 驗證
        with open(file_path, 'r', encoding='utf-8') as f:
            verify = json.load(f)
        actual_balance = verify[username].get('virtual_balance', None)

        if actual_balance == new_balance:
            st.session_state.bet_result = ('success', f"✅ 已投注 ${bet_amount} 喺 {horse_name}，新餘額：${new_balance:,.0f}")
        else:
            # 回滾
            user['virtual_balance'] = balance
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            st.session_state.bet_result = ('error', f"❌ 儲存驗證失敗（預期 ${new_balance}，實際 ${actual_balance}）")

    except Exception as e:
        st.session_state.bet_result = ('error', f"❌ 投注錯誤：{str(e)}")


def show_betting_interface(username):
    """
    投注模擬器界面
    """
    if not username:
        st.info("請先登入")
        return

    # 顯示投注結果
    if 'bet_result' in st.session_state:
        msg_type, msg = st.session_state.bet_result
        if msg_type == 'success':
            st.success(msg)
        else:
            st.error(msg)
        del st.session_state.bet_result

    # 重新讀取 users.json
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        user = users.get(username, {})
        balance = user.get('virtual_balance', 0)
    except Exception as e:
        st.error(f"無法讀取 users.json：{e}")
        return

    st.subheader("💰 投注模擬器")
    st.caption("用虛擬幣體驗投注樂趣，唔使真錢！")

    # 餘額顯示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💎 虛擬幣結餘", f"${balance:,.0f}")
    with col2:
        today = datetime.now().strftime('%Y-%m-%d')
        if user.get('last_claim_date', '') != today and CONFIG.get("virtual_coin_enabled", True):
            if st.button("🎁 領取每日獎勵", use_container_width=True, key="claim_btn"):
                amount, msg = claim_daily_virtual_coin(username)
                if amount > 0:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.info(msg)
        else:
            st.success("✅ 今日已領取")
    with col3:
        st.caption(f"📅 每日派發：${CONFIG.get('daily_virtual_coin', 1000)}")

    st.divider()
    st.subheader("📝 投注")

    col_date, col_race = st.columns(2)
    with col_date:
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2026-09-06"), key="bet_date_input")
    with col_race:
        bet_race = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8, key="bet_race_select")

    if st.button("🔍 睇預測 & 投注", key="show_bet_options"):
        date_str = date.strftime('%Y-%m-%d')
        with st.spinner("載入預測..."):
            result, pool = run_prediction(date_str, bet_race)
            if result is not None and not result.empty:
                display_df = result[['horse_name', 'draw', '預測勝率', '值博指數', '信心指數']].copy()
                display_df.rename(columns={'horse_name': '馬名', 'draw': '檔位'}, inplace=True)
                display_df['預測勝率'] = display_df['預測勝率'].apply(lambda x: f"{x:.2%}")
                display_df['值博指數'] = display_df['值博指數'].apply(lambda x: f"{x:.4f}")
                st.dataframe(display_df, use_container_width=True)

                st.subheader("💸 落注")

                # 重新讀取最新餘額
                try:
                    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                        temp_users = json.load(f)
                    current_balance = temp_users.get(username, {}).get('virtual_balance', 0)
                except:
                    current_balance = 0

                with st.form(key="place_bet_form"):
                    horse_options = result['horse_name'].tolist()
                    selected_horse = st.selectbox("揀馬", horse_options, key="bet_horse_select")

                    max_bet = int(current_balance) if current_balance > 0 else 1
                    bet_amount = st.number_input(
                        "投注金額",
                        min_value=1,
                        max_value=max_bet,
                        value=min(100, max_bet),
                        step=10,
                        key="bet_amount_input"
                    )
                    st.caption(f"💰 當前餘額：${current_balance:,.0f}")

                    submit_bet = st.form_submit_button("✅ 確認投注", type="primary")

                    if submit_bet:
                        if bet_amount > current_balance:
                            st.error(f"❌ 餘額不足（餘額：${current_balance:,.0f}）")
                        else:
                            place_bet(username, date_str, bet_race, selected_horse, bet_amount)
                            st.rerun()
            else:
                st.warning("無法載入預測數據")

    st.divider()
    st.subheader("📋 我的投注記錄")

    # 重新讀取投注記錄
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        user = users.get(username, {})
        bets = user.get('bets', [])
    except:
        bets = []

    if bets:
        df_bets = pd.DataFrame(bets[-20:][::-1])
        display_cols = ['date', 'race', 'horse', 'amount', 'result', 'payout']
        available_cols = [col for col in display_cols if col in df_bets.columns]
        st.dataframe(df_bets[available_cols], use_container_width=True)

        settled = [b for b in bets if b.get('settled', False)]
        wins = [b for b in settled if b.get('result') == 'win']
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("📊 總投注", len(bets))
        col_s2.metric("✅ 已結算", len(settled))
        col_s3.metric("🏆 命中", len(wins))
        col_s4.metric("📈 命中率", f"{len(wins)/len(settled)*100:.1f}%" if settled else "0%")
    else:
        st.info("📭 尚未有任何投注記錄")


def settle_bets(username, race_date, race_no, results_df):
    """
    結算投注：如果投注馬跑第一，加錢
    """
    file_path = USER_DATA_FILE

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users = json.load(f)

        if username not in users:
            return

        user = users[username]
        bets = user.get('bets', [])
        updated = False

        for bet in bets:
            if bet.get('settled', False):
                continue
            if bet.get('date') != race_date or bet.get('race') != race_no:
                continue

            horse = bet.get('horse')

            matched = results_df[
                (results_df['race_date'].dt.strftime('%Y-%m-%d') == race_date) &
                (results_df['race_no'] == race_no) &
                (results_df['horse_name'] == horse)
            ]

            if not matched.empty:
                pos = matched.iloc[0]['finish_position']
                is_win = (pos == 1)
                bet['result'] = 'win' if is_win else 'lose'
                bet['settled'] = True

                if is_win:
                    odds = matched.iloc[0].get('win_odds', 4.0)
                    if pd.isna(odds) or odds <= 0:
                        odds = 4.0
                    bet['odds'] = float(odds)
                    payout = bet['amount'] * odds
                    bet['payout'] = payout
                    user['virtual_balance'] = user.get('virtual_balance', 0) + payout
                    updated = True

        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"結算錯誤：{e}")

def adjust_model_weights():
    acc = load_accuracy()
    records = acc.get('records', [])
    total = len([r for r in records if r.get('is_hit') is not None])
    hit = sum(1 for r in records if r.get('is_hit') is True)
    hit_rate = hit / total if total > 0 else 0
    config = load_system_config()
    current_xgb = config.get('xgb_weight', 25)
    current_cat = config.get('cat_weight', 1)
    if hit_rate >= 0.6:
        new_xgb, new_cat = min(40, current_xgb + 3), max(1, current_cat - 1)
    elif hit_rate >= 0.5:
        new_xgb, new_cat = min(35, current_xgb + 1), max(1, current_cat)
    elif hit_rate >= 0.4:
        new_xgb, new_cat = max(15, current_xgb - 2), min(10, current_cat + 2)
    elif hit_rate >= 0.3:
        new_xgb, new_cat = max(10, current_xgb - 5), min(15, current_cat + 5)
    else:
        new_xgb, new_cat = max(5, current_xgb - 8), min(20, current_cat + 8)
    config['xgb_weight'] = max(1, min(50, new_xgb))
    config['cat_weight'] = max(1, min(30, new_cat))
    config['last_weight_update'] = datetime.now().isoformat()
    config['last_hit_rate'] = hit_rate
    save_system_config(config)
    return {'xgb_weight': config['xgb_weight'], 'cat_weight': config['cat_weight'],
            'hit_rate': hit_rate, 'total': total, 'hit': hit}

def update_ai_accuracy():
    ai_file = "ai_predictions.json"
    results_file = "race_results_clean.csv"
    if not os.path.exists(ai_file):
        return 0, "未有 AI 預測記錄"
    if not os.path.exists(results_file):
        return 0, "未有賽果數據"
    with open(ai_file, 'r', encoding='utf-8') as f:
        ai_data = json.load(f)
    results_df = pd.read_csv(results_file, encoding='utf-8-sig')
    if not all(col in results_df.columns for col in ['race_date', 'race_no', 'horse_name', 'finish_position']):
        return 0, "賽果檔案欄位不正確"
    results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
    results_df['race_date_str'] = results_df['race_date'].dt.strftime('%Y-%m-%d')
    hit_count = 0
    total_count = 0
    for key, pred in ai_data.items():
        date_str = pred.get('date')
        race_no = pred.get('race')
        top_horse = pred.get('top_horse')
        if not date_str or not race_no or not top_horse:
            continue
        matched = results_df[
            (results_df['race_date_str'] == date_str) &
            (results_df['race_no'] == race_no) &
            (results_df['horse_name'] == top_horse)
        ]
        total_count += 1
        if not matched.empty:
            finish_pos = matched.iloc[0].get('finish_position')
            if pd.notna(finish_pos) and finish_pos == 1:
                hit_count += 1
                pred['is_hit'] = True
            else:
                pred['is_hit'] = False
        else:
            pred['is_hit'] = None
    with open(ai_file, 'w', encoding='utf-8') as f:
        json.dump(ai_data, f, ensure_ascii=False, indent=2)
    hit_rate = hit_count / total_count if total_count > 0 else 0
    return hit_count, f"命中 {hit_count}/{total_count} ({hit_rate:.1%})"

# ============================================================
# 特徵工程
# ============================================================
FEATURES_EN = [
    'draw', 'act_wt', 'distance', 'rtg', 'avg_rank_last3',
    'jockey_win_rate_50', 'trainer_win_rate_50', 'distance_win_rate', 'distance_avg_rank',
    'win_odds', 'weight_change', 'jockey_trainer_win_rate', 'course_win_rate', 'course_avg_rank',
    'days_since_last_run', 'odds_rank_in_race', 'rtg_change', 'jockey_horse_win_rate',
    'races_last14days', 'going_win_rate', 'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
    'early_pace', 'finish_speed', 'last_trial_rank', 'last_trial_time',
    'jockey_win_rate_5', 'jockey_win_rate_10', 'draw_win_rate',
    'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
    'total_injuries', 'injury_severity'
]

EXPECTED_FEATURES = [
    'draw', 'weight', 'distance', 'Rtg.', '近3場平均名次',
    '騎師近50場勝率', '練馬師近50場勝率', '同路程歷史勝率', '同路程歷史平均名次',
    'win_odds', '體重變化', '騎練組合勝率', '詳細賽道歷史勝率', '詳細賽道歷史平均名次',
    '出賽相隔日數', '賠率場次排名', '評分變化', '騎馬合作勝率', '近14日出賽次數',
    '場地狀況勝率', '試閘歷史勝率', '父系歷史勝率', '父系同程勝率',
    '前速指標', '後勁指標', '最近試閘名次', '最近試閘時間',
    '騎師近5場勝率', '騎師近10場勝率', '檔位勝率', '最近傷患日數',
    '過去30日內有傷患', '過去60日內有傷患', '過去90日內有傷患',
    '傷患總次數', '傷患嚴重程度'
]

def standardize_columns_safe(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance', '場地': 'going',
        '檔位': 'draw', '評分': 'rtg', '馬匹編號': 'horse_id', '馬匹ID': 'horse_id',
        '馬號': 'horse_no', '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course', '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name', '賠率': 'win_odds', '獨贏賠率': 'win_odds',
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    if '比賽日期' in df.columns and 'race_date' not in df.columns:
        df.rename(columns={'比賽日期': 'race_date'}, inplace=True)
    return df

# ============================================================
# 彩池推薦
# ============================================================
def generate_pool_recommendations(df, top_n=6):
    if df.empty:
        return "⚠️ 無數據"
    horse_names = df['horse_name'].tolist()
    probs = df['預測勝率'].tolist()
    def combo_score(indices):
        score = 1.0
        for i in indices:
            score *= probs[i]
        return score / len(indices)

    rec = ""
    if len(horse_names) >= 1:
        rec += "【獨贏】\n"
        rec += f"  {horse_names[0]}（{probs[0]:.1%}）\n"

    rec += "\n【位置】\n"
    for i in range(min(4, len(horse_names))):
        rec += f"  {horse_names[i]}（{probs[i]:.1%}）\n"

    rec += "\n【連贏】\n"
    pairs = []
    for i in range(min(len(horse_names), 4)):
        for j in range(i+1, min(len(horse_names), 5)):
            pairs.append((combo_score([i, j]), i, j))
    pairs.sort(reverse=True)
    for _, i, j in pairs[:3]:
        rec += f"  {horse_names[i]} + {horse_names[j]}\n"

    rec += "\n【位置Q】\n"
    q_pairs = []
    for i in range(min(len(horse_names), 5)):
        for j in range(i+1, min(len(horse_names), 7)):
            if j < len(horse_names):
                q_pairs.append((combo_score([i, j]), i, j))
    q_pairs.sort(reverse=True)
    for _, i, j in q_pairs[:6]:
        rec += f"  {horse_names[i]} + {horse_names[j]}\n"

    rec += "\n【三重彩 / 單T】\n"
    tierce = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                if i != j and i != k and j != k:
                    tierce.append((combo_score([i, j, k]), i, j, k))
    tierce.sort(reverse=True)
    for _, i, j, k in tierce[:3]:
        rec += f"  {horse_names[i]} > {horse_names[j]} > {horse_names[k]}\n"

    rec += "\n【四重彩】\n"
    quartet = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                for l in range(min(len(horse_names), 7)):
                    if len(set([i, j, k, l])) == 4:
                        quartet.append((combo_score([i, j, k, l]), i, j, k, l))
    quartet.sort(reverse=True)
    for _, i, j, k, l in quartet[:3]:
        rec += f"  {horse_names[i]} > {horse_names[j]} > {horse_names[k]} > {horse_names[l]}\n"

    return rec

# ============================================================
# 核心預測函數
# ============================================================
def run_prediction(date_str, race_no):
    if not os.path.exists("racecard_uploaded.csv"):
        st.error("❌ 找不到 racecard_uploaded.csv")
        return None, None
    try:
        df = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None, None

    rename_map = {'馬名': 'horse_name', '檔位': 'draw', '場次': 'race_no',
        '比賽日期': 'race_date', '騎師': 'jockey', '練馬師': 'trainer',
        '負磅': 'weight', '馬號': 'horse_no', '賠率': 'win_odds',
        '獨贏賠率': 'win_odds', 'Odds': 'win_odds'}
    for old, new in rename_map.items():
        if old in df.columns and old != new:
            df.rename(columns={old: new}, inplace=True)

    if 'race_date' not in df.columns:
        st.error("❌ 缺少 '比賽日期' 欄位")
        return None, None

    df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
    df = df.dropna(subset=['race_date'])
    df['race_date_str'] = df['race_date'].dt.strftime('%Y-%m-%d')

    available_dates = sorted(df['race_date_str'].unique())
    if date_str not in available_dates:
        st.warning(f"⚠️ 日期 {date_str} 無數據，改用 {available_dates[-1]}")
        date_str = available_dates[-1]

    df_date = df[df['race_date_str'] == date_str]
    if race_no not in df_date['race_no'].unique():
        available_races = sorted(df_date['race_no'].unique())
        if available_races:
            st.info(f"🔄 場次 {race_no} 無數據，改用第 {available_races[0]} 場")
            race_no = available_races[0]
        else:
            st.error("❌ 無場次")
            return None, None

    filtered = df_date[df_date['race_no'] == race_no].copy()
    st.success(f"✅ 成功載入 {date_str} 第 {race_no} 場，共 {len(filtered)} 匹馬")

    # 自動偵測賠率欄位
    odds_col = None
    for col in ['win_odds', '賠率', '獨贏賠率', 'odds', 'WinOdds', 'Odds']:
        if col in filtered.columns:
            odds_col = col
            break

    if odds_col is not None:
        win_odds = pd.to_numeric(filtered[odds_col], errors='coerce').fillna(4.0)
    else:
        st.warning("⚠️ 排位表冇賠率欄位，將使用預設賠率 4.0")
        win_odds = pd.Series([4.0] * len(filtered), index=filtered.index)

    win_odds = win_odds.replace(0, 4.0)
    inv_odds = 1 / win_odds
    final_pred = inv_odds / inv_odds.sum()

    result_df = filtered[['horse_name', 'draw', 'weight', 'jockey', 'trainer']].copy()
    result_df['預測勝率'] = final_pred
    result_df['值博指數'] = result_df['預測勝率'] * 10
    result_df['信心指數'] = result_df['預測勝率'].apply(
        lambda x: '⭐⭐⭐ 高' if x > 0.2 else '⭐⭐ 中' if x > 0.1 else '⭐ 低')
    result_df = result_df.sort_values('預測勝率', ascending=False)
    result_df['horse_name'] = result_df['horse_name'].fillna('未知').astype(str)

    # 儲存 AI 預測
    ai_file = "ai_predictions.json"
    ai_data = {}
    if os.path.exists(ai_file):
        try:
            with open(ai_file, 'r', encoding='utf-8') as f:
                ai_data = json.load(f)
        except:
            ai_data = {}

    key = f"{date_str}_{race_no}"
    ai_data[key] = {
        "date": date_str, "race": int(race_no),
        "top_horse": str(result_df.iloc[0]['horse_name']),
        "top_prob": float(result_df.iloc[0]['預測勝率']),
        "all_horses": result_df['horse_name'].tolist(),
        "predicted_at": datetime.now().isoformat()
    }
    try:
        with open(ai_file, 'w', encoding='utf-8') as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)
        st.success(f"✅ AI 預測已儲存（共 {len(ai_data)} 筆記錄）")
        if st.session_state.get('username'):
            log_user_activity(st.session_state.username, 'predict', f"{date_str} 第{race_no}場")
    except Exception as e:
        st.error(f"❌ 儲存預測失敗：{e}")

    full_pool_text = generate_pool_recommendations(result_df)
    config = load_system_config()
    enable_vip_content = config.get("enable_vip_content", True)
    username = st.session_state.get('username')
    user_group = 'free'
    if username:
        users = load_users()
        user_group = users.get(username, {}).get('group', 'free')
    is_vip = user_group in ['VIP', 'super_admin']
    if enable_vip_content and not is_vip:
        lines = full_pool_text.split('\n')
        filtered_lines = []
        skip = False
        for line in lines:
            if '【三重彩' in line or '【四重彩' in line:
                skip = True
                continue
            if skip and line.strip() == '':
                skip = False
                continue
            if not skip:
                filtered_lines.append(line)
        pool_text = '\n'.join(filtered_lines)
        pool_text += "\n\n🔒 三重彩 / 四重彩 為 VIP 專屬內容，請升級至 VIP 查看"
    else:
        pool_text = full_pool_text

    return result_df, pool_text

# ============================================================
# 用戶預測紀錄
# ============================================================
def record_prediction(username, date_str, race_no, horse_name, predicted_prob=None):
    users = load_users()
    if username in users:
        if 'history' not in users[username]:
            users[username]['history'] = []
        users[username]['history'].append({
            'date': date_str, 'race': race_no, 'horse': horse_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_prob': predicted_prob, 'is_hit': None
        })
        save_users(users)
        acc = load_accuracy()
        if 'records' not in acc:
            acc['records'] = []
        acc['records'].append({
            'username': username, 'date': date_str, 'race': race_no, 'horse': horse_name,
            'predicted_at': datetime.now().isoformat(), 'actual_result': None, 'is_hit': None
        })
        save_accuracy(acc)
        update_user_exp(username, is_hit=False)

def get_user_stats(username):
    users = load_users()
    if username not in users:
        return {'total_predictions': 0, 'free_used': 0, 'is_paid': False, 'group': 'free', 'plan': None}
    user = users[username]
    return {
        'total_predictions': len(user.get('history', [])),
        'free_used': user.get('free_usage', 0),
        'is_paid': user.get('is_paid', False),
        'group': user.get('group', 'free'),
        'plan': user.get('plan', None)
    }

# ============================================================
# 投注模擬器
# ============================================================
def place_bet(username, race_date, race_no, horse_name, bet_amount, bet_type="win"):
    """
    投注：扣錢並寫入 users.json，立即驗證
    """
    import os
    file_path = USER_DATA_FILE  # 即 'users.json'

    try:
        # 1. 讀取現有用戶數據
        with open(file_path, 'r', encoding='utf-8') as f:
            users = json.load(f)

        if username not in users:
            return False, "用戶不存在"

        user = users[username]
        balance = user.get('virtual_balance', 0)

        if bet_amount <= 0:
            return False, "投注金額必須大於 0"
        if bet_amount > balance:
            return False, f"餘額不足（餘額：${balance}）"

        # 2. 扣錢
        new_balance = balance - bet_amount
        user['virtual_balance'] = new_balance

        # 3. 記錄投注
        if 'bets' not in user:
            user['bets'] = []
        user['bets'].append({
            "date": race_date,
            "race": race_no,
            "horse": horse_name,
            "amount": bet_amount,
            "bet_type": bet_type,
            "placed_at": datetime.now().isoformat(),
            "result": None,
            "payout": 0,
            "odds": None,
            "settled": False
        })

        # 4. 寫入檔案
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
            f.flush()

        # 5. 立即驗證寫入是否成功
        with open(file_path, 'r', encoding='utf-8') as f:
            verify = json.load(f)

        actual_balance = verify[username].get('virtual_balance', None)

        if actual_balance == new_balance:
            return True, f"✅ 已投注 ${bet_amount} 喺 {horse_name}，新餘額：${new_balance:,.0f}"
        else:
            # 驗證失敗，回滾
            user['virtual_balance'] = balance
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            return False, f"❌ 儲存驗證失敗（預期 ${new_balance}，實際 ${actual_balance}）"

    except Exception as e:
        return False, f"❌ 投注錯誤：{str(e)}"

# ============================================================
# 排行榜
# ============================================================
def show_leaderboard():
    st.subheader("🏆 投注排行榜")
    users = load_users()
    leaderboard_data = []
    for username, user in users.items():
        if username == "admin" and not user.get('bets'):
            continue
        bets = user.get('bets', [])
        if not bets:
            continue
        settled = [b for b in bets if b.get('settled', False)]
        wins = [b for b in settled if b.get('result') == 'win']
        hit_rate = len(wins) / len(settled) if settled else 0
        total_staked = sum(b.get('amount', 0) for b in bets)
        total_payout = sum(b.get('payout', 0) for b in bets)
        leaderboard_data.append({
            "用戶": username, "總投注": len(bets), "命中": len(wins),
            "命中率": hit_rate, "盈利": total_payout - total_staked,
            "結餘": user.get('virtual_balance', 0)
        })
    if not leaderboard_data:
        st.info("📭 暫時未有投注記錄")
        return
    df = pd.DataFrame(leaderboard_data)
    df = df.sort_values('盈利', ascending=False).reset_index(drop=True)
    st.subheader("💰 總盈利榜")
    df_display = df[['用戶', '盈利', '命中率', '總投注', '命中', '結餘']].copy()
    df_display['盈利'] = df_display['盈利'].apply(lambda x: f"${x:,.0f}")
    df_display['命中率'] = df_display['命中率'].apply(lambda x: f"{x:.1%}")
    st.dataframe(df_display, use_container_width=True)
    if len(df) >= 2:
        fig = px.bar(df.head(10), x='用戶', y='盈利', title='Top 10 用戶盈利',
                     color='盈利', color_continuous_scale='RdYlGn',
                     text=df.head(10)['盈利'].apply(lambda x: f"${x:,.0f}"))
        fig.update_traces(textposition='outside')
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 用戶儀表板
# ============================================================
def show_user_dashboard(username):
    if not username:
        return
    try:
        stats = get_user_stats(username)
    except:
        stats = {'total_predictions': 0, 'free_used': 0, 'is_paid': False, 'group': 'free', 'plan': None}
    users = load_users()
    user_data = users.get(username, {})
    group = user_data.get('group', 'free')
    is_paid = user_data.get('is_paid', False)
    plan = user_data.get('plan', None)
    invite_code = user_data.get('invite_code', '')
    invite_count = user_data.get('invite_count', 0)
    invite_rewards = user_data.get('invite_rewards', 0)
    level = user_data.get('level', '🥉 銅牌會員')
    exp = user_data.get('exp', 0)
    badges = user_data.get('badges', [])
    next_level_exp = get_level_info(exp)[1]
    virtual_balance = user_data.get('virtual_balance', 0)
    if group == 'super_admin':
        level_display = "👑 超級管理員"
    elif group == 'VIP':
        level_display = "👑 VIP"
    elif is_paid:
        level_display = "💎 付費用戶"
    else:
        level_display = "🆓 免費用戶"
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👤 用戶", username)
    col2.metric("🏷️ 級別", level_display)
    total_pred = int(stats.get('total_predictions', 0))
    col3.metric("📊 總預測次數", total_pred)
    limit = user_data.get('predictions_limit', CONFIG['free_limit'])
    if limit == -1:
        col4.metric("📊 剩餘場次", "♾️ 無限")
    else:
        col4.metric("📊 剩餘場次", max(0, limit - user_data.get('free_usage', 0)))
    col5.metric("💰 虛擬幣", f"${virtual_balance:,.0f}")
    st.markdown("---")
    st.subheader("🏅 用戶等級 & 勳章")
    col_level1, col_level2, col_level3 = st.columns(3)
    with col_level1:
        st.metric("🏅 當前等級", level)
    with col_level2:
        if next_level_exp:
            progress = min(100, int((exp / next_level_exp) * 100))
            st.metric("📊 經驗值", f"{exp} / {next_level_exp}")
            st.progress(progress / 100)
        else:
            st.metric("📊 經驗值", f"{exp}（已滿級）")
    with col_level3:
        st.metric("🎖️ 勳章數量", len(badges))
    if badges:
        st.write("🏅 已獲得勳章：")
        badge_cols = st.columns(4)
        for idx, badge in enumerate(badges):
            with badge_cols[idx % 4]:
                st.markdown(f"**{badge}**")
    st.markdown("---")
    if plan:
        st.caption(f"📌 當前方案：{get_plan_name(plan)}")
    if CONFIG.get("enable_invite_reward", True):
        st.subheader("🎁 邀請獎勵")
        col_inv1, col_inv2, col_inv3 = st.columns(3)
        with col_inv1:
            st.caption(f"你的邀請碼：**{invite_code}**")
        with col_inv2:
            st.caption(f"已成功邀請 **{invite_count}** 位朋友")
        with col_inv3:
            st.caption(f"已獲得獎勵次數：**{invite_rewards}** 次")
    st.markdown("---")
    st.subheader("📊 預測統計")
    today = datetime.now().strftime('%Y-%m-%d')
    history = user_data.get('history', [])
    today_count = sum(1 for h in history if h.get('date') == today)
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        st.metric("📈 總預測", total_pred)
    with col_p2:
        st.metric("📅 今日已用", today_count)
    with col_p3:
        if limit == -1:
            st.metric("🔮 剩餘次數", "♾️ 無限")
        else:
            st.metric("🔮 剩餘次數", max(0, limit - user_data.get('free_usage', 0)))
    with col_p4:
        if st.button("🚀 去預測", use_container_width=True, key="quick_predict"):
            st.session_state.page = "預測"
            st.rerun()


# ============================================================
# 登入/註冊
# ============================================================
def login_page():
    st.title("🔐 登入 / 註冊")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 登入", use_container_width=True):
            st.session_state.page_mode = "login"
    with col2:
        if st.button("📝 註冊", use_container_width=True):
            st.session_state.page_mode = "register"
    mode = st.session_state.get("page_mode", "login")
    if mode == "login":
        with st.form("login_form"):
            username = st.text_input("用戶名稱", key="login_user")
            password = st.text_input("密碼", type="password", key="login_pass")
            if st.form_submit_button("登入"):
                user = authenticate(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = user.get('group', 'free')
                    st.session_state.usage_count = user.get('free_usage', 0)
                    log_user_activity(username, 'login', '用戶登入')
                    st.rerun()
                else:
                    st.error("❌ 用戶名稱或密碼錯誤")
    else:
        st.subheader("📝 註冊新帳號")
        with st.form("register_form"):
            new_user = st.text_input("用戶名稱（最少 3 個字）", key="reg_user")
            phone = st.text_input("手機號碼（可選）", key="reg_phone")
            new_pass = st.text_input("密碼", type="password", key="reg_pass")
            new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
            if CONFIG.get("enable_invite_reward", True):
                invite_code_input = st.text_input("邀請碼（如有）", key="reg_invite_code", placeholder="輸入朋友的邀請碼")
            else:
                invite_code_input = None
            col1, col2 = st.columns([3, 1])
            with col1:
                verify_code_input = st.text_input("驗證碼", key="reg_verify", placeholder="輸入 6 位數字", max_chars=6)
            with col2:
                if st.form_submit_button("📨 獲取驗證碼", type="secondary"):
                    code = generate_verification_code()
                    st.session_state['reg_verify_code'] = code
                    st.session_state['reg_verify_expiry'] = datetime.now() + timedelta(minutes=CONFIG.get('verification_expiry', 5))
                    st.info(f"📧 你嘅驗證碼係：**{code}**（有效期 5 分鐘）")
            st.divider()
            with st.expander("📜 服務條款（請仔細閱讀）"):
                st.markdown("""
                **SHTSN 賽馬預測系統 服務條款**
                **1. 服務說明**
                本系統提供賽馬預測數據及分析，僅供參考及娛樂用途，並非投注建議。
                **2. 用戶責任**
                - 用戶必須年滿 18 歲。
                - 用戶需確保所提供嘅資料真實、準確、完整。
                **3. 免責聲明**
                - 預測結果僅為演算法分析，不構成任何形式嘅投資建議或保證。
                - 本系統不保證預測準確度，亦不對用戶因使用本系統而產生嘅任何損失負責。
                **4. 付款與退款**
                - 用戶付款後即表示同意購買所選方案。
                - 付款後不設退款，除非系統因技術問題未能提供服務。
                **5. 帳戶安全**
                - 用戶需自行保管帳號及密碼，任何經由帳戶進行嘅活動均視為用戶本人所為。
                **6. 終止服務**
                - 管理員保留隨時終止或暫停用戶帳戶嘅權利。
                **7. 條款修訂**
                本系統有權隨時修訂服務條款，修訂後會於系統內公告。
                **8. 聯絡我們**
                如有任何疑問，可透過 Telegram 聯絡管理員：@bryhjdjbrbxibvrjskofndhiebdpaq
                **最後更新日期：2026 年 8 月 25 日**
                """)
            agree_terms = st.checkbox("✅ 我已閱讀並同意上述服務條款", key="agree_terms")
            submitted = st.form_submit_button("註冊")
            if submitted:
                if len(new_user) < 3:
                    st.error("❌ 用戶名稱至少 3 個字")
                elif new_pass != new_pass2:
                    st.error("❌ 密碼不一致")
                elif len(new_pass) < 4:
                    st.error("❌ 密碼至少 4 個字")
                elif 'reg_verify_code' not in st.session_state or \
                     verify_code_input != st.session_state['reg_verify_code'] or \
                     datetime.now() > st.session_state.get('reg_verify_expiry', datetime.now()):
                    st.error("❌ 驗證碼無效或已過期，請重新獲取")
                elif not agree_terms:
                    st.error("❌ 請先閱讀並同意服務條款，方可註冊")
                else:
                    users = load_users()
                    if new_user in users:
                        st.error("❌ 用戶名稱已被使用")
                    else:
                        invited_by = None
                        if CONFIG.get("enable_invite_reward", True) and invite_code_input:
                            for uid, u in users.items():
                                if u.get('invite_code') == invite_code_input:
                                    invited_by = uid
                                    break
                            if not invited_by:
                                st.warning("⚠️ 邀請碼無效，請確認後再試。")
                        new_user_data = {
                            'password': new_pass, 'phone': phone, 'is_paid': False,
                            'paid_date': None, 'expiry_date': None, 'free_usage': 0,
                            'total_usage': 0, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'note': '', 'group': 'free', 'plan': None,
                            'predictions_limit': CONFIG["free_limit"], 'history': [],
                            'terms_agreed': datetime.now().isoformat(),
                            'invite_code': new_user.upper() + str(random.randint(100, 999)),
                            'invited_by': invited_by, 'invite_rewards': 0, 'invite_count': 0,
                            'level': '🥉 銅牌會員', 'exp': 0, 'badges': [],
                            'virtual_balance': CONFIG.get('daily_virtual_coin', 1000),
                            'last_claim_date': '', 'bets': []
                        }
                        users[new_user] = new_user_data
                        save_users(users)
                        if CONFIG.get("enable_invite_reward", True) and invited_by:
                            inviter = users.get(invited_by)
                            if inviter:
                                reward_inviter = CONFIG.get("invite_reward_inviter", 1)
                                reward_invitee = CONFIG.get("invite_reward_invitee", 1)
                                if inviter['predictions_limit'] != -1:
                                    inviter['predictions_limit'] += reward_inviter
                                inviter['invite_count'] = inviter.get('invite_count', 0) + 1
                                inviter['invite_rewards'] = inviter.get('invite_rewards', 0) + reward_inviter
                                if new_user_data['predictions_limit'] != -1:
                                    new_user_data['predictions_limit'] += reward_invitee
                                new_user_data['invite_rewards'] = reward_invitee
                                save_users(users)
                                st.success(f"✅ 註冊成功！你同邀請人各獲得 {reward_invitee} 次免費預測獎勵！")
                            else:
                                st.success("✅ 註冊成功！")
                        else:
                            st.success("✅ 註冊成功！")
                        st.session_state.page_mode = "login"
                        st.rerun()

# ============================================================
# 賽事日曆
# ============================================================
def get_future_races():
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df = standardize_columns_safe(df)
        if 'race_date' in df.columns:
            df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
            df = df.dropna(subset=['race_date'])
            today = datetime.now().date()
            future = df[df['race_date'].dt.date >= today]
            if not future.empty:
                dates = sorted(future['race_date'].dt.date.unique())
                race_courses = []
                for d in dates:
                    course = future[future['race_date'].dt.date == d]['race_course'].iloc[0] if 'race_course' in future.columns else '賽馬'
                    race_courses.append(course)
                return dates, race_courses
    except Exception as e:
        print(f"讀取排位表失敗：{e}")
    return [], []

def display_race_calendar():
    dates, courses = get_future_races()
    if not dates:
        st.info("📭 暫時未有未來賽事資料")
        return
    next_date = dates[0]
    next_course = courses[0] if courses else "賽馬"
    today = datetime.now().date()
    delta = (next_date - today).days
    if delta > 0:
        time_str = f"⏳ 仲有 **{delta} 天**"
    elif delta == 0:
        hours = (datetime.combine(next_date, datetime.min.time()) - datetime.now()).seconds // 3600
        time_str = f"⏳ 今日開跑！仲有約 **{hours} 小時**"
    else:
        time_str = "⏳ 已過期"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1a237e, #0d47a1); border-radius: 12px; padding: 15px 20px; color: white; margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="font-size: 20px;">🏇 下一場賽事</span><br>
                <span style="font-size: 16px; opacity: 0.9;">{next_course}　📅 {next_date.strftime('%Y年%m月%d日')}</span>
            </div>
            <div style="font-size: 22px; font-weight: bold; background: rgba(255,255,255,0.15); padding: 8px 20px; border-radius: 30px;">
                {time_str}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if len(dates) > 1:
        st.caption("📅 未來賽事一覽")
        for i in range(1, min(len(dates), 4)):
            d = dates[i]
            c = courses[i] if i < len(courses) else "賽馬"
            delta_i = (d - today).days
            st.write(f"• {d.strftime('%Y-%m-%d')}　{c}　（還有 {delta_i} 天）")

# ============================================================
# 後台：儀表板
# ============================================================
def admin_dashboard():
    st.subheader("📊 系統儀表板")
    st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    users = load_users()
    acc = load_accuracy()
    finance = load_finance()
    records = acc.get('records', [])
    payment_proofs = load_payment_proofs()
    total_users = len(users)
    today = datetime.now().date()
    today_new_users = sum(1 for u in users.values() if u.get('created_at', '').startswith(str(today)))
    total_income = finance.get('total_income', 0)
    pending_payments = len([p for p in payment_proofs.get('proof_records', []) if p.get('status') == 'pending'])
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("👤 總用戶", total_users)
    col2.metric("📈 今日新增", today_new_users)
    col3.metric("💰 總收入", f"${total_income:.2f}")
    col4.metric("📊 總預測", len(records))
    total = len([r for r in records if r.get('is_hit') is not None])
    hit = sum(1 for r in records if r.get('is_hit') is True)
    hit_rate = hit/total if total>0 else 0
    col5.metric("🎯 命中率", f"{hit_rate:.2%}")
    col6.metric("⏳ 待審核付款", pending_payments, delta="需處理" if pending_payments > 0 else None)
    st.divider()
    st.subheader("⚠️ 待辦事項")
    col_w1, col_w2, col_w3 = st.columns(3)
    with col_w1:
        if pending_payments > 0:
            st.warning(f"⏳ 有 {pending_payments} 筆付款申請待審核")
        else:
            st.success("✅ 沒有待審核付款")
    with col_w2:
        vip_expiring = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    exp = pd.to_datetime(u['expiry_date'])
                    days_left = (exp - datetime.now()).days
                    if 0 < days_left <= 3:
                        vip_expiring.append(f"{uid}({days_left}天)")
                except:
                    pass
        if vip_expiring:
            st.warning(f"⚠️ 即將到期 VIP：{', '.join(vip_expiring)}")
        else:
            st.success("✅ 沒有即將到期 VIP")
    with col_w3:
        files_missing = []
        for f in ['users.json', 'system_config.json', 'accuracy.json']:
            if not os.path.exists(f):
                files_missing.append(f)
        if files_missing:
            st.error(f"❌ 缺少檔案：{', '.join(files_missing)}")
        else:
            st.success("✅ 系統檔案正常")
    st.divider()
    col_ch1, col_ch2 = st.columns(2)
    with col_ch1:
        st.subheader("📈 用戶增長（最近7日）")
        if users:
            df_users = pd.DataFrame.from_dict(users, orient='index')
            if 'created_at' in df_users.columns:
                df_users['created_at'] = pd.to_datetime(df_users['created_at'], errors='coerce')
                df_users = df_users.dropna(subset=['created_at'])
                df_users['date'] = df_users['created_at'].dt.date
                last_7 = datetime.now().date() - timedelta(days=7)
                df_recent = df_users[df_users['date'] >= last_7]
                if not df_recent.empty:
                    daily = df_recent.groupby('date').size().reset_index(name='new_users')
                    fig = px.bar(daily.sort_values('date'), x='date', y='new_users', title='每日新增用戶')
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("最近7日沒有新用戶")

# ============================================================
# 後台：自動維護
# ============================================================
def admin_auto_maintenance():
    st.subheader("🤖 自動維護")
    st.info("一鍵執行所有維護任務")
    tasks = ["🔄 比對賽果 + 更新統計", "⚖️ 調整模型權重", "⏰ 檢查並終止過期會員",
             "📊 同步用戶數據", "📝 檢查系統檔案狀態", "📥 自動備份所有數據"]
    for task in tasks:
        st.write(f"• {task}")
    st.divider()

    if st.button("🚀 執行全部維護任務", type="primary", use_container_width=True, key="btn_full_maintenance"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("🔄 比對賽果中...")
        updated, msg = update_accuracy_with_results()
        results.append(f"🔄 比對賽果：{msg}")
        progress_bar.progress(20)
        status_text.text("⚖️ 調整權重中...")
        try:
            weight_result = adjust_model_weights()
            results.append(f"⚖️ 調整權重：XGB={weight_result['xgb_weight']}, Cat={weight_result['cat_weight']}")
        except Exception as e:
            results.append(f"⚖️ 調整權重：失敗 - {str(e)}")
        progress_bar.progress(40)
        status_text.text("⏰ 檢查過期會員中...")
        users = load_users()
        today = datetime.now()
        expired = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    if pd.to_datetime(u['expiry_date']) < today:
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        u['plan'] = None
                        expired.append(uid)
                except:
                    pass
        if expired:
            save_users(users)
            results.append(f"⏰ 已將 {len(expired)} 個過期會員降級")
        else:
            results.append("⏰ 目前沒有過期會員")
        progress_bar.progress(60)
        status_text.text("📝 檢查系統檔案中...")
        files_to_check = ['users.json', 'system_config.json', 'accuracy.json', 'race_results_clean.csv']
        file_status = [f"{'✅' if os.path.exists(f) else '❌'} {f}" for f in files_to_check]
        results.append(f"📝 檔案檢查：{' | '.join(file_status)}")
        progress_bar.progress(80)
        status_text.text("📥 自動備份中...")
        try:
            backup_data = {"users": load_users(), "accuracy": load_accuracy(),
                           "finance": load_finance(), "payment_proofs": load_payment_proofs(),
                           "backup_time": datetime.now().isoformat()}
            backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(backup_json)
            st.download_button(label=f"📥 下載備份 ({timestamp})", data=backup_json,
                              file_name=backup_filename, mime="application/json",
                              key=f"auto_backup_{timestamp}")
            results.append(f"📥 自動備份：✅ 備份完成")
        except Exception as e:
            results.append(f"📥 自動備份：❌ 失敗 - {str(e)}")
        progress_bar.progress(100)
        status_text.text("✅ 所有維護任務已完成！")
        st.success("✅ 自動維護完成！")
        st.divider()
        st.subheader("📋 執行結果")
        for r in results:
            st.write(r)

    st.divider()
    st.subheader("⚡ 單獨執行")

    if 'operation_result' in st.session_state:
        msg_type, msg = st.session_state.operation_result
        if msg_type == 'success':
            st.success(msg)
        elif msg_type == 'error':
            st.error(msg)
        elif msg_type == 'info':
            st.info(msg)
        del st.session_state.operation_result

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔄 比對賽果", use_container_width=True, key="btn_compare"):
            try:
                updated, msg = update_accuracy_with_results()
                st.session_state.operation_result = ('success' if updated > 0 else 'info', f"{'✅' if updated > 0 else 'ℹ️'} {msg}")
            except Exception as e:
                st.session_state.operation_result = ('error', f"❌ 比對賽果失敗：{str(e)}")
            st.rerun()
    with col2:
        if st.button("⚖️ 調整權重", use_container_width=True, key="btn_adjust_weights"):
            try:
                result = adjust_model_weights()
                st.session_state.operation_result = ('success', f"✅ XGB={result['xgb_weight']}, Cat={result['cat_weight']}")
            except Exception as e:
                st.session_state.operation_result = ('error', f"❌ 調整權重失敗：{str(e)}")
            st.rerun()
    with col3:
        if st.button("⏰ 終止過期會員", use_container_width=True, key="btn_expire"):
            try:
                users = load_users()
                today = datetime.now()
                expired = []
                for uid, u in users.items():
                    if u.get('group') == 'VIP' and u.get('expiry_date'):
                        try:
                            if pd.to_datetime(u['expiry_date']) < today:
                                u['group'] = 'free'
                                u['is_paid'] = False
                                u['predictions_limit'] = CONFIG["free_limit"]
                                u['plan'] = None
                                expired.append(uid)
                        except:
                            pass
                if expired:
                    save_users(users)
                    st.session_state.operation_result = ('success', f"✅ 已將 {len(expired)} 個過期會員降級")
                else:
                    st.session_state.operation_result = ('info', "✅ 目前沒有過期會員")
            except Exception as e:
                st.session_state.operation_result = ('error', f"❌ 失敗：{str(e)}")
            st.rerun()
    with col4:
        if st.button("🎯 更新 AI 命中率", use_container_width=True, key="btn_update_ai"):
            try:
                hit_count, msg = update_ai_accuracy()
                st.session_state.operation_result = ('success', f"✅ 比對完成：{msg}")
            except Exception as e:
                st.session_state.operation_result = ('error', f"❌ 失敗：{str(e)}")
            st.rerun()

# ============================================================
# 後台：用戶管理
# ============================================================
def admin_user_management():
    st.subheader("👥 用戶管理")
    user_file = "users.json"
    if not os.path.exists(user_file):
        st.error("❌ users.json 檔案不存在！")
        return
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return
    st.info(f"✅ 成功載入 {len(users)} 個用戶")
    if users and isinstance(users, dict):
        df = pd.DataFrame.from_dict(users, orient='index')
        if 'level' not in df.columns: df['level'] = '🥉 銅牌會員'
        if 'exp' not in df.columns: df['exp'] = 0
        if 'badges' not in df.columns: df['badges'] = ''
        df['badges_count'] = df['badges'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        display_cols = ['username', 'group', 'level', 'exp', 'badges_count', 'total_usage', 'is_paid', 'virtual_balance']
        available_cols = [col for col in display_cols if col in df.columns]
        st.dataframe(df[available_cols], use_container_width=True)
    st.divider()

    with st.expander("➕ 新增用戶", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("新用戶名", key="new_user_name")
            new_password = st.text_input("密碼", type="password", key="new_user_pw")
        with col2:
            new_group = st.selectbox("群組", ["free", "paid", "VIP", "super_admin"], key="new_user_group")
            new_is_paid = st.checkbox("付費狀態", value=False, key="new_user_paid")
        if st.button("建立用戶", key="create_user_btn"):
            if not new_username or not new_password:
                st.warning("請填寫用戶名同密碼")
            else:
                try:
                    with open(user_file, 'r', encoding='utf-8') as f:
                        users = json.load(f)
                except:
                    users = {}
                if new_username in users:
                    st.error("❌ 用戶名已被使用")
                else:
                    users[new_username] = {
                        "password": new_password, "is_paid": new_is_paid,
                        "paid_date": None, "expiry_date": None, "free_usage": 0,
                        "total_usage": 0, "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "note": "手動新增", "group": new_group, "phone": "", "plan": None,
                        "predictions_limit": -1 if new_group in ['super_admin', 'VIP'] else CONFIG.get("free_limit", 2),
                        "history": [], "terms_agreed": datetime.now().isoformat(),
                        "invite_code": new_username.upper() + str(random.randint(100, 999)),
                        "invited_by": None, "invite_rewards": 0, "invite_count": 0,
                        "level": "🥉 銅牌會員", "exp": 0, "badges": [],
                        "virtual_balance": CONFIG.get("daily_virtual_coin", 1000),
                        "last_claim_date": '', "bets": []
                    }
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    st.success(f"✅ 用戶 {new_username} 已建立！")
                    st.rerun()

    st.divider()
    st.subheader("🗑️ 刪除用戶")
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except:
        users = {}
    if users:
        del_user = st.selectbox("選擇要刪除嘅用戶", list(users.keys()), key="del_user_select")
        if del_user:
            if del_user == "admin":
                st.warning("⚠️ 唔可以刪除 admin 帳號")
            else:
                confirm = st.checkbox(f"確認刪除 {del_user}？", key="confirm_del")
                if confirm and st.button("🗑️ 確認刪除", key="del_user_btn"):
                    users.pop(del_user)
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    st.success(f"✅ 用戶 {del_user} 已刪除")
                    st.rerun()

    st.divider()
    st.subheader("👁️ 查看用戶視角")
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except:
        users = {}
    if users:
        selected_user = st.selectbox("選擇要查看的用戶", list(users.keys()), key="view_user_select")
        if selected_user:
            user_data = users[selected_user]
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👤 用戶", selected_user)
            col2.metric("🏷️ 級別", user_data.get('group', 'free').upper())
            col3.metric("📊 總預測次數", len(user_data.get('history', [])))
            limit = user_data.get('predictions_limit', CONFIG.get('free_limit', 2))
            col4.metric("📊 剩餘場次", "♾️ 無限" if limit == -1 else max(0, limit - user_data.get('free_usage', 0)))
            st.subheader(f"📋 {selected_user} 嘅預測記錄")
            history = user_data.get('history', [])
            if history:
                st.dataframe(pd.DataFrame(history[-20:][::-1]), use_container_width=True)
            else:
                st.info("呢個用戶暫時冇任何預測記錄")

    st.divider()
    with st.expander("✏️ 編輯用戶"):
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except:
            users = {}
        if users:
            username = st.selectbox("選擇要編輯的用戶", list(users.keys()), key="edit_user_select")
            if username:
                user = users[username]
                col_edit1, col_edit2 = st.columns(2)
                with col_edit1:
                    new_group = st.selectbox("群組", ['free', 'paid', 'VIP', 'super_admin'],
                                            index=['free','paid','VIP','super_admin'].index(user.get('group','free')),
                                            key="edit_group")
                    new_is_paid = st.checkbox("付費狀態", value=user.get('is_paid', False), key="edit_is_paid")
                    # 🔥 修正：確保 default_expiry 係 datetime.date
                    current_expiry = user.get('expiry_date', None)
                    if current_expiry:
                        try:
                            default_expiry = pd.to_datetime(current_expiry).date()
                            if pd.isna(default_expiry):
                                default_expiry = datetime.now().date()
                        except:
                            default_expiry = datetime.now().date()
                    else:
                        default_expiry = datetime.now().date()
                    new_expiry = st.date_input("會員到期日", value=default_expiry, key="edit_expiry_admin")
                with col_edit2:
                    level_options = ["🥉 銅牌會員", "🥈 銀牌會員", "🥇 金牌會員", "💎 鑽石會員", "👑 傳說會員", "👑 超級管理員"]
                    current_level = user.get('level', '🥉 銅牌會員')
                    if current_level not in level_options:
                        level_options.append(current_level)
                    new_level = st.selectbox("🏅 等級", level_options,
                                            index=level_options.index(current_level) if current_level in level_options else 0,
                                            key="edit_level")
                    new_exp = st.number_input("📊 經驗值", min_value=0, value=user.get('exp', 0), step=10, key="edit_exp")
                st.markdown("---")
                st.subheader("💰 虛擬幣調整")
                col_coin1, col_coin2 = st.columns(2)
                with col_coin1:
                    current_balance = user.get('virtual_balance', 0)
                    st.metric("當前結餘", f"${current_balance:,.0f}")
                with col_coin2:
                    coin_adjust = st.number_input("調整金額（+ 加錢，- 扣錢）", value=0, step=100, key="coin_adjust")
                    if st.button("✅ 確認調整虛擬幣", key="apply_coin_adjust"):
                        if coin_adjust != 0:
                            new_balance = current_balance + coin_adjust
                            if new_balance < 0:
                                st.error("❌ 餘額不能為負數")
                            else:
                                users[username]['virtual_balance'] = new_balance
                                with open(user_file, 'w', encoding='utf-8') as f:
                                    json.dump(users, f, ensure_ascii=False, indent=2)
                                st.success(f"✅ 新餘額：${new_balance:,.0f}")
                                st.rerun()
                if st.button("💾 儲存變更", key="save_user_changes"):
                    users[username]['group'] = new_group
                    users[username]['is_paid'] = new_is_paid
                    users[username]['level'] = new_level
                    users[username]['exp'] = new_exp
                    # 🔥 確保 new_expiry 有 strftime 方法
                    try:
                        users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        users[username]['expiry_date'] = str(new_expiry)
                    if new_group in ['super_admin', 'VIP']:
                        users[username]['predictions_limit'] = -1
                    else:
                        users[username]['predictions_limit'] = CONFIG.get("free_limit", 2)
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    st.success("✅ 已更新用戶資料！")
                    st.rerun()

# ============================================================
# 後台：次數管理
# ============================================================
def admin_manage_predictions():
    st.subheader("📊 管理用戶預測次數")
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return
    selected_user = st.selectbox("選擇用戶", list(users.keys()), key="manage_predictions_user")
    if selected_user:
        user_data = users[selected_user]
        current_limit = user_data.get('predictions_limit', CONFIG['free_limit'])
        current_usage = user_data.get('free_usage', 0)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("用戶", selected_user)
        with col2:
            st.metric("目前剩餘次數", current_limit - current_usage if current_limit != -1 else "無限")
        with col3:
            st.metric("已使用次數", current_usage)
        st.divider()
        action = st.radio("選擇操作", ["增加次數", "減少次數", "設定為指定次數"], horizontal=True, key="predictions_action")
        if action == "增加次數":
            add_amount = st.number_input("增加次數", min_value=1, step=1, value=1, key="add_predictions")
            if st.button("✅ 增加", type="primary", key="confirm_add_predictions"):
                if current_limit == -1:
                    st.warning("⚠️ 此用戶已是無限次數")
                else:
                    users[selected_user]['predictions_limit'] = current_limit + add_amount
                    save_users(users)
                    st.success(f"✅ 已增加 {add_amount} 次")
                    st.rerun()
        elif action == "減少次數":
            reduce_amount = st.number_input("減少次數", min_value=1, step=1, value=1, key="reduce_predictions")
            if st.button("✅ 減少", type="primary", key="confirm_reduce_predictions"):
                if current_limit == -1:
                    st.warning("⚠️ 此用戶是無限次數")
                elif current_limit - reduce_amount < 0:
                    st.error("❌ 減少後次數不能低於 0")
                else:
                    users[selected_user]['predictions_limit'] = current_limit - reduce_amount
                    save_users(users)
                    st.success(f"✅ 已減少 {reduce_amount} 次")
                    st.rerun()
        elif action == "設定為指定次數":
            set_amount = st.number_input("設定為指定次數（輸入 -1 = 無限）", min_value=-1, step=1,
                                         value=current_limit if current_limit != -1 else 10, key="set_predictions")
            if st.button("✅ 設定", type="primary", key="confirm_set_predictions"):
                users[selected_user]['predictions_limit'] = set_amount
                save_users(users)
                st.success(f"✅ 已設定為 {'無限' if set_amount == -1 else set_amount}")
                st.rerun()

# ============================================================
# 後台：數據分析
# ============================================================
def admin_analytics():
    st.subheader("📊 數據分析 & 用戶增長")
    users = load_users()
    total_users = len(users)
    paid_users = sum(1 for u in users.values() if u.get('is_paid', False))
    vip_users = sum(1 for u in users.values() if u.get('group') == 'VIP')
    super_admin_users = sum(1 for u in users.values() if u.get('group') == 'super_admin')
    total_pred = sum(u.get('total_usage', 0) for u in users.values())
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("總用戶", total_users)
    col2.metric("付費用戶", paid_users)
    col3.metric("VIP", vip_users)
    col4.metric("超級管理員", super_admin_users)
    col5.metric("總預測次數", total_pred)
    if users:
        df_users = pd.DataFrame.from_dict(users, orient='index')
        if 'created_at' in df_users.columns:
            df_users['created_at'] = pd.to_datetime(df_users['created_at'], errors='coerce')
            df_users = df_users.dropna(subset=['created_at'])
            df_users['date'] = df_users['created_at'].dt.date
            daily = df_users.groupby('date').size().reset_index(name='new_users')
            daily = daily.sort_values('date')
            daily['cumulative'] = daily['new_users'].cumsum()
            fig = px.line(daily, x='date', y=['new_users', 'cumulative'],
                          title='每日新增用戶 & 累積用戶', labels={'value':'用戶數', 'date':'日期'})
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 後台：馬匹/騎師/練馬師排行榜
# ============================================================
def admin_horse_ranking():
    st.subheader("🏇 馬匹勝率排行榜")
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    if not valid_records:
        st.info("暫時未有足夠數據（最少需要 1 場已比對嘅預測記錄）")
        return
    horse_stats = {}
    for rec in valid_records:
        horse = rec.get('horse', '未知馬匹')
        if horse not in horse_stats:
            horse_stats[horse] = {'total': 0, 'hit': 0}
        horse_stats[horse]['total'] += 1
        if rec.get('is_hit') == True:
            horse_stats[horse]['hit'] += 1
    horse_list = [{'馬匹': h, '總預測': s['total'], '命中': s['hit'], '命中率': s['hit']/s['total']}
                  for h, s in horse_stats.items() if s['total'] >= 2]
    if not horse_list:
        st.info("暫時未有足夠數據（需要每匹馬至少預測 2 次先上榜）")
        return
    df_horse = pd.DataFrame(horse_list).sort_values('命中率', ascending=False).reset_index(drop=True)
    st.dataframe(df_horse.head(15), use_container_width=True)

def admin_jockey_ranking():
    st.subheader("👨‍🏫 騎師勝率排行榜")
    st.info("💡 騎師數據需要從排位表檔案提取，建議喺預測時記錄騎師名稱")
    st.info("暫時未有足夠數據")

def admin_trainer_ranking():
    st.subheader("👨‍🏫 練馬師勝率排行榜")
    st.info("💡 練馬師數據需要從排位表檔案提取")
    st.info("暫時未有足夠數據")

def admin_course_analysis():
    st.subheader("📊 場地/路程勝率分析")
    st.info("暫時未有足夠數據")

def admin_monthly_report():
    st.subheader("📅 每月命中率報告")
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    if not valid_records:
        st.info("暫時未有足夠數據")
        return
    df = pd.DataFrame(valid_records)
    if 'date' not in df.columns:
        st.info("記錄中缺少日期欄位")
        return
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')
    df['month_str'] = df['month'].astype(str)
    monthly = df.groupby('month_str').agg(
        total=('is_hit', 'count'),
        hit=('is_hit', lambda x: (x==True).sum())
    ).reset_index()
    monthly['hit_rate'] = monthly['hit'] / monthly['total']
    st.dataframe(monthly, use_container_width=True)

# ============================================================
# 後台：財務
# ============================================================
def admin_finance():
    st.subheader("💰 財務管理")
    finance = load_finance()
    col1, col2, col3 = st.columns(3)
    col1.metric("總收入 (HKD)", f"${finance.get('total_income', 0):.2f}")
    col2.metric("本月收入 (HKD)", f"${finance.get('monthly_income', 0):.2f}")
    col3.metric("今年收入 (HKD)", f"${finance.get('yearly_income', 0):.2f}")
    with st.expander("➕ 新增收入記錄"):
        amount = st.number_input("金額", min_value=0.0, step=10.0, key="finance_amount")
        desc = st.text_input("描述", key="finance_desc")
        if st.button("記錄", key="add_finance"):
            finance['total_income'] = finance.get('total_income', 0) + amount
            finance['monthly_income'] = finance.get('monthly_income', 0) + amount
            finance['yearly_income'] = finance.get('yearly_income', 0) + amount
            save_finance(finance)
            log_admin_action(st.session_state.username, f"新增收入 {amount} - {desc}")
            st.success("✅ 已記錄")
            st.rerun()

# ============================================================
# 後台：優惠碼
# ============================================================
def admin_promo_codes():
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()
    col1, col2 = st.columns(2)
    with col1:
        st.write("現有優惠碼")
        if promos:
            st.dataframe(pd.DataFrame.from_dict(promos, orient='index'), use_container_width=True)
        else:
            st.info("暫無優惠碼")
    with col2:
        st.write("產生新優惠碼")
        duration = st.number_input("有效期 (天)", min_value=1, value=30, key="promo_duration")
        discount_type = st.selectbox("折扣類型", ["percentage", "fixed", "free"], key="promo_discount_type",
                                     format_func=lambda x: {"percentage": "百分比", "fixed": "固定金額", "free": "完全免費"}.get(x, x))
        discount_value = st.number_input("折扣數值", min_value=0, value=20, key="promo_discount_value")
        if st.button("產生優惠碼", key="gen_promo"):
            code = generate_promo_code()
            expiry = (datetime.now() + timedelta(days=duration)).isoformat()
            promos[code] = {"used": False, "expiry": expiry, "created_at": datetime.now().isoformat(),
                            "discount_type": discount_type, "discount_value": discount_value}
            save_promos(promos)
            st.success(f"✅ 優惠碼：`{code}` 有效期 {duration} 天")
            st.rerun()

# ============================================================
# 後台：預測準確率監控
# ============================================================
def admin_accuracy_monitor():
    st.subheader("📈 預測準確率監控")
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        st.info("暫時未有預測記錄，未能進行監控。")
        return
    df_records = pd.DataFrame(records)
    total = len(df_records)
    hit = df_records[df_records['is_hit'] == True].shape[0] if 'is_hit' in df_records else 0
    hit_rate = hit/total if total>0 else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("總預測記錄", total)
    col2.metric("命中次數", hit)
    col3.metric("命中率", f"{hit_rate:.2%}")
    st.divider()
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 比對賽果 + 更新統計", key="admin_update_analysis", use_container_width=True):
            with st.spinner("正在比對賽果..."):
                updated, msg = update_accuracy_with_results()
                if updated > 0:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.info(f"📭 {msg}")
    with col_btn2:
        if st.button("⚖️ 自動調整權重", key="admin_adjust_weights", use_container_width=True):
            with st.spinner("正在計算最佳權重..."):
                result = adjust_model_weights()
                st.success(f"✅ 權重已調整：XGB={result['xgb_weight']}, Cat={result['cat_weight']}")
                st.rerun()

# ============================================================
# 後台：訂閱管理
# ============================================================
def admin_subscription():
    st.subheader("⏰ 訂閱管理 & 到期提醒")
    users = load_users()
    paid_users = {u: data for u, data in users.items() if data.get('is_paid', False) or data.get('group') in ['VIP', 'super_admin']}
    if not paid_users:
        st.info("暫時沒有付費用戶")
    else:
        df_paid = pd.DataFrame.from_dict(paid_users, orient='index')
        df_paid['expiry_date'] = pd.to_datetime(df_paid.get('expiry_date', pd.Series()), errors='coerce')
        today = datetime.now()
        df_paid['days_left'] = (df_paid['expiry_date'] - today).dt.days
        df_paid['status'] = df_paid['days_left'].apply(lambda x: '🟢 有效' if x > 7 else ('🟡 快到期' if x > 0 else '🔴 已過期') if pd.notna(x) else '⚪ 未設定')
        st.dataframe(df_paid, use_container_width=True)

# ============================================================
# 後台：付款審核
# ============================================================
def admin_payment_review():
    st.subheader("📤 付款審核")
    pending = get_all_pending_requests()
    if not pending:
        st.info("✅ 目前沒有待審核嘅付款申請")
        return
    st.write(f"共 **{len(pending)}** 條待審核記錄")
    for item in pending:
        username = item['username']
        req = item['request']
        with st.container():
            cols = st.columns([2, 2, 1.5, 1.5, 2])
            with cols[0]:
                st.write(f"👤 **{username}**")
            with cols[1]:
                st.write(f"📌 {req.get('plan_name', '未知')}")
                st.write(f"💰 ${req.get('final_price', 0):.2f}")
            with cols[2]:
                st.caption(req.get('submitted_at', '')[:16])
            with cols[3]:
                st.warning("⏳ 待審核")
            with cols[4]:
                if st.button("✅ 批准", key=f"approve_{req.get('id')}"):
                    success, msg = approve_payment_request(username, req['id'], st.session_state.username)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                if st.button("❌ 拒絕", key=f"reject_{req.get('id')}"):
                    success, msg = reject_payment_request(username, req['id'], st.session_state.username)
                    if success:
                        st.warning(msg)
                        st.rerun()
            st.divider()

# ============================================================
# 後台：系統監控
# ============================================================
def admin_monitoring():
    st.subheader("📡 系統監控")
    files = ['ALL_DATA_MERGED.csv', 'HKCJ_FULL_YEAR_DATA.csv', 'hk_racing_model.pkl', 'hk_catboost_model.cbm']
    for f in files:
        if os.path.exists(f):
            size = os.path.getsize(f)/1024
            st.success(f"✅ {f} 存在 ({size:.1f} KB)")
        else:
            st.error(f"❌ {f} 不存在")
    logs = load_logs()
    if logs.get('logs'):
        st.dataframe(pd.DataFrame(logs['logs'][-20:]), use_container_width=True)

# ============================================================
# 後台：內容管理
# ============================================================
def admin_content():
    st.subheader("📝 內容管理")
    content = load_json(CONTENT_FILE)
    with st.expander("📢 發佈新公告", expanded=False):
        title = st.text_input("公告標題", key="ann_title")
        content_text = st.text_area("公告內容", height=80, key="ann_content")
        ann_type = st.selectbox("公告類型", ["一般", "重要", "緊急"], key="ann_type")
        if st.button("📤 發佈公告", type="primary", key="publish_ann"):
            if not title or not content_text:
                st.warning("請填寫標題同內容")
            else:
                if 'announcements' not in content:
                    content['announcements'] = []
                content['announcements'].append({
                    "id": len(content['announcements']) + 1, "title": title,
                    "content": content_text, "type": ann_type,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "status": "active"
                })
                save_json(CONTENT_FILE, content)
                st.success("✅ 公告已發佈！")
                st.rerun()
    st.write("---")
    st.write("上傳排位表")
    uploaded = st.file_uploader("選擇 CSV 排位表", type=['csv'], key="upload_racecard")
    if uploaded:
        with open('racecard_uploaded.csv', 'wb') as f:
            f.write(uploaded.getbuffer())
        st.success("✅ 排位表已更新")

# ============================================================
# 後台：自動化工具
# ============================================================
def admin_automation():
    st.subheader("🤖 自動化工具")
    auto = load_json(AUTOMATION_FILE)
    days = st.number_input("提前幾天提醒", min_value=1, value=auto.get('remind_days', 3), key="remind_days_auto")
    if st.button("儲存設定", key="save_remind_auto"):
        auto['remind_days'] = days
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")

# ============================================================
# 後台：安全與權限
# ============================================================
def admin_security():
    st.subheader("🔐 安全與權限")
    st.write("操作日誌")
    logs = load_logs()
    if logs.get('logs'):
        st.dataframe(pd.DataFrame(logs['logs'][-20:]), use_container_width=True)
    users = load_users()
    admin_list = [u for u, d in users.items() if d.get('group') == 'super_admin']
    st.write("現有超級管理員：", ", ".join(admin_list) if admin_list else "無")

# ============================================================
# 後台：用戶監控
# ============================================================
def admin_user_monitor():
    st.subheader("👁️ 用戶監控")
    st.caption("即時監控用戶活動：登入、預測、付款申請、修改資料")

    col1, col2, col3 = st.columns(3)
    with col1:
        users = load_users()
        user_list = ["全部用戶"] + list(users.keys())
        selected_user = st.selectbox("👤 篩選用戶", user_list, key="monitor_user")
    with col2:
        days = st.selectbox("📅 最近日數", [1, 7, 14, 30, 90, 365], index=3, key="monitor_days")
    with col3:
        action_options = {
            "全部動作": None, "🔑 登入": "login", "🔮 預測": "predict",
            "💳 付款申請": "payment_submit", "✏️ 修改資料": "profile_update"
        }
        selected_action_label = st.selectbox("🎯 篩選動作", list(action_options.keys()), key="monitor_action")
        selected_action = action_options[selected_action_label]

    username = None if selected_user == "全部用戶" else selected_user
    logs = get_user_activity_logs(username, days, selected_action)

    if not logs:
        st.info("📭 沒有符合條件嘅活動記錄")
        return

    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp', ascending=False)

    st.markdown("---")
    st.subheader("📊 活動摘要")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("📋 總活動數", len(df))
    col_s2.metric("👤 活躍用戶", df['username'].nunique())
    col_s3.metric("🔑 登入次數", len(df[df['action'] == 'login']))
    col_s4.metric("🔮 預測次數", len(df[df['action'] == 'predict']))

    action_names = {'login': '🔑 登入', 'predict': '🔮 預測',
                    'payment_submit': '💳 付款申請', 'profile_update': '✏️ 修改資料'}

    st.markdown("---")
    st.subheader("📈 動作分佈")
    action_counts = df['action'].value_counts().reset_index()
    action_counts.columns = ['動作', '次數']
    action_counts['動作'] = action_counts['動作'].map(action_names).fillna(action_counts['動作'])
    fig = px.pie(action_counts, names='動作', values='次數', title='活動類型分佈')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📅 每日活動趨勢")
    df['date'] = df['timestamp'].dt.date
    daily = df.groupby('date').size().reset_index(name='活動數')
    fig2 = px.bar(daily.sort_values('date'), x='date', y='活動數', title='每日活動數量')
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 活動記錄")
    display_df = df[['timestamp', 'username', 'action', 'details']].copy()
    display_df['action'] = display_df['action'].map(action_names).fillna(display_df['action'])
    display_df.columns = ['時間', '用戶', '動作', '詳情']
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 下載活動記錄 CSV",
        data=csv,
        file_name=f"user_monitor_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="download_user_monitor"
    )

# ============================================================
# 後台：系統設定
# ============================================================
def admin_system_settings():
    users = load_users()
    admin_username = st.session_state.get('admin_username', 'admin')
    user_group = users.get(admin_username, {}).get('group', 'free')
    if user_group != 'super_admin':
        st.error("⛔ 只有超級管理員可以修改系統設定")
        return
    st.subheader("⚙️ 系統設定")
    st.info("修改設定後，撳「儲存設定」會自動重新整理頁面。")
    config = load_system_config()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔐 基本設定")
        enable_registration = st.checkbox("開放註冊", value=config.get("enable_registration", True))
        enable_payment = st.checkbox("啟用付款功能", value=config.get("enable_payment", True))
        enable_admin = st.checkbox("啟用後台管理", value=config.get("enable_admin", True))
        enable_vip_content = st.checkbox("🔒 三重彩/四重彩 VIP 專屬", value=config.get("enable_vip_content", True))
        st.markdown("#### 💰 價格設定")
        price_day = st.number_input("日費價格 (HKD)", min_value=0, value=config.get("price_day", 18), step=1)
        price_month = st.number_input("月費價格 (HKD)", min_value=0, value=config.get("price_month", 128), step=1)
        price_quarter = st.number_input("季費價格 (HKD)", min_value=0, value=config.get("price_quarter", 328), step=1)
        st.markdown("#### 🎁 邀請獎勵設定")
        enable_invite_reward = st.checkbox("啟用邀請獎勵", value=config.get("enable_invite_reward", True))
        invite_reward_inviter = st.number_input("邀請人獲得免費次數", min_value=0, value=config.get("invite_reward_inviter", 1), step=1)
        invite_reward_invitee = st.number_input("被邀請人獲得免費次數", min_value=0, value=config.get("invite_reward_invitee", 1), step=1)
    with col2:
        st.markdown("#### 📊 預設限制")
        free_limit = st.number_input("免費預測次數", min_value=0, value=config.get("free_limit", 2), step=1)
        verification_expiry = st.number_input("驗證碼有效期 (分鐘)", min_value=1, value=config.get("verification_expiry", 5), step=1)
        admin_password = st.text_input("管理員密碼", value=config.get("admin_password", "z54060437K"), type="password")
        st.markdown("#### 💰 虛擬幣設定")
        virtual_coin_enabled = st.checkbox("啟用虛擬幣功能", value=config.get("virtual_coin_enabled", True))
        daily_virtual_coin = st.number_input("每日派發虛擬幣金額", min_value=0, value=config.get("daily_virtual_coin", 1000), step=100)
        st.markdown("#### 🧩 後台模組開關")
        module_user_management = st.checkbox("用戶管理模組", value=config.get("module_user_management", True))
        module_analytics = st.checkbox("數據分析模組", value=config.get("module_analytics", True))
        module_finance = st.checkbox("財務管理模組", value=config.get("module_finance", True))
        module_monitoring = st.checkbox("系統監控模組", value=config.get("module_monitoring", True))
        module_content = st.checkbox("內容管理模組", value=config.get("module_content", True))
        module_automation = st.checkbox("自動化工具模組", value=config.get("module_automation", True))
        module_security = st.checkbox("安全與權限模組", value=config.get("module_security", True))
        module_promo = st.checkbox("優惠碼模組", value=config.get("module_promo", True))
    st.divider()
    if st.button("💾 儲存設定", type="primary"):
        new_config = {
            "enable_registration": enable_registration, "enable_payment": enable_payment,
            "enable_admin": enable_admin, "currency": "HKD", "free_limit": free_limit,
            "admin_password": admin_password, "price_day": price_day,
            "price_month": price_month, "price_quarter": price_quarter,
            "verification_expiry": verification_expiry, "enable_vip_content": enable_vip_content,
            "module_user_management": module_user_management, "module_analytics": module_analytics,
            "module_finance": module_finance, "module_monitoring": module_monitoring,
            "module_content": module_content, "module_automation": module_automation,
            "module_security": module_security, "module_promo": module_promo,
            "enable_invite_reward": enable_invite_reward,
            "invite_reward_inviter": invite_reward_inviter,
            "invite_reward_invitee": invite_reward_invitee,
            "virtual_coin_enabled": virtual_coin_enabled, "daily_virtual_coin": daily_virtual_coin,
        }
        if save_system_config(new_config):
            st.success("✅ 設定已儲存！")
            import time
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 儲存失敗")

# ============================================================
# 後台主頁面
# ============================================================
def admin_page():
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if not st.session_state.admin_authenticated:
        st.title("🔐 後台管理 - 身份驗證")
        admin_pw = st.text_input("管理員密碼", type="password", key="admin_login_pw")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 解鎖後台", type="primary", key="unlock_admin"):
                if admin_pw == CONFIG["admin_password"]:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_username = "admin"
                    log_admin_action("admin", "登入後台")
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤！")
        with col2:
            if st.button("⬅️ 返回主頁", key="back_home_from_admin"):
                st.session_state.show_admin = False
                st.rerun()
        return
    users = load_users()
    admin_username = st.session_state.get('admin_username', 'admin')
    user_group = users.get(admin_username, {}).get('group', 'free')
    is_super_admin = (user_group == 'super_admin')
    st.title("🔐 後台管理")
    st.info(f"👤 管理員：{admin_username} | 身份：{'超級管理員' if is_super_admin else '管理員'}")
    if st.button("🚪 登出後台", key="logout_admin"):
        st.session_state.admin_authenticated = False
        st.session_state.show_admin = False
        st.rerun()
    st.divider()

    tab_functions = {
        "📊 儀表板": admin_dashboard,
        "👥 用戶管理": admin_user_management,
        "📊 次數管理": admin_manage_predictions,
        "📊 數據分析": admin_analytics,
        "🏇 馬匹排行榜": admin_horse_ranking,
        "👨‍🏫 騎師排行榜": admin_jockey_ranking,
        "👨‍🏫 練馬師排行榜": admin_trainer_ranking,
        "📊 場地/路程分析": admin_course_analysis,
        "📅 每月報告": admin_monthly_report,
        "💰 財務": admin_finance,
        "🎟️ 優惠碼": admin_promo_codes,
        "📈 預測監控": admin_accuracy_monitor,
        "⏰ 訂閱管理": admin_subscription,
        "📤 付款審核": admin_payment_review,
        "📡 監控": admin_monitoring,
        "📝 內容": admin_content,
        "🤖 自動維護": admin_auto_maintenance,
        "🤖 自動化": admin_automation,
        "🔐 安全": admin_security,
        "👁️ 用戶監控": admin_user_monitor,
    }
    tab_names = list(tab_functions.keys())
    if is_super_admin:
        tab_names.append("⚙️ 系統設定")
        tab_functions["⚙️ 系統設定"] = admin_system_settings
    tabs = st.tabs(tab_names)
    for i, name in enumerate(tab_names):
        with tabs[i]:
            tab_functions[name]()

# ============================================================
# 主頁面
# ============================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = 'free'
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'show_bet' not in st.session_state:
        st.session_state.show_bet = False
    if 'show_leaderboard' not in st.session_state:
        st.session_state.show_leaderboard = False

    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        return

    col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
    with col1:
        st.title("🏇 賽馬預測系統")
        st.markdown("AI 驅動・即時預測・彩池推薦")
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')} · 36個特徵 · 三模型融合 · 六種彩池")
    with col2:
        if CONFIG["enable_admin"] and st.session_state.get("role") == "super_admin":
            if st.button("🔐 後台", use_container_width=True, key="go_to_admin"):
                st.session_state.show_admin = True
                st.session_state.admin_authenticated = False
                st.rerun()
    with col3:
        if st.session_state.get('logged_in', False):
            with st.popover("👤 個人中心", use_container_width=True):
                st.markdown(f"**👤 {st.session_state.username}**")
                st.divider()
                # 修改密碼
                with st.form("change_password_form_header"):
                    st.markdown("#### 🔑 修改密碼")
                    old_pw = st.text_input("當前密碼", type="password", key="hdr_old_pw")
                    new_pw = st.text_input("新密碼", type="password", key="hdr_new_pw")
                    confirm_pw = st.text_input("確認新密碼", type="password", key="hdr_confirm_pw")
                    submitted = st.form_submit_button("更新密碼", use_container_width=True)
                    if submitted:
                        if not old_pw or not new_pw or not confirm_pw:
                            st.error("請填寫所有欄位")
                        elif new_pw != confirm_pw:
                            st.error("新密碼與確認密碼不一致")
                        else:
                            users = load_users()
                            if st.session_state.username in users and users[st.session_state.username].get('password') == old_pw:
                                users[st.session_state.username]['password'] = new_pw
                                save_users(users)
                                log_user_activity(st.session_state.username, 'profile_update', '修改密碼')
                                st.success("✅ 密碼已更新")
                            else:
                                st.error("❌ 當前密碼錯誤")
                st.divider()
                # 查看預測紀錄
                st.markdown("#### 📊 我的預測紀錄")
                users = load_users()
                user_data = users.get(st.session_state.username, {})
                history = user_data.get('history', [])
                if history:
                    df_history = pd.DataFrame(history[-10:][::-1])
                    display_cols = ['date', 'race', 'horse', 'is_hit']
                    available_cols = [c for c in display_cols if c in df_history.columns]
                    st.dataframe(df_history[available_cols], use_container_width=True, hide_index=True)
                    st.caption(f"共 {len(history)} 筆預測紀錄（只顯示最近 10 筆）")
                else:
                    st.info("暫時未有預測紀錄")
    with col4:
        if st.session_state.get('logged_in', False):
            if st.button("🚪 登出", use_container_width=True, key="logout_main"):
                log_user_activity(st.session_state.username, 'logout', '用戶登出')
                for key in ['logged_in', 'username', 'role', 'usage_count', 'show_history']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    st.markdown("---")
    display_race_calendar()
    st.markdown("---")

    if CONFIG["enable_registration"] and st.session_state.logged_in:
        show_user_dashboard(st.session_state.username)

    st.markdown("---")
    st.subheader("🧠 模型自我學習 & 表現分析")
    acc = load_accuracy()
    records = acc.get('records', [])
    if records:
        total = len([r for r in records if r.get('is_hit') is not None])
        hit = sum(1 for r in records if r.get('is_hit') is True)
        hit_rate = hit/total if total>0 else 0
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric("📊 總預測", total)
        col_stat2.metric("🎯 命中次數", hit)
        col_stat3.metric("📈 命中率", f"{hit_rate:.2%}")
    else:
        st.info("暫時未有預測記錄，未能進行自我學習分析。請先執行預測。")

    st.markdown("---")
    st.subheader("🎯 賽事預測控制")
    col_date, col_race, col_btn = st.columns([2, 2, 1])
    with col_date:
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2026-09-06"), key="predict_date_mid")
    with col_race:
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=0, key="predict_race_mid")
    with col_btn:
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True, key="predict_btn_mid")

    if predict_btn:
        date_str = date.strftime("%Y-%m-%d")
        with st.spinner(f"⏳ 正在預測 {date_str} 第 {race_no} 場..."):
            try:
                result, pool = run_prediction(date_str, race_no)
                if result is not None and not result.empty:
                    st.success(f"✅ {date_str} 第 {race_no} 場預測完成！")
                    if pool:
                        st.info(pool)
                    st.dataframe(result, use_container_width=True)
                else:
                    st.error("❌ 未能獲取預測結果，請檢查排位表")
            except Exception as e:
                st.error(f"❌ 預測過程發生錯誤：{e}")

    # ========== AI 預測表現及賽果對比 ==========
    with st.expander("🤖 AI 預測表現 & 賽果對比（點擊展開）", expanded=False):
        ai_file = "ai_predictions.json"
        predictions = {}
        if os.path.exists(ai_file):
            try:
                with open(ai_file, 'r', encoding='utf-8') as f:
                    predictions = json.load(f)
                st.info(f"✅ 成功讀取 {len(predictions)} 個預測紀錄")
            except Exception as e:
                st.error(f"❌ 讀取預測紀錄失敗：{e}")
                predictions = {}
        else:
            st.warning("⚠️ 尚未有任何預測紀錄")

        result_file = "race_results_clean.csv"
        df_results = pd.DataFrame()
        if os.path.exists(result_file):
            try:
                df_results = pd.read_csv(result_file, encoding='utf-8-sig')
                required_cols = ['race_date', 'race_no', 'horse_name', 'finish_position']
                if not all(col in df_results.columns for col in required_cols):
                    st.error(f"❌ 賽果檔案缺少必要欄位")
                    df_results = pd.DataFrame()
                else:
                    df_results['horse_name'] = df_results['horse_name'].str.strip()
                    df_results['horse_name'] = df_results['horse_name'].str.replace(r'\s*\([^)]*\)', '', regex=True).str.strip()
                    df_results['finish_position'] = pd.to_numeric(df_results['finish_position'], errors='coerce')
                    df_results['race_no'] = pd.to_numeric(df_results['race_no'], errors='coerce').astype(int)
                    df_results['race_date'] = pd.to_datetime(df_results['race_date'], errors='coerce')
                    df_results = df_results.dropna(subset=['race_date'])
            except Exception as e:
                st.error(f"❌ 讀取賽果失敗：{e}")
                df_results = pd.DataFrame()
        else:
            st.warning("⚠️ 找不到賽果檔案 race_results_clean.csv")

        pred_list = []
        if predictions and not df_results.empty:
            for key, value in predictions.items():
                if '_' not in key:
                    continue
                parts = key.split('_')
                if len(parts) != 2:
                    continue
                date_str, race_no_str = parts[0], parts[1]
                if not race_no_str.isdigit():
                    continue
                race_no = int(race_no_str)
                if not isinstance(value, dict):
                    continue
                horse_list = value.get('all_horses', [])
                if not horse_list or not isinstance(horse_list, list):
                    top = value.get('top_horse')
                    if top:
                        horse_list = [top]
                    else:
                        continue
                cleaned = [str(h).strip() for h in horse_list if str(h).strip()]
                cleaned = [re.sub(r'\s*\([^)]*\)', '', h).strip() for h in cleaned]
                for idx, horse in enumerate(cleaned[:4], 1):
                    pred_list.append({'日期': date_str, '場次': race_no, '預測名次': idx, '預測馬': horse})
            if pred_list:
                st.info(f"✅ 成功解析 {len(pred_list)} 筆預測（頭四名）")

        if pred_list and not df_results.empty:
            df_pred = pd.DataFrame(pred_list)
            df_pred['場次'] = df_pred['場次'].astype(int)
            df_pred['預測名次'] = df_pred['預測名次'].astype(int)
            df_pred['預測馬'] = df_pred['預測馬'].str.replace(r'\s*\([^)]*\)', '', regex=True).str.strip()

            pred_dates = set(df_pred['日期'].unique())
            result_dates = set(df_results['race_date'].dt.strftime('%Y-%m-%d').unique())
            available_dates = sorted(pred_dates & result_dates)

            if available_dates:
                selected_date = st.selectbox("📅 選擇日期", available_dates)
                df_pred_date = df_pred[df_pred['日期'] == selected_date].copy()
                df_result_date = df_results[df_results['race_date'].dt.strftime('%Y-%m-%d') == selected_date].copy()

                pred_races = set(df_pred_date['場次'].unique())
                result_races = set(df_result_date['race_no'].unique())
                available_races = sorted(pred_races & result_races)

                if available_races:
                    selected_race = st.selectbox("🏇 選擇場次", available_races, format_func=lambda x: f"第 {x} 場")
                    df_pred_race = df_pred_date[df_pred_date['場次'] == selected_race].copy()
                    df_result_race = df_result_date[df_result_date['race_no'] == selected_race].copy()
                    df_result_race = df_result_race.sort_values('finish_position').head(4)
                    df_result_race.rename(columns={'finish_position': '真實名次', 'horse_name': '真實馬'}, inplace=True)
                    df_result_race['真實馬'] = df_result_race['真實馬'].str.replace(r'\s*\([^)]*\)', '', regex=True).str.strip()

                    df_compare = df_pred_race.merge(df_result_race, left_on='預測名次', right_on='真實名次', how='left')
                    df_compare['結果'] = df_compare.apply(lambda row: '命中' if row['預測馬'] == row['真實馬'] else '失準', axis=1)
                    display_df = df_compare[['預測名次', '預測馬', '真實名次', '真實馬', '結果']].copy()
                    display_df.columns = ['名次', '預測馬', '真實名次', '真實馬', '結果']
                    st.write(f"📊 {selected_date} 第 {selected_race} 場 預測 vs 賽果")

                    def highlight_row(row):
                        if row['結果'] == '命中':
                            return ['background-color: #d4edda; color: black'] * len(row)
                        elif row['結果'] == '失準':
                            return ['background-color: #f8d7da; color: black'] * len(row)
                        else:
                            return ['background-color: white; color: black'] * len(row)

                    styled_df = display_df.style.apply(highlight_row, axis=1)
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ 所選日期沒有可比較嘅場次")
            else:
                st.info("ℹ️ 沒有同時存在預測同賽果嘅日期")

    # ========== 虛擬投注 ==========
    if st.session_state.get('logged_in', False):
        st.markdown("---")
        st.subheader("🎮 虛擬投注")
        col_v1, col_v2, col_v3 = st.columns([1, 1, 2])
        with col_v1:
            if st.button("💰 投注模擬器", use_container_width=True, key="btn_bet"):
                st.session_state.show_bet = not st.session_state.get('show_bet', False)
                st.session_state.show_leaderboard = False
        with col_v2:
            if st.button("🏆 排行榜", use_container_width=True, key="btn_leaderboard"):
                st.session_state.show_leaderboard = not st.session_state.get('show_leaderboard', False)
                st.session_state.show_bet = False
        with col_v3:
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            balance = user_data.get('virtual_balance', 0)
            st.info(f"💎 你嘅虛擬幣結餘：**${balance:,.0f}**")
        if st.session_state.get('show_bet', False):
            show_betting_interface(st.session_state.username)
        if st.session_state.get('show_leaderboard', False):
            show_leaderboard()
        if st.session_state.get('role') == 'super_admin':
            st.markdown("---")
            st.subheader("🎁 管理員贈送虛擬幣")
            with st.form(key="admin_gift_form"):
                col_g1, col_g2, col_g3 = st.columns([2, 1, 1])
                with col_g1:
                    target_user = st.selectbox("選擇用戶", list(load_users().keys()), key="gift_user")
                with col_g2:
                    gift_amount = st.number_input("金額", min_value=1, value=100, step=50, key="gift_amount")
                with col_g3:
                    submit_gift = st.form_submit_button("🎁 贈送")
                if submit_gift:
                    if target_user == st.session_state.username:
                        st.error("❌ 唔可以送俾自己")
                    else:
                        users = load_users()
                        if target_user in users:
                            users[target_user]['virtual_balance'] = users[target_user].get('virtual_balance', 0) + gift_amount
                            save_users(users)
                            log_admin_action(st.session_state.username, f"贈送 ${gift_amount} 虛擬幣給 {target_user}")
                            st.success(f"✅ 已贈送 ${gift_amount} 給 {target_user}")
                            st.rerun()

    # ====== 付款功能 ======
    st.markdown("---")
    st.subheader("💳 付款功能")
    if st.session_state.get('logged_in'):
        show_paywall()
    else:
        st.info("請先登入以使用付款功能")

    # ====== 今日賽程 ======
    st.subheader("📅 今日賽程")
    try:
        df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df_sched = standardize_columns_safe(df_sched)
        if 'race_date' in df_sched.columns:
            df_sched['race_date'] = pd.to_datetime(df_sched['race_date'], errors='coerce')
            today_dt = datetime.now().date()
            day_races = df_sched[df_sched['race_date'].dt.date == today_dt]
            if not day_races.empty:
                for course in day_races['race_course'].unique():
                    races = day_races[day_races['race_course'] == course]['race_no'].unique()
                    st.write(f"🏟️ **{course}**：第 {', '.join(map(str, sorted(races)))} 場")
            else:
                st.info("今日沒有賽事")
        else:
            st.info("今日沒有賽事")
    except Exception as e:
        st.info(f"無法讀取排位表：{e}")

    st.divider()
    st.warning("⚠️ **免責聲明**：本系統提供之預測僅供參考，不構成投注建議。賽馬活動涉及風險，用戶應量力而為。用戶必須年滿18歲。")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col_f2:
        st.caption("🔐 數據來源：HKJC | 系統版本：v15.0")
    with col_f3:
        st.caption("💬 Telegram：@bryhjdjbrbxibvrjskofndhiebdpaq")

if __name__ == '__main__':
    main()
