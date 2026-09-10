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

def settle_bets(username, race_date, race_no, results_df):
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
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
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
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
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        if username not in users:
            return False, "用戶不存在"
        user = users[username]
        balance = user.get('virtual_balance', 0)
        if bet_amount <= 0:
            return False, "投注金額必須大於 0"
        if bet_amount > balance:
            return False, f"餘額不足（餘額：${balance}）"
        new_balance = balance - bet_amount
        user['virtual_balance'] = new_balance
        if 'bets' not in user:
            user['bets'] = []
        bet = {"date": race_date, "race": race_no, "horse": horse_name,
               "amount": bet_amount, "bet_type": bet_type,
               "placed_at": datetime.now().isoformat(), "result": None,
               "payout": 0, "odds": None, "settled": False}
        user['bets'].append(bet)
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            verify = json.load(f)
        if verify[username].get('virtual_balance') == new_balance:
            return True, f"已投注 ${bet_amount} 喺 {horse_name}"
        else:
            user['virtual_balance'] = balance
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            return False, "儲存驗證失敗"
    except Exception as e:
        return False, f"錯誤：{str(e)}"

def show_betting_interface(username):
    if not username:
        st.info("請先登入")
        return
    if 'bet_result' in st.session_state:
        msg_type, msg = st.session_state.bet_result
        if msg_type == 'success':
            st.success(msg)
        else:
            st.error(msg)
        del st.session_state.bet_result
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        user = users.get(username, {})
        balance = user.get('virtual_balance', 0)
    except:
        st.error("無法讀取 users.json")
        return
    st.subheader("💰 投注模擬器")
    st.caption("用虛擬幣體驗投注樂趣，唔使真錢！")
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
                with st.form(key="place_bet_form"):
                    horse_options = result['horse_name'].tolist()
                    selected_horse = st.selectbox("揀馬", horse_options, key="bet_horse_select")
                    max_bet = int(balance) if balance > 0 else 1
                    bet_amount = st.number_input("投注金額", min_value=1, max_value=max_bet,
                                                 value=min(100, max_bet), step=10, key="bet_amount_input")
                    submit_bet = st.form_submit_button("✅ 確認投注", type="primary")
                    if submit_bet:
                        try:
                            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                                temp = json.load(f)
                            current_balance = temp.get(username, {}).get('virtual_balance', 0)
                        except:
                            current_balance = 0
                        if bet_amount > current_balance:
                            st.error(f"❌ 餘額不足（餘額：${current_balance:,.0f}）")
                        else:
                            success, msg = place_bet(username, date_str, bet_race, selected_horse, bet_amount)
                            if success:
                                st.session_state.bet_result = ('success', msg)
                            else:
                                st.session_state.bet_result = ('error', msg)
                            st.rerun()
            else:
                st.warning("無法載入預測數據")
    st.divider()
    st.subheader("📋 我的投注記錄")
    bets = user.get('bets', [])
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

    # 🔑 修改密碼
    with st.expander("🔑 修改密碼", expanded=False):
        with st.form("change_password_form"):
            old_pw = st.text_input("當前密碼", type="password")
            new_pw = st.text_input("新密碼", type="password")
            confirm_pw = st.text_input("確認新密碼", type="password")
            submitted = st.form_submit_button("更新密碼")
            if submitted:
                if not old_pw or not new_pw or not confirm_pw:
                    st.error("請填寫所有欄位")
                elif new_pw != confirm_pw:
                    st.error("新密碼與確認密碼不一致")
                else:
                    users = load_users()
                    if username in users and users[username].get('password') == old_pw:
                        users[username]['password'] = new_pw
                        save_users(users)
                        log_user_activity(username, 'profile_update', '修改密碼')
                        st.success("✅ 密碼已更新")
                    else:
                        st.error("❌ 當前密碼錯誤")

    # 📊 查看預測紀錄
    with st.expander("📊 我的預測紀錄", expanded=False):
        history = user_data.get('history', [])
        if history:
            df_history = pd.DataFrame(history[-50:][::-1])
            st.dataframe(df_history, use_container_width=True)
            st.caption(f"共 {len(history)} 筆預測紀錄")
        else:
            st.info("暫時未有預測紀錄")
 登入/註冊
