#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整版（付款功能統一，開放所有用戶）
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import json
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
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None,
    }
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
    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 300px !important;
    }
    section[data-testid="stSidebar"] * {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    .stApp > header + div {
        padding-top: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔐 系統設定
# ============================================================
CONFIG_FILE = 'system_config.json'

DEFAULT_CONFIG = {
    "enable_registration": True,
    "enable_payment": True,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "admin_password": "z54060437K",
    "price_day": 18,
    "price_month": 128,
    "price_quarter": 328,
    "verification_expiry": 5,
    "enable_vip_content": True,
    "enable_daily_free_tip": True,
    "enable_invite_reward": True,
    "invite_reward_inviter": 1,
    "invite_reward_invitee": 1,
    "xgb_weight": 25,
    "cat_weight": 1,
    "last_weight_update": "",
    "last_hit_rate": 0.0,
    "module_user_management": True,
    "module_analytics": True,
    "module_finance": True,
    "module_monitoring": True,
    "module_content": True,
    "module_automation": True,
    "module_security": True,
    "module_promo": True,
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

# ============================================================
# 初始化 session_state 付款記錄
# ============================================================
if 'payment_requests' not in st.session_state:
    st.session_state.payment_requests = {"requests": []}

# ============================================================
# 用戶等級/勳章系統（輔助函數）
# ============================================================
def get_level_info(exp):
    """根據經驗值回傳等級名稱同emoji"""
    levels = [
        (0, "🥉 銅牌會員"),
        (100, "🥈 銀牌會員"),
        (500, "🥇 金牌會員"),
        (1500, "💎 鑽石會員"),
        (5000, "👑 傳說會員")
    ]
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
    """檢查並更新用戶勳章"""
    users = load_users()
    if username not in users:
        return
    
    user = users[username]
    history = user.get('history', [])
    badges = user.get('badges', [])
    total_predictions = len(history)
    hits = sum(1 for h in history if h.get('is_hit') is True)
    hit_rate = hits / total_predictions if total_predictions > 0 else 0
    
    # 計算連續命中
    consecutive_hits = 0
    max_consecutive = 0
    for h in history:
        if h.get('is_hit') is True:
            consecutive_hits += 1
            max_consecutive = max(max_consecutive, consecutive_hits)
        else:
            consecutive_hits = 0
    
    # 勳章條件
    badge_conditions = {
        "🏆 首勝": (total_predictions >= 1 and hits >= 1, "第一次預測命中"),
        "🔥 三連勝": (max_consecutive >= 3, "連續 3 次預測命中"),
        "⚡ 五連勝": (max_consecutive >= 5, "連續 5 次預測命中"),
        "💯 百場預測": (total_predictions >= 100, "累積預測 100 次"),
        "🎯 命中大師": (total_predictions >= 20 and hit_rate >= 0.5, "命中率超過 50%"),
        "👥 社交達人": (user.get('invite_count', 0) >= 5, "成功邀請 5 位朋友"),
        "💰 付費會員": (user.get('is_paid', False) or user.get('group') == 'VIP', "首次付款升級 VIP"),
        "🏇 馬匹專家": (len(set(h.get('horse') for h in history)) >= 5, "預測過 5 匹不同馬匹"),
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
    """更新用戶經驗值"""
    users = load_users()
    if username not in users:
        return
    
    user = users[username]
    exp = user.get('exp', 0)
    
    # 預測加 10 EXP
    exp += 10
    # 命中額外加 20 EXP
    if is_hit:
        exp += 20
    
    user['exp'] = exp
    
    # 更新等級
    new_level, next_exp = get_level_info(exp)
    if new_level != user.get('level', ''):
        old_level = user.get('level', '')
        user['level'] = new_level
        # 如果升呢，加入日誌
        if old_level != new_level:
            log_admin_action("system", f"{username} 升級：{old_level} → {new_level}")
    
    save_users(users)
    
    # 檢查勳章
    check_badges(username)

# ============================================================
# 用戶系統
# ============================================================
def load_users():
    users = load_json(USER_DATA_FILE)
    if not users or "admin" not in users:
        users = {
            "admin": {
                "username": "admin",
                "password": CONFIG["admin_password"],
                "is_paid": False,
                "paid_date": None,
                "expiry_date": None,
                "free_usage": 0,
                "total_usage": 0,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "note": "系統超級管理員",
                "group": "super_admin",
                "phone": "",
                "plan": None,
                "predictions_limit": -1,
                "history": [],
                "terms_agreed": datetime.now().isoformat(),
                "invite_code": "ADMIN001",
                "invited_by": None,
                "invite_rewards": 0,
                "invite_count": 0,
                "level": "👑 超級管理員",
                "exp": 0,
                "badges": []
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
            if 'level' not in u:
                u['level'] = '🥉 銅牌會員'
            if 'exp' not in u:
                u['exp'] = 0
            if 'badges' not in u:
                u['badges'] = []
        save_users(users)
    return users

def save_users(users):
    return save_json(USER_DATA_FILE, users)

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
        'admin': admin,
        'action': action
    })
    save_logs(logs)

def load_finance():
    return load_json(FINANCE_FILE)

def save_finance(finance):
    return save_json(FINANCE_FILE, finance)

def load_promos():
    return load_json(PROMO_FILE)

def save_promos(promos):
    return save_json(PROMO_FILE, promos)

def load_logs():
    return load_json(LOG_FILE)

def save_logs(logs):
    return save_json(LOG_FILE, logs)

def load_accuracy():
    return load_json(ACCURACY_FILE)

def save_accuracy(acc):
    return save_json(ACCURACY_FILE, acc)

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
    names = {'day': '日費', 'month': '月費', 'quarter': '季費'}
    return names.get(plan, '未知')

def get_plan_price(plan):
    if plan == 'day': return CONFIG['price_day']
    elif plan == 'month': return CONFIG['price_month']
    elif plan == 'quarter': return CONFIG['price_quarter']
    return 0

# ============================================================
# 付款申請功能（存入 session_state + payment_proofs.json）
# ============================================================
def submit_payment_request(username, plan, final_price, discount_desc, promo_code_used):
    proof = load_payment_proofs()
    if 'proof_records' not in proof:
        proof['proof_records'] = []
    
    new_id = len(proof['proof_records']) + 1
    
    new_request = {
        "id": new_id,
        "username": username,
        "plan": plan,
        "plan_name": get_plan_name(plan),
        "final_price": final_price,
        "discount_desc": discount_desc,
        "promo_code": promo_code_used,
        "submitted_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    proof['proof_records'].append(new_request)
    save_payment_proofs(proof)
    
    if 'payment_requests' not in st.session_state:
        st.session_state.payment_requests = {"requests": []}
    st.session_state.payment_requests['requests'].append(new_request)
    
    return True, "申請已提交"

def get_all_pending_requests():
    proof = load_payment_proofs()
    all_requests = []
    
    for req in proof.get('proof_records', []):
        if req.get('status') == 'pending':
            all_requests.append({
                "username": req.get('username', ''),
                "request": req
            })
    
    if 'payment_requests' not in st.session_state:
        st.session_state.payment_requests = {"requests": []}
    st.session_state.payment_requests['requests'] = proof.get('proof_records', [])
    
    return all_requests

def approve_payment_request(username, request_id, admin_username):
    proof = load_payment_proofs()
    found = False
    
    for req in proof.get('proof_records', []):
        if req.get('id') == request_id and req.get('status') == 'pending':
            found = True
            users = load_users()
            if username in users:
                plan = req.get('plan', 'month')
                days = get_plan_days(plan)
                if days == 0:
                    days = 30
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
                
                if 'payment_requests' in st.session_state:
                    for sr in st.session_state.payment_requests['requests']:
                        if sr.get('id') == request_id:
                            sr['status'] = 'approved'
                            sr['approved_by'] = admin_username
                            sr['approved_at'] = datetime.now().isoformat()
                            break
                
                log_admin_action(admin_username, f"批准付款並升級 {username} 為 VIP（{plan}）")
                return True, f"已批准 {username} 的付款，到期日 {expiry}"
            else:
                return False, "用戶不存在"
    
    if not found:
        return False, "找不到該申請"
    return False, "處理失敗"

def reject_payment_request(username, request_id, admin_username):
    proof = load_payment_proofs()
    
    for req in proof.get('proof_records', []):
        if req.get('id') == request_id and req.get('status') == 'pending':
            req['status'] = 'rejected'
            req['rejected_by'] = admin_username
            req['rejected_at'] = datetime.now().isoformat()
            save_payment_proofs(proof)
            
            if 'payment_requests' in st.session_state:
                for sr in st.session_state.payment_requests['requests']:
                    if sr.get('id') == request_id:
                        sr['status'] = 'rejected'
                        sr['rejected_by'] = admin_username
                        sr['rejected_at'] = datetime.now().isoformat()
                        break
            
            log_admin_action(admin_username, f"拒絕 {username} 的付款申請")
            return True, "已拒絕該申請"
    
    return False, "找不到該申請"

# ============================================================
# 付款牆（統一付款界面，開放所有用戶）
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
        plan_choice = st.radio(
            "請選擇付費方案：",
            options=list(plan_options.keys()),
            format_func=lambda x: plan_options[x],
            horizontal=True,
            key="plan_radio_in_form"
        )

        if plan_choice:
            original_price = get_plan_price(plan_choice)
            st.info(f"💰 價格：${original_price}")
        else:
            st.info("請選擇一個方案")

        promo_input = st.text_input("優惠碼（如有）", key="promo_input_form")

        st.divider()
        st.markdown("""
        **📤 付款方式：FPS 轉數快 `12345678`（SHTSN SYSTEM）**  
        💬 過數後請將截圖發送 Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**
        """)

        submitted = st.form_submit_button("📩 提交付款申請，等待管理員審核")

        if submitted:
            if not plan_choice:
                st.error("❌ 請選擇方案")
                return
            if not st.session_state.get('logged_in'):
                st.error("❌ 請先登入")
                return

            username = st.session_state.username
            original_price = get_plan_price(plan_choice)
            final_price = original_price
            discount_desc = ""
            promo_code_used = None

            if promo_input:
                try:
                    promos = load_promos()
                    promo_data = promos.get(promo_input.strip())
                    if promo_data and not promo_data.get('used', False):
                        expiry = promo_data.get('expiry')
                        if expiry:
                            expiry_date = datetime.fromisoformat(expiry)
                            if expiry_date >= datetime.now():
                                discount_type = promo_data.get('discount_type', 'percentage')
                                discount_value = promo_data.get('discount_value', 0)
                                if discount_type == 'percentage':
                                    final_price = original_price * (1 - discount_value / 100)
                                    discount_desc = f"{discount_value}% 折扣"
                                elif discount_type == 'fixed':
                                    final_price = max(0, original_price - discount_value)
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
                st.success(msg)
                st.session_state['payment_just_submitted'] = True
                st.session_state['payment_detail'] = f"方案：{get_plan_name(plan_choice)}，金額：${final_price}"
                st.rerun()
            else:
                st.error(msg)

# ============================================================
# 後台付款審核
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
                st.caption(f"ID: {req.get('id', '')}")
            with cols[1]:
                plan_name = req.get('plan_name', '未知方案')
                price = req.get('final_price', 0)
                st.write(f"📌 {plan_name}")
                st.write(f"💰 ${price:.2f}")
                if req.get('discount_desc'):
                    st.caption(f"折扣: {req.get('discount_desc', '')}")
            with cols[2]:
                submitted_at = req.get('submitted_at', '')
                if submitted_at:
                    try:
                        dt = datetime.fromisoformat(submitted_at)
                        st.caption(f"📅 {dt.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        st.caption(submitted_at)
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
                    else:
                        st.error(msg)
            st.divider()

# ============================================================
# 補齊付款證明相關函數（確保儀表板正常）
# ============================================================
PAYMENT_PROOFS_FILE = 'payment_proofs.json'
PAYMENT_PROOFS_DIR = 'payment_proofs'

if not os.path.exists(PAYMENT_PROOFS_DIR):
    os.makedirs(PAYMENT_PROOFS_DIR)

def load_payment_proofs():
    return load_json(PAYMENT_PROOFS_FILE)

def save_payment_proofs(data):
    return save_json(PAYMENT_PROOFS_FILE, data)

# ============================================================
# AI 自我學習（完整）
# ============================================================
def update_accuracy_with_results():
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        return 0, "沒有預測記錄"
    try:
        results_df = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
        results_df = standardize_columns_safe(results_df)
        results_df = results_df.loc[:, ~results_df.columns.duplicated()]
        
        required = ['race_date', 'race_no', 'horse_name', 'finish_position']
        for col in required:
            if col not in results_df.columns:
                return 0, f"缺少必要欄位：{col}"
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
                
                # 如果命中，更新用戶經驗值（額外加分）
                if rec.get('is_hit') == True:
                    username = rec.get('username')
                    if username:
                        # 先更新用戶歷史記錄入面嘅 is_hit
                        users = load_users()
                        if username in users:
                            for h in users[username].get('history', []):
                                if h.get('date') == rec.get('date') and h.get('race') == rec.get('race'):
                                    h['is_hit'] = True
                                    break
                            save_users(users)
                        # 更新經驗值（命中加額外 20 EXP）
                        update_user_exp(username, is_hit=True)
                    # 檢查勳章
                    check_badges(username)
        if updated > 0:
            save_accuracy(acc)
        return updated, f"成功比對 {updated} 條記錄"
    except Exception as e:
        return 0, f"比對失敗：{str(e)}"

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
        new_xgb = min(40, current_xgb + 3)
        new_cat = max(1, current_cat - 1)
    elif hit_rate >= 0.5:
        new_xgb = min(35, current_xgb + 1)
        new_cat = max(1, current_cat)
    elif hit_rate >= 0.4:
        new_xgb = max(15, current_xgb - 2)
        new_cat = min(10, current_cat + 2)
    elif hit_rate >= 0.3:
        new_xgb = max(10, current_xgb - 5)
        new_cat = min(15, current_cat + 5)
    else:
        new_xgb = max(5, current_xgb - 8)
        new_cat = min(20, current_cat + 8)

    new_xgb = max(1, min(50, new_xgb))
    new_cat = max(1, min(30, new_cat))

    config['xgb_weight'] = new_xgb
    config['cat_weight'] = new_cat
    config['last_weight_update'] = datetime.now().isoformat()
    config['last_hit_rate'] = hit_rate
    save_system_config(config)

    return {
        'xgb_weight': new_xgb,
        'cat_weight': new_cat,
        'hit_rate': hit_rate,
        'total': total,
        'hit': hit
    }

# ============================================================
# 模型載入（完整）
# ============================================================
@st.cache_resource
def load_models():
    try:
        with open('hk_racing_model.pkl', 'rb') as f:
            xgb_obj = pickle.load(f)
            xgb_model = xgb_obj[0] if isinstance(xgb_obj, tuple) else xgb_obj
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        with open('hk_ranking_model.pkl', 'rb') as f:
            rank_obj = pickle.load(f)
            rank_model = rank_obj[0] if isinstance(rank_obj, tuple) else rank_obj
        return xgb_model, cat_model, rank_model
    except:
        st.error("❌ 模型載入失敗")
        return None, None, None

# ============================================================
# 特徵工程（36 特徵，完整）
# ============================================================
FEATURES_EN = [
    'draw', 'act_wt', 'distance', 'rtg', 'avg_rank_last3',
    'jockey_win_rate_50', 'trainer_win_rate_50',
    'distance_win_rate', 'distance_avg_rank',
    'win_odds', 'weight_change', 'jockey_trainer_win_rate',
    'course_win_rate', 'course_avg_rank',
    'days_since_last_run', 'odds_rank_in_race',
    'rtg_change', 'jockey_horse_win_rate',
    'races_last14days', 'going_win_rate',
    'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
    'early_pace', 'finish_speed',
    'last_trial_rank', 'last_trial_time',
    'jockey_win_rate_5', 'jockey_win_rate_10', 'draw_win_rate',
    'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
    'total_injuries', 'injury_severity'
]

EXPECTED_FEATURES = [
    'draw', 'weight', 'distance', 'Rtg.', '近3場平均名次',
    '騎師近50場勝率', '練馬師近50場勝率', '同路程歷史勝率',
    '同路程歷史平均名次', 'win_odds', '體重變化', '騎練組合勝率',
    '詳細賽道歷史勝率', '詳細賽道歷史平均名次', '出賽相隔日數',
    '賠率場次排名', '評分變化', '騎馬合作勝率', '近14日出賽次數',
    '場地狀況勝率', '試閘歷史勝率', '父系歷史勝率', '父系同程勝率',
    '前速指標', '後勁指標', '最近試閘名次', '最近試閘時間',
    '騎師近5場勝率', '騎師近10場勝率', '檔位勝率', '最近傷患日數',
    '過去30日內有傷患', '過去60日內有傷患', '過去90日內有傷患',
    '傷患總次數', '傷患嚴重程度'
]

NAME_MAPPING = {
    'act_wt': 'weight', 'rtg': 'Rtg.',
    'avg_rank_last3': '近3場平均名次',
    'jockey_win_rate_50': '騎師近50場勝率',
    'trainer_win_rate_50': '練馬師近50場勝率',
    'distance_win_rate': '同路程歷史勝率',
    'distance_avg_rank': '同路程歷史平均名次',
    'weight_change': '體重變化',
    'jockey_trainer_win_rate': '騎練組合勝率',
    'course_win_rate': '詳細賽道歷史勝率',
    'course_avg_rank': '詳細賽道歷史平均名次',
    'days_since_last_run': '出賽相隔日數',
    'odds_rank_in_race': '賠率場次排名',
    'rtg_change': '評分變化',
    'jockey_horse_win_rate': '騎馬合作勝率',
    'races_last14days': '近14日出賽次數',
    'going_win_rate': '場地狀況勝率',
    'trial_win_rate': '試閘歷史勝率',
    'sire_win_rate': '父系歷史勝率',
    'sire_course_win_rate': '父系同程勝率',
    'early_pace': '前速指標',
    'finish_speed': '後勁指標',
    'last_trial_rank': '最近試閘名次',
    'last_trial_time': '最近試閘時間',
    'jockey_win_rate_5': '騎師近5場勝率',
    'jockey_win_rate_10': '騎師近10場勝率',
    'draw_win_rate': '檔位勝率',
    'days_since_injury': '最近傷患日數',
    'injury_30d': '過去30日內有傷患',
    'injury_60d': '過去60日內有傷患',
    'injury_90d': '過去90日內有傷患',
    'total_injuries': '傷患總次數',
    'injury_severity': '傷患嚴重程度'
}

def standardize_columns_safe(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course',
        '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    if '比賽日期' in df.columns and 'race_date' not in df.columns:
        df.rename(columns={'比賽日期': 'race_date'}, inplace=True)
    elif '比賽日期' in df.columns and 'race_date' in df.columns:
        df.drop(columns=['比賽日期'], inplace=True, errors='ignore')
    return df

def ensure_series(df):
    for col in df.columns:
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    return df

def get_finish_column(df):
    candidates = ['finish_position', '名次', 'Position', 'pos', 'Rank', 'rank', '最終名次']
    for col in candidates:
        if col in df.columns:
            return col
    return None

def safe_parse_dates(df):
    date_col = None
    for col in ['race_date', '比賽日期']:
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        return None, None
    dates = df[date_col].copy()
    dates = dates.astype(str).str.strip()
    parsed = pd.to_datetime(dates, errors='coerce')
    if parsed.notna().sum() == 0:
        return None, None
    df['race_date'] = parsed
    return df, date_col

def get_latest_features(race_df, history_df):
    history_df['race_date'] = pd.to_datetime(history_df['race_date'], errors='coerce')
    latest = history_df.sort_values('race_date').groupby('horse_id').last().reset_index()
    merged = race_df.merge(latest, on='horse_id', how='left', suffixes=('', '_hist'))
    for col in FEATURES_EN:
        if col in merged.columns and col not in race_df.columns:
            hist_col = col + '_hist'
            if hist_col in merged.columns:
                merged[col] = merged[hist_col]
            else:
                merged[col] = 0
        elif col not in merged.columns:
            merged[col] = 0
        merged[col] = merged[col].fillna(0)
    for col in ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']:
        if col in race_df.columns:
            merged[col] = race_df[col].values
    return merged

def compute_stats(race_df, history_df, race_date):
    history_df = ensure_series(history_df)
    if history_df.columns.duplicated().any():
        history_df = history_df.loc[:, ~history_df.columns.duplicated(keep='first')]
    for col in ['jockey', 'trainer', 'horse_id']:
        if col not in race_df.columns:
            race_df[col] = 0
    hist = history_df[history_df['race_date'] < race_date].copy()
    if hist.empty:
        for col in ['jockey_win_rate_50', 'trainer_win_rate_50', 'avg_rank_last3',
                    'distance_win_rate', 'jockey_horse_win_rate', 'going_win_rate',
                    'draw_win_rate', 'jockey_win_rate_5', 'jockey_win_rate_10']:
            race_df[col] = 0.0
        return race_df
    if 'finish_position' not in hist.columns:
        raise KeyError("歷史數據缺少 finish_position")
    hist['finish_position'] = pd.to_numeric(hist['finish_position'], errors='coerce')
    try:
        jockey_stats = hist.groupby('jockey').apply(lambda g: (g['finish_position']==1).sum()/max(len(g),1)).reset_index(name='jockey_win_rate_50')
        race_df = race_df.merge(jockey_stats, on='jockey', how='left')
        race_df['jockey_win_rate_50'] = race_df['jockey_win_rate_50'].fillna(0)
    except:
        race_df['jockey_win_rate_50'] = 0.0
    try:
        trainer_stats = hist.groupby('trainer').apply(lambda g: (g['finish_position']==1).sum()/max(len(g),1)).reset_index(name='trainer_win_rate_50')
        race_df = race_df.merge(trainer_stats, on='trainer', how='left')
        race_df['trainer_win_rate_50'] = race_df['trainer_win_rate_50'].fillna(0)
    except:
        race_df['trainer_win_rate_50'] = 0.0
    try:
        last3 = hist.groupby('horse_id').apply(lambda g: g.sort_values('race_date').tail(3)['finish_position'].mean()).reset_index(name='avg_rank_last3')
        race_df = race_df.merge(last3, on='horse_id', how='left')
        race_df['avg_rank_last3'] = race_df['avg_rank_last3'].fillna(99)
    except:
        race_df['avg_rank_last3'] = 99.0
    try:
        def dist_win(g, dist):
            sub = g[g['distance']==dist]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['distance_win_rate'] = race_df.apply(lambda r: dist_win(hist[hist['horse_id']==r['horse_id']], r['distance']), axis=1)
    except:
        race_df['distance_win_rate'] = 0.0
    try:
        def jh_win(g, j, h):
            sub = g[(g['jockey']==j) & (g['horse_id']==h)]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['jockey_horse_win_rate'] = race_df.apply(lambda r: jh_win(hist, r['jockey'], r['horse_id']), axis=1)
    except:
        race_df['jockey_horse_win_rate'] = 0.0
    try:
        def going_win(g, go):
            sub = g[g['going']==go]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['going_win_rate'] = race_df.apply(lambda r: going_win(hist[hist['horse_id']==r['horse_id']], r['going']), axis=1)
    except:
        race_df['going_win_rate'] = 0.0
    try:
        def draw_win(g, dr):
            sub = g[g['draw']==dr]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['draw_win_rate'] = race_df.apply(lambda r: draw_win(hist[hist['horse_id']==r['horse_id']], r['draw']), axis=1)
    except:
        race_df['draw_win_rate'] = 0.0
    try:
        last_run = hist.groupby('horse_id')['race_date'].max().reset_index(name='last_date')
        race_df = race_df.merge(last_run, on='horse_id', how='left')
        race_df['days_since_last_run'] = (race_date - race_df['last_date']).dt.days.fillna(999)
    except:
        race_df['days_since_last_run'] = 999
    try:
        last_rtg = hist.groupby('horse_id').last()['rtg'].reset_index(name='last_rtg')
        race_df = race_df.merge(last_rtg, on='horse_id', how='left')
        race_df['rtg_change'] = (race_df['rtg'] - race_df['last_rtg']).fillna(0)
    except:
        race_df['rtg_change'] = 0
    try:
        race_df['races_last14days'] = race_df.apply(lambda r: len(hist[(hist['horse_id']==r['horse_id']) & (hist['race_date']>=race_date-pd.Timedelta(days=14))]), axis=1)
    except:
        race_df['races_last14days'] = 0
    for col in ['course_win_rate', 'course_avg_rank', 'weight_change', 'jockey_trainer_win_rate',
                'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
                'early_pace', 'finish_speed', 'last_trial_rank', 'last_trial_time',
                'jockey_win_rate_5', 'jockey_win_rate_10',
                'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
                'total_injuries', 'injury_severity']:
        if col not in race_df.columns:
            race_df[col] = 0
        else:
            race_df[col] = race_df[col].fillna(0)
    return race_df

@st.cache_data
def load_horse_name_map():
    try:
        df_map = pd.read_csv('horse_name_mapping.csv', encoding='utf-8-sig')
        if 'horse_id' in df_map.columns and '馬名' in df_map.columns:
            return dict(zip(df_map['horse_id'], df_map['馬名']))
    except:
        pass
    return {}

def generate_pool_recommendations(df, top_n=6):
    top_horses = df.head(top_n)
    horse_names = top_horses['馬匹名稱'].tolist()
    probs = top_horses['預測勝率'].tolist()
    def combo_score(indices):
        score = 1.0
        for i in indices:
            score *= probs[i]
        return score / len(indices)
    rec = "【獨贏】\n"
    for i, row in top_horses.head(3).iterrows():
        rec += f"  {row['馬匹名稱']} (勝率 {row['預測勝率']:.2%})\n"
    rec += "\n【位置】\n"
    for i, row in top_horses.head(4).iterrows():
        rec += f"  {row['馬匹名稱']} (勝率 {row['預測勝率']:.2%})\n"
    rec += "\n【連贏】\n"
    pairs = []
    for i in range(min(len(horse_names), 5)):
        for j in range(i+1, min(len(horse_names), 6)):
            pairs.append((combo_score([i, j]), i, j))
    pairs.sort(reverse=True)
    for _, i, j in pairs[:5]:
        rec += f"  {horse_names[i]} + {horse_names[j]}\n"
    rec += "\n【位置Q】\n"
    q_pairs = []
    for i in range(min(len(horse_names), 6)):
        for j in range(i+1, min(len(horse_names), 8)):
            if j < len(horse_names):
                q_pairs.append((combo_score([i, j]), i, j))
    q_pairs.sort(reverse=True)
    for _, i, j in q_pairs[:6]:
        rec += f"  {horse_names[i]} + {horse_names[j]}\n"
    rec += "\n【三重彩】\n"
    tierce = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                if i != j and i != k and j != k:
                    tierce.append((combo_score([i, j, k]), i, j, k))
    tierce.sort(reverse=True)
    for _, i, j, k in tierce[:5]:
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

def run_prediction(date_str, race_no):
    xgb_model, cat_model, rank_model = load_models()
    if xgb_model is None:
        return None, None

    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    except:
        st.error("讀取排位表失敗")
        return None, None

    df = standardize_columns_safe(df)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df = ensure_series(df)

    df, _ = safe_parse_dates(df)
    if df is None:
        st.error("無法解析日期")
        return None, None
    df = df.dropna(subset=['race_date'])
    if df.empty:
        st.error("無有效日期")
        return None, None

    if 'race_no' not in df.columns:
        st.error("找不到場次欄位")
        return None, None
    df['race_no'] = df['race_no'].astype(str).str.extract(r'(\d+)')[0]
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce')
    df = df.dropna(subset=['race_no'])
    if df.empty:
        st.error("無有效場次")
        return None, None

    target = pd.to_datetime(date_str)
    race_sel = df[(df['race_date'].dt.date == target.date()) & (df['race_no'] == race_no)]
    if race_sel.empty:
        st.error(f"日期 {date_str} 第 {race_no} 場無數據")
        return None, None

    try:
        history = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
    except:
        st.error("缺少歷史數據檔案 ALL_DATA_MERGED.csv")
        return None, None

    history = standardize_columns_safe(history)
    history = history.loc[:, ~history.columns.duplicated(keep='first')]
    history = ensure_series(history)
    if 'race_date' not in history.columns:
        if '比賽日期' in history.columns:
            history.rename(columns={'比賽日期': 'race_date'}, inplace=True)
        else:
            st.error("歷史數據缺少日期欄位")
            return None, None
    history['race_date'] = pd.to_datetime(history['race_date'], errors='coerce')
    history = history.dropna(subset=['race_date'])

    finish_col = get_finish_column(history)
    if finish_col is None:
        st.error("歷史數據缺少名次欄位")
        return None, None
    history.rename(columns={finish_col: 'finish_position'}, inplace=True)

    name_map = load_horse_name_map()

    race_sel = get_latest_features(race_sel, history)
    race_sel = compute_stats(race_sel, history, target)
    race_sel['中文名'] = race_sel['horse_id'].map(name_map).fillna(race_sel['horse_id'])

    if 'win_odds' not in race_sel.columns:
        race_sel['win_odds'] = 4.0
    else:
        race_sel['win_odds'] = race_sel['win_odds'].replace(0, 4.0).fillna(4.0)
    race_sel['win_odds'] = pd.to_numeric(race_sel['win_odds'], errors='coerce').fillna(4.0)
    race_sel['odds_rank_in_race'] = race_sel['win_odds'].rank(ascending=True)

    for f in FEATURES_EN:
        if f not in race_sel.columns:
            race_sel[f] = 0
        else:
            race_sel[f] = race_sel[f].fillna(0)

    X = race_sel[FEATURES_EN].copy()
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

    X.rename(columns=NAME_MAPPING, inplace=True)
    for col in EXPECTED_FEATURES:
        if col not in X.columns:
            X[col] = 0
    X = X[EXPECTED_FEATURES]

    prob_xgb = xgb_model.predict_proba(X)[:, 1]
    prob_cat = cat_model.predict_proba(X)[:, 1]
    
    xgb_w = CONFIG.get('xgb_weight', 25)
    cat_w = CONFIG.get('cat_weight', 1)
    prob_final = (prob_xgb * xgb_w + prob_cat * cat_w) / (xgb_w + cat_w)
    
    rank_score = rank_model.predict(X)

    result = race_sel[['中文名', 'draw', 'win_odds']].copy()
    result.rename(columns={'中文名': '馬匹名稱', 'draw': '檔位', 'win_odds': '賠率'}, inplace=True)
    result['預測勝率'] = prob_final
    result['值博指數'] = result['預測勝率'] / result['賠率']
    result = result.sort_values('值博指數', ascending=False)

    pool_rec = generate_pool_recommendations(result)
    return result, pool_rec

# ============================================================
# 用戶功能（完整）
# ============================================================
def record_prediction(username, date_str, race_no, horse_name, predicted_prob=None):
    users = load_users()
    if username in users:
        if 'history' not in users[username]:
            users[username]['history'] = []
        users[username]['history'].append({
            'date': date_str,
            'race': race_no,
            'horse': horse_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_prob': predicted_prob,
            'is_hit': None
        })
        save_users(users)
        acc = load_accuracy()
        if 'records' not in acc:
            acc['records'] = []
        acc['records'].append({
            'username': username,
            'date': date_str,
            'race': race_no,
            'horse': horse_name,
            'predicted_at': datetime.now().isoformat(),
            'actual_result': None,
            'is_hit': None
        })
        save_accuracy(acc)
        
        # 每次預測加 10 EXP
        update_user_exp(username, is_hit=False)

def get_user_stats(username):
    users = load_users()
    if username not in users:
        return {'total_predictions': 0, 'free_used': 0, 'is_paid': False, 'group': 'free', 'plan': None}
    user = users[username]
    history = user.get('history', [])
    total = len(history)
    free_used = user.get('free_usage', 0)
    return {
        'total_predictions': total,
        'free_used': free_used,
        'is_paid': user.get('is_paid', False),
        'group': user.get('group', 'free'),
        'plan': user.get('plan', None)
    }

def show_user_dashboard(username):
    if not username:
        return
    stats = get_user_stats(username)
    users = load_users()
    user_data = users.get(username, {})
    group = user_data.get('group', 'free')
    is_paid = user_data.get('is_paid', False)
    plan = user_data.get('plan', None)
    expiry = user_data.get('expiry_date', None)
    invite_code = user_data.get('invite_code', '')
    invite_count = user_data.get('invite_count', 0)
    invite_rewards = user_data.get('invite_rewards', 0)
    
    # 等級/勳章
    level = user_data.get('level', '🥉 銅牌會員')
    exp = user_data.get('exp', 0)
    badges = user_data.get('badges', [])
    next_level_exp = get_level_info(exp)[1]
    
    if group == 'super_admin':
        level_display = "👑 超級管理員"
    elif group == 'VIP':
        level_display = "👑 VIP"
    elif is_paid:
        level_display = "💎 付費用戶"
    else:
        level_display = "🆓 免費用戶"
    
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👤 用戶", username)
    col2.metric("🏷️ 級別", level_display)
    col3.metric("📊 總預測次數", stats['total_predictions'])
    limit = user_data.get('predictions_limit', CONFIG['free_limit'])
    if limit == -1:
        col4.metric("📊 剩餘場次", "♾️ 無限")
    else:
        used = user_data.get('free_usage', 0)
        remain = max(0, limit - used)
        col4.metric("📊 剩餘場次", remain)
    st.markdown("---")
    
    # 顯示等級/勳章
    st.subheader("🏅 用戶等級 & 勳章")
    col_level1, col_level2, col_level3 = st.columns(3)
    with col_level1:
        st.metric("🏅 當前等級", level)
    with col_level2:
        if next_level_exp:
            progress = min(100, int((exp / next_level_exp) * 100))
            st.metric("📊 經驗值", f"{exp} / {next_level_exp}")
            st.progress(progress / 100)
            st.caption(f"進度：{progress}%")
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
    else:
        st.info("📭 尚未獲得任何勳章，繼續預測解鎖更多成就！")
    
    st.markdown("---")
    
    if plan:
        st.caption(f"📌 當前方案：{get_plan_name(plan)}")
    
    if CONFIG.get("enable_invite_reward", True):
        st.markdown("---")
        st.subheader("🎁 邀請獎勵")
        col_inv1, col_inv2, col_inv3 = st.columns(3)
        with col_inv1:
            st.caption(f"你的邀請碼：**{invite_code}**")
        with col_inv2:
            st.caption(f"已成功邀請 **{invite_count}** 位朋友")
        with col_inv3:
            st.caption(f"已獲得獎勵次數：**{invite_rewards}** 次（已自動加到你的預測額度）")
    
    st.markdown("---")
    st.subheader("📊 預測統計")
    today = datetime.now().strftime('%Y-%m-%d')
    history = user_data.get('history', [])
    today_count = sum(1 for h in history if h.get('date') == today)
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        st.metric("📈 總預測", stats['total_predictions'])
    with col_p2:
        st.metric("📅 今日已用", today_count)
    with col_p3:
        if limit == -1:
            st.metric("🔮 剩餘次數", "♾️ 無限")
        else:
            remain = max(0, limit - user_data.get('free_usage', 0))
            st.metric("🔮 剩餘次數", remain)
    with col_p4:
        if st.button("🚀 去預測", use_container_width=True, key="quick_predict"):
            st.session_state.page = "預測"
            st.rerun()
    
    if today_count > 0:
        st.caption(f"📝 今日已進行 {today_count} 次預測")
    else:
        st.caption("📝 今日尚未進行預測")

def show_prediction_history(username):
    if not username:
        st.info("請先登入以查看歷史記錄")
        return
    users = load_users()
    if username not in users:
        st.info("未有歷史記錄")
        return
    history = users[username].get('history', [])
    if not history:
        st.info("你仲未有任何預測記錄")
        return
    df = pd.DataFrame(history[-20:][::-1])
    st.dataframe(df, use_container_width=True)

# ============================================================
# 登入/註冊（完整）
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
                本系統提供賽馬預測數據及分析，僅供參考及娛樂用途，並非投注建議。用戶應自行判斷，所有投注決定及後果由用戶自行承擔。

                **2. 用戶責任**
                - 用戶必須年滿 18 歲。
                - 用戶需確保所提供嘅資料真實、準確、完整。
                - 用戶不得將本系統用於任何非法或不當用途。

                **3. 免責聲明**
                - 預測結果僅為演算法分析，不構成任何形式嘅投資建議或保證。
                - 本系統不保證預測準確度，亦不對用戶因使用本系統而產生嘅任何損失負責。
                - 用戶明白賽馬活動存在風險，應量力而為。

                **4. 付款與退款**
                - 用戶付款後即表示同意購買所選方案。
                - 付款後不設退款，除非系統因技術問題未能提供服務。
                - 管理員保留最終審核及拒絕退款嘅權利。

                **5. 帳戶安全**
                - 用戶需自行保管帳號及密碼，任何經由帳戶進行嘅活動均視為用戶本人所為。
                - 如發現帳戶被盜用，應立即通知管理員。

                **6. 終止服務**
                - 管理員保留隨時終止或暫停用戶帳戶嘅權利，如用戶違反條款或進行不當行為。
                - 終止後，用戶將無法使用系統服務，已付費用將不獲退還。

                **7. 條款修訂**
                本系統有權隨時修訂服務條款，修訂後會於系統內公告。用戶繼續使用即表示同意最新條款。

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
                            'password': new_pass,
                            'phone': phone,
                            'is_paid': False,
                            'paid_date': None,
                            'expiry_date': None,
                            'free_usage': 0,
                            'total_usage': 0,
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'note': '',
                            'group': 'free',
                            'plan': None,
                            'predictions_limit': CONFIG["free_limit"],
                            'history': [],
                            'terms_agreed': datetime.now().isoformat(),
                            'invite_code': new_user.upper() + str(random.randint(100, 999)),
                            'invited_by': invited_by,
                            'invite_rewards': 0,
                            'invite_count': 0,
                            'level': '🥉 銅牌會員',
                            'exp': 0,
                            'badges': []
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
# 系統儀表板
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
    total_predictions = len(records)
    pending_payments = len([p for p in payment_proofs.get('proof_records', []) if p.get('status') == 'pending'])
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("👤 總用戶", total_users)
    col2.metric("📈 今日新增", today_new_users)
    col3.metric("💰 總收入", f"${total_income:.2f}")
    col4.metric("📊 總預測", total_predictions)
    
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
        for f in ['users.json', 'system_config.json', 'accuracy.json', 'HKCJ_FULL_YEAR_DATA.csv', 'ALL_DATA_MERGED.csv']:
            if not os.path.exists(f):
                files_missing.append(f)
        if files_missing:
            st.error(f"❌ 缺少檔案：{', '.join(files_missing)}")
        else:
            st.success("✅ 所有系統檔案正常")
    
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
                    daily = daily.sort_values('date')
                    fig = px.bar(daily, x='date', y='new_users', title='每日新增用戶')
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("最近7日沒有新用戶")
    
    with col_ch2:
        st.subheader("📊 命中率走勢（最近7日）")
        if records:
            df_records = pd.DataFrame(records)
            if 'date' in df_records.columns and 'is_hit' in df_records.columns:
                df_records['date'] = pd.to_datetime(df_records['date'])
                df_records = df_records.dropna(subset=['date', 'is_hit'])
                last_7 = datetime.now().date() - timedelta(days=7)
                df_recent = df_records[df_records['date'].dt.date >= last_7]
                if not df_recent.empty:
                    daily = df_recent.groupby(df_recent['date'].dt.date).agg(
                        total=('is_hit', 'count'),
                        hit=('is_hit', lambda x: (x==True).sum())
                    ).reset_index()
                    daily['hit_rate'] = daily['hit'] / daily['total']
                    fig = px.line(daily, x='date', y='hit_rate', title='每日命中率趨勢', markers=True)
                    fig.update_layout(height=250, yaxis_tickformat='.0%')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("最近7日沒有預測記錄")
    
    st.divider()
    
    st.subheader("🚀 快速行動")
    col_q1, col_q2, col_q3 = st.columns(3)
    with col_q1:
        if st.button("🔄 刷新數據", use_container_width=True):
            st.rerun()
    with col_q2:
        if st.button("🤖 執行維護", use_container_width=True):
            admin_auto_maintenance()
    with col_q3:
        if st.button("📥 下載所有數據", use_container_width=True):
            try:
                data = {
                    "users": load_users(),
                    "accuracy": load_accuracy(),
                    "finance": load_finance(),
                    "payment_proofs": load_payment_proofs()
                }
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="✅ 下載 backup.json",
                    data=json_str,
                    file_name=f"backup_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    key="download_backup"
                )
            except Exception as e:
                st.error(f"下載失敗：{e}")

# ============================================================
# 數據分析類（馬匹、騎師、練馬師、場地/路程）
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
    
    horse_list = []
    for horse, stats in horse_stats.items():
        if stats['total'] >= 2:
            hit_rate = stats['hit'] / stats['total']
            horse_list.append({
                '馬匹': horse,
                '總預測': stats['total'],
                '命中': stats['hit'],
                '命中率': hit_rate
            })
    
    if not horse_list:
        st.info("暫時未有足夠數據（需要每匹馬至少預測 2 次先上榜）")
        return
    
    df_horse = pd.DataFrame(horse_list)
    df_horse = df_horse.sort_values('命中率', ascending=False).reset_index(drop=True)
    
    st.subheader("🏆 勝率最高馬匹 Top 15")
    st.dataframe(df_horse.head(15), use_container_width=True)
    
    if len(df_horse) >= 3:
        fig = px.bar(
            df_horse.head(10), 
            x='馬匹', 
            y='命中率', 
            title='Top 10 馬匹命中率',
            color='命中率',
            color_continuous_scale='Blues',
            text=df_horse.head(10)['命中率'].apply(lambda x: f'{x:.1%}')
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(yaxis_tickformat='.0%', height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.caption(f"📊 共 {len(df_horse)} 匹馬符合上榜條件（最少預測 2 次）")

def admin_jockey_ranking():
    st.subheader("👨‍🏫 騎師勝率排行榜")
    
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    
    if not valid_records:
        st.info("暫時未有足夠數據（最少需要 1 場已比對嘅預測記錄）")
        return
    
    st.warning("⚠️ 騎師數據需要從排位表檔案 'HKCJ_FULL_YEAR_DATA.csv' 提取")
    st.info("💡 建議：喺預測時記錄騎師名稱，先可以統計騎師勝率")
    
    try:
        df_racecard = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df_racecard = standardize_columns_safe(df_racecard)
        if 'jockey' in df_racecard.columns and 'horse_name' in df_racecard.columns:
            horse_jockey_map = dict(zip(df_racecard['horse_name'], df_racecard['jockey']))
            
            jockey_stats = {}
            for rec in valid_records:
                horse = rec.get('horse', '')
                jockey = horse_jockey_map.get(horse, '未知騎師')
                if jockey not in jockey_stats:
                    jockey_stats[jockey] = {'total': 0, 'hit': 0}
                jockey_stats[jockey]['total'] += 1
                if rec.get('is_hit') == True:
                    jockey_stats[jockey]['hit'] += 1
            
            jockey_list = []
            for jockey, stats in jockey_stats.items():
                if stats['total'] >= 2 and jockey != '未知騎師':
                    hit_rate = stats['hit'] / stats['total']
                    jockey_list.append({
                        '騎師': jockey,
                        '總預測': stats['total'],
                        '命中': stats['hit'],
                        '命中率': hit_rate
                    })
            
            if jockey_list:
                df_jockey = pd.DataFrame(jockey_list)
                df_jockey = df_jockey.sort_values('命中率', ascending=False).reset_index(drop=True)
                st.subheader("🏆 勝率最高騎師 Top 10")
                st.dataframe(df_jockey.head(10), use_container_width=True)
                
                if len(df_jockey) >= 3:
                    fig = px.bar(
                        df_jockey.head(8),
                        x='騎師',
                        y='命中率',
                        title='Top 8 騎師命中率',
                        color='命中率',
                        color_continuous_scale='Greens',
                        text=df_jockey.head(8)['命中率'].apply(lambda x: f'{x:.1%}')
                    )
                    fig.update_traces(textposition='outside')
                    fig.update_layout(yaxis_tickformat='.0%', height=350)
                    st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📊 共 {len(df_jockey)} 位騎師符合上榜條件（最少預測 2 次）")
            else:
                st.info("暫時未有足夠騎師數據（需要馬匹對應騎師資料）")
        else:
            st.info("排位表檔案缺少 'jockey' 或 'horse_name' 欄位")
    except Exception as e:
        st.info(f"無法讀取排位表：{e}")

def admin_trainer_ranking():
    st.subheader("👨‍🏫 練馬師勝率排行榜")
    
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    
    if not valid_records:
        st.info("暫時未有足夠數據（最少需要 1 場已比對嘅預測記錄）")
        return
    
    st.warning("⚠️ 練馬師數據需要從排位表檔案 'HKCJ_FULL_YEAR_DATA.csv' 提取")
    st.info("💡 建議：喺預測時記錄練馬師名稱，先可以統計練馬師勝率")
    
    try:
        df_racecard = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df_racecard = standardize_columns_safe(df_racecard)
        if 'trainer' in df_racecard.columns and 'horse_name' in df_racecard.columns:
            horse_trainer_map = dict(zip(df_racecard['horse_name'], df_racecard['trainer']))
            
            trainer_stats = {}
            for rec in valid_records:
                horse = rec.get('horse', '')
                trainer = horse_trainer_map.get(horse, '未知練馬師')
                if trainer not in trainer_stats:
                    trainer_stats[trainer] = {'total': 0, 'hit': 0}
                trainer_stats[trainer]['total'] += 1
                if rec.get('is_hit') == True:
                    trainer_stats[trainer]['hit'] += 1
            
            trainer_list = []
            for trainer, stats in trainer_stats.items():
                if stats['total'] >= 2 and trainer != '未知練馬師':
                    hit_rate = stats['hit'] / stats['total']
                    trainer_list.append({
                        '練馬師': trainer,
                        '總預測': stats['total'],
                        '命中': stats['hit'],
                        '命中率': hit_rate
                    })
            
            if trainer_list:
                df_trainer = pd.DataFrame(trainer_list)
                df_trainer = df_trainer.sort_values('命中率', ascending=False).reset_index(drop=True)
                st.subheader("🏆 勝率最高練馬師 Top 10")
                st.dataframe(df_trainer.head(10), use_container_width=True)
                
                if len(df_trainer) >= 3:
                    fig = px.bar(
                        df_trainer.head(8),
                        x='練馬師',
                        y='命中率',
                        title='Top 8 練馬師命中率',
                        color='命中率',
                        color_continuous_scale='Oranges',
                        text=df_trainer.head(8)['命中率'].apply(lambda x: f'{x:.1%}')
                    )
                    fig.update_traces(textposition='outside')
                    fig.update_layout(yaxis_tickformat='.0%', height=350)
                    st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📊 共 {len(df_trainer)} 位練馬師符合上榜條件（最少預測 2 次）")
            else:
                st.info("暫時未有足夠練馬師數據（需要馬匹對應練馬師資料）")
        else:
            st.info("排位表檔案缺少 'trainer' 或 'horse_name' 欄位")
    except Exception as e:
        st.info(f"無法讀取排位表：{e}")

def admin_course_analysis():
    st.subheader("📊 場地/路程勝率分析")
    
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    
    if not valid_records:
        st.info("暫時未有足夠數據（最少需要 1 場已比對嘅預測記錄）")
        return
    
    st.warning("⚠️ 場地/路程數據需要從排位表檔案 'HKCJ_FULL_YEAR_DATA.csv' 提取")
    
    try:
        df_racecard = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df_racecard = standardize_columns_safe(df_racecard)
        
        if 'race_no' in df_racecard.columns and 'distance' in df_racecard.columns:
            race_distance_map = dict(zip(df_racecard['race_no'], df_racecard['distance']))
            race_going_map = {}
            if 'going' in df_racecard.columns:
                race_going_map = dict(zip(df_racecard['race_no'], df_racecard['going']))
            
            distance_stats = {}
            going_stats = {}
            
            for rec in valid_records:
                race_no = rec.get('race')
                distance = race_distance_map.get(race_no, '未知')
                
                if distance not in distance_stats:
                    distance_stats[distance] = {'total': 0, 'hit': 0}
                distance_stats[distance]['total'] += 1
                if rec.get('is_hit') == True:
                    distance_stats[distance]['hit'] += 1
                
                going = race_going_map.get(race_no, '未知')
                if going not in going_stats:
                    going_stats[going] = {'total': 0, 'hit': 0}
                going_stats[going]['total'] += 1
                if rec.get('is_hit') == True:
                    going_stats[going]['hit'] += 1
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏇 路程勝率分析")
                distance_list = []
                for dist, stats in distance_stats.items():
                    if stats['total'] >= 2:
                        hit_rate = stats['hit'] / stats['total']
                        distance_list.append({
                            '路程': dist,
                            '總預測': stats['total'],
                            '命中': stats['hit'],
                            '命中率': hit_rate
                        })
                if distance_list:
                    df_dist = pd.DataFrame(distance_list)
                    df_dist = df_dist.sort_values('命中率', ascending=False).reset_index(drop=True)
                    st.dataframe(df_dist, use_container_width=True)
                    
                    if len(df_dist) >= 2:
                        fig = px.bar(
                            df_dist.head(8),
                            x='路程',
                            y='命中率',
                            title='各路程命中率',
                            color='命中率',
                            color_continuous_scale='Purples',
                            text=df_dist.head(8)['命中率'].apply(lambda x: f'{x:.1%}')
                        )
                        fig.update_traces(textposition='outside')
                        fig.update_layout(yaxis_tickformat='.0%', height=300)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("未有足夠路程數據（最少預測 2 次）")
            
            with col2:
                st.subheader("🌤️ 場地勝率分析")
                going_list = []
                for going, stats in going_stats.items():
                    if stats['total'] >= 2 and going != '未知':
                        hit_rate = stats['hit'] / stats['total']
                        going_list.append({
                            '場地': going,
                            '總預測': stats['total'],
                            '命中': stats['hit'],
                            '命中率': hit_rate
                        })
                if going_list:
                    df_going = pd.DataFrame(going_list)
                    df_going = df_going.sort_values('命中率', ascending=False).reset_index(drop=True)
                    st.dataframe(df_going, use_container_width=True)
                    
                    if len(df_going) >= 2:
                        fig = px.bar(
                            df_going,
                            x='場地',
                            y='命中率',
                            title='各場地命中率',
                            color='命中率',
                            color_continuous_scale='Blues',
                            text=df_going['命中率'].apply(lambda x: f'{x:.1%}')
                        )
                        fig.update_traces(textposition='outside')
                        fig.update_layout(yaxis_tickformat='.0%', height=300)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("未有足夠場地數據（最少預測 2 次）")
        else:
            st.info("排位表檔案缺少 'race_no' 或 'distance' 欄位")
    except Exception as e:
        st.info(f"無法讀取排位表：{e}")

def admin_monthly_report():
    st.subheader("📅 每月命中率報告")
    
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    
    if not valid_records:
        st.info("暫時未有足夠數據（最少需要 1 場已比對嘅預測記錄）")
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
    monthly = monthly.sort_values('month_str')
    
    st.subheader("📊 每月命中率總表")
    st.dataframe(monthly, use_container_width=True)
    
    fig = px.bar(
        monthly,
        x='month_str',
        y='hit_rate',
        title='每月命中率',
        color='hit_rate',
        color_continuous_scale='RdYlGn',
        text=monthly['hit_rate'].apply(lambda x: f'{x:.1%}')
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(yaxis_tickformat='.0%', height=350)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    st.subheader("📥 下載報告")
    
    csv_data = monthly.to_csv(index=False)
    st.download_button(
        label="📥 下載每月命中率報告 (CSV)",
        data=csv_data,
        file_name=f"monthly_report_{datetime.now().strftime('%Y%m')}.csv",
        mime="text/csv",
        key="download_monthly_report"
    )
    
    json_data = json.dumps(monthly.to_dict(orient='records'), ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 下載每月命中率報告 (JSON)",
        data=json_data,
        file_name=f"monthly_report_{datetime.now().strftime('%Y%m')}.json",
        mime="application/json",
        key="download_monthly_report_json"
    )
    
    st.caption("💡 提示：CSV 同 JSON 檔案可用 Excel 打開，或轉換成 PDF")

# ============================================================
# 後台管理（所有模組完整實作）
# ============================================================
def admin_user_management():
    st.subheader("👥 用戶管理")
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
                users = load_users()
                if new_username in users:
                    st.error("❌ 用戶名已被使用")
                else:
                    users[new_username] = {
                        "password": new_password,
                        "is_paid": new_is_paid,
                        "paid_date": None,
                        "expiry_date": None,
                        "free_usage": 0,
                        "total_usage": 0,
                        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "note": "手動新增",
                        "group": new_group,
                        "phone": "",
                        "plan": None,
                        "predictions_limit": -1 if new_group in ['super_admin', 'VIP'] else CONFIG["free_limit"],
                        "history": [],
                        "terms_agreed": datetime.now().isoformat(),
                        "invite_code": new_username.upper() + str(random.randint(100, 999)),
                        "invited_by": None,
                        "invite_rewards": 0,
                        "invite_count": 0,
                        "level": "🥉 銅牌會員",
                        "exp": 0,
                        "badges": []
                    }
                    save_users(users)
                    log_admin_action(st.session_state.username, f"新增用戶 {new_username}")
                    st.success(f"✅ 用戶 {new_username} 已建立！")
                    st.rerun()
    
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return
    
    st.write("現有用戶列表：")
    df = pd.DataFrame.from_dict(users, orient='index')
    if 'level' not in df.columns:
        df['level'] = '🥉 銅牌會員'
    if 'exp' not in df.columns:
        df['exp'] = 0
    if 'badges' not in df.columns:
        df['badges'] = ''
    df['badges_count'] = df['badges'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    display_cols = ['username', 'group', 'level', 'exp', 'badges_count', 'total_usage', 'is_paid']
    available_cols = [col for col in display_cols if col in df.columns]
    st.dataframe(df[available_cols], use_container_width=True)
    
    st.divider()
    st.subheader("🗑️ 刪除用戶")
    del_user = st.selectbox("選擇要刪除嘅用戶", list(users.keys()), key="del_user_select")
    if del_user:
        if del_user == "admin":
            st.warning("⚠️ 唔可以刪除 admin 帳號")
        else:
            confirm = st.checkbox(f"確認刪除 {del_user}？", key="confirm_del")
            if confirm and st.button("🗑️ 確認刪除", key="del_user_btn"):
                users.pop(del_user)
                save_users(users)
                log_admin_action(st.session_state.username, f"刪除用戶 {del_user}")
                st.success(f"✅ 用戶 {del_user} 已刪除")
                st.rerun()
    
    st.divider()
    st.subheader("👁️ 查看用戶視角")
    selected_user = st.selectbox("選擇要查看的用戶", list(users.keys()), key="view_user_select")
    if selected_user:
        user_data = users[selected_user]
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👤 用戶", selected_user)
        col2.metric("🏷️ 級別", user_data.get('group', 'free').upper())
        col3.metric("📊 總預測次數", len(user_data.get('history', [])))
        limit = user_data.get('predictions_limit', CONFIG['free_limit'])
        if limit == -1:
            col4.metric("📊 剩餘場次", "♾️ 無限")
        else:
            used = user_data.get('free_usage', 0)
            remain = max(0, limit - used)
            col4.metric("📊 剩餘場次", remain)
        st.markdown("---")
        st.subheader(f"📋 {selected_user} 嘅預測記錄")
        history = user_data.get('history', [])
        if history:
            df_hist = pd.DataFrame(history[-20:][::-1])
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("呢個用戶暫時冇任何預測記錄")
        if history:
            st.subheader(f"🎯 {selected_user} 嘅準確度統計")
            acc = load_accuracy()
            records = acc.get('records', [])
            user_records = [r for r in records if r.get('username') == selected_user]
            if user_records:
                df_rec = pd.DataFrame(user_records)
                total = len(df_rec)
                hit = df_rec[df_rec['is_hit'] == True].shape[0] if 'is_hit' in df_rec else 0
                hit_rate = hit/total if total>0 else 0
                roi = (hit * 400 - total * 100) / (total * 100) if total>0 else 0
                col1, col2, col3 = st.columns(3)
                col1.metric("總預測", total)
                col2.metric("命中", hit)
                col3.metric("命中率", f"{hit_rate:.2%}")
                st.metric("ROI (模擬)", f"{roi:.2%}")
                if 'date' in df_rec:
                    df_rec['date'] = pd.to_datetime(df_rec['date'])
                    daily = df_rec.groupby(df_rec['date'].dt.date).agg(
                        total=('is_hit', 'count'),
                        hit=('is_hit', lambda x: (x==True).sum())
                    ).reset_index()
                    daily['hit_rate'] = daily['hit'] / daily['total']
                    fig = px.line(daily, x='date', y='hit_rate', title=f'{selected_user} 嘅命中率趨勢')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("呢個用戶未有準確度數據（未對比賽果）")
    
    # 編輯用戶（包含等級/勳章編輯）
    with st.expander("✏️ 編輯用戶"):
        username = st.selectbox("選擇要編輯的用戶", list(users.keys()), key="edit_user_select")
        if username:
            user = users[username]
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                new_group = st.selectbox("群組", ['free', 'paid', 'VIP', 'super_admin'], index=['free','paid','VIP','super_admin'].index(user.get('group','free')), key="edit_group")
                new_is_paid = st.checkbox("付費狀態", value=user.get('is_paid', False), key="edit_is_paid")
                new_password = st.text_input("新密碼（留空 = 不變）", type="password", key="edit_password", placeholder="輸入新密碼")
            
            with col_edit2:
                # 編輯等級
                level_options = ["🥉 銅牌會員", "🥈 銀牌會員", "🥇 金牌會員", "💎 鑽石會員", "👑 傳說會員", "👑 超級管理員"]
                current_level = user.get('level', '🥉 銅牌會員')
                if current_level not in level_options:
                    level_options.append(current_level)
                new_level = st.selectbox("🏅 等級", level_options, index=level_options.index(current_level) if current_level in level_options else 0, key="edit_level")
                
                # 編輯經驗值
                new_exp = st.number_input("📊 經驗值", min_value=0, value=user.get('exp', 0), step=10, key="edit_exp")
                
                # 編輯勳章
                all_badges = ["🏆 首勝", "🔥 三連勝", "⚡ 五連勝", "💯 百場預測", "🎯 命中大師", "👥 社交達人", "💰 付費會員", "🏇 馬匹專家"]
                current_badges = user.get('badges', [])
                new_badges = st.multiselect("🎖️ 勳章", all_badges, default=[b for b in current_badges if b in all_badges], key="edit_badges")
            
            note = st.text_area("備註", value=user.get('note', ''), key="edit_note")
            
            if st.button("💾 儲存變更", key="save_user_changes"):
                users[username]['group'] = new_group
                users[username]['is_paid'] = new_is_paid
                users[username]['note'] = note
                users[username]['level'] = new_level
                users[username]['exp'] = new_exp
                users[username]['badges'] = new_badges
                if new_password:
                    users[username]['password'] = new_password
                if new_group in ['super_admin', 'VIP']:
                    users[username]['predictions_limit'] = -1
                else:
                    users[username]['predictions_limit'] = CONFIG["free_limit"]
                save_users(users)
                log_admin_action(st.session_state.username, f"編輯用戶 {username}（等級：{new_level}，勳章：{len(new_badges)}個）")
                st.success("✅ 已更新用戶資料！")
                st.rerun()
    
    st.divider()
    st.subheader("📥 數據匯出")
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            data = f.read()
        st.download_button(
            label="📥 下載 users.json",
            data=data,
            file_name="users.json",
            mime="application/json",
            key="download_users_json"
        )
    except Exception as e:
        st.error(f"讀取檔案失敗：{e}")

def admin_manage_predictions():
    st.subheader("📊 管理用戶預測次數")
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return

    username_list = list(users.keys())
    selected_user = st.selectbox("選擇用戶", username_list, key="manage_predictions_user")

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

        action = st.radio(
            "選擇操作",
            ["增加次數", "減少次數", "設定為指定次數"],
            horizontal=True,
            key="predictions_action"
        )

        if action == "增加次數":
            add_amount = st.number_input("增加次數", min_value=1, step=1, value=1, key="add_predictions")
            if st.button("✅ 增加", type="primary", key="confirm_add_predictions"):
                if current_limit == -1:
                    st.warning("⚠️ 此用戶已是無限次數，無需增加")
                else:
                    users[selected_user]['predictions_limit'] = current_limit + add_amount
                    save_users(users)
                    log_admin_action(st.session_state.username, f"為 {selected_user} 增加 {add_amount} 次預測")
                    st.success(f"✅ 已為 {selected_user} 增加 {add_amount} 次預測（新上限：{current_limit + add_amount}）")
                    st.rerun()

        elif action == "減少次數":
            reduce_amount = st.number_input("減少次數", min_value=1, step=1, value=1, key="reduce_predictions")
            if st.button("✅ 減少", type="primary", key="confirm_reduce_predictions"):
                if current_limit == -1:
                    st.warning("⚠️ 此用戶是無限次數，無法減少")
                elif current_limit - reduce_amount < 0:
                    st.error(f"❌ 減少後次數不能低於 0（目前為 {current_limit}）")
                else:
                    users[selected_user]['predictions_limit'] = current_limit - reduce_amount
                    save_users(users)
                    log_admin_action(st.session_state.username, f"為 {selected_user} 減少 {reduce_amount} 次預測")
                    st.success(f"✅ 已為 {selected_user} 減少 {reduce_amount} 次預測（新上限：{current_limit - reduce_amount}）")
                    st.rerun()

        elif action == "設定為指定次數":
            set_amount = st.number_input(
                "設定為指定次數（輸入 -1 = 無限）",
                min_value=-1,
                step=1,
                value=current_limit if current_limit != -1 else 10,
                key="set_predictions"
            )
            if st.button("✅ 設定", type="primary", key="confirm_set_predictions"):
                users[selected_user]['predictions_limit'] = set_amount
                save_users(users)
                log_admin_action(st.session_state.username, f"將 {selected_user} 預測次數設定為 {set_amount}")
                display_text = "無限" if set_amount == -1 else str(set_amount)
                st.success(f"✅ 已將 {selected_user} 的預測次數設為 {display_text}")
                st.rerun()

        st.divider()
        st.caption("💡 提示：修改會即時生效，用戶無需重新登入")

def admin_auto_maintenance():
    st.subheader("🤖 自動維護")
    st.info("一鍵執行所有維護任務，系統會自動幫你完成以下操作：")
    
    tasks = [
        "🔄 比對賽果 + 更新統計",
        "⚖️ 調整模型權重（根據命中率）",
        "⏰ 檢查並終止過期會員",
        "📊 同步用戶數據（session → 檔案）",
        "📝 檢查系統檔案狀態",
        "📥 自動備份所有數據"
    ]
    
    for task in tasks:
        st.write(f"• {task}")
    
    st.divider()
    
    if st.button("🚀 執行全部維護任務", type="primary", use_container_width=True):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔄 比對賽果中...")
        updated, msg = update_accuracy_with_results()
        results.append(f"🔄 比對賽果：{msg}")
        progress_bar.progress(15)
        
        status_text.text("⚖️ 調整權重中...")
        try:
            weight_result = adjust_model_weights()
            results.append(f"⚖️ 調整權重：XGB={weight_result['xgb_weight']}, Cat={weight_result['cat_weight']}（命中率 {weight_result['hit_rate']:.2%}）")
        except Exception as e:
            results.append(f"⚖️ 調整權重：失敗 - {str(e)}")
        progress_bar.progress(30)
        
        status_text.text("⏰ 檢查過期會員中...")
        users = load_users()
        today = datetime.now()
        expired = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    exp = pd.to_datetime(u['expiry_date'])
                    if exp < today:
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        u['plan'] = None
                        u['note'] = (u.get('note', '') + f' [於 {today.strftime("%Y-%m-%d")} 自動降級]').strip()
                        expired.append(uid)
                except:
                    pass
        if expired:
            save_users(users)
            results.append(f"⏰ 檢查過期會員：已將 {len(expired)} 個過期會員降級：{', '.join(expired)}")
        else:
            results.append("⏰ 檢查過期會員：目前沒有過期會員")
        progress_bar.progress(45)
        
        status_text.text("📊 同步用戶數據中...")
        try:
            if 'temp_new_users' in st.session_state:
                file_users = load_json(USER_DATA_FILE)
                synced = 0
                for username, user_data in st.session_state.temp_new_users.items():
                    if username not in file_users:
                        file_users[username] = user_data
                        synced += 1
                if synced > 0:
                    save_json(USER_DATA_FILE, file_users)
                    results.append(f"📊 同步用戶數據：已同步 {synced} 個新用戶到檔案")
                else:
                    results.append("📊 同步用戶數據：無需同步")
            else:
                results.append("📊 同步用戶數據：無需同步")
        except Exception as e:
            results.append(f"📊 同步用戶數據：失敗 - {str(e)}")
        progress_bar.progress(60)
        
        status_text.text("📝 檢查系統檔案中...")
        files_to_check = [
            'users.json', 'system_config.json', 'finance.json',
            'promo_codes.json', 'admin_log.json', 'accuracy.json',
            'payment_proofs.json', 'HKCJ_FULL_YEAR_DATA.csv', 'ALL_DATA_MERGED.csv'
        ]
        file_status = []
        for f in files_to_check:
            exists = os.path.exists(f)
            size = os.path.getsize(f) if exists else 0
            status = "✅" if exists else "❌"
            file_status.append(f"{status} {f} ({size} bytes)" if exists else f"{status} {f} (不存在)")
        results.append(f"📝 檢查系統檔案：{' | '.join(file_status[:5])}")
        progress_bar.progress(80)
        
        status_text.text("📥 自動備份中...")
        try:
            backup_data = {
                "users": load_users(),
                "accuracy": load_accuracy(),
                "finance": load_finance(),
                "payment_proofs": load_payment_proofs(),
                "backup_time": datetime.now().isoformat(),
                "version": "v14.0-用戶體驗版"
            }
            backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.json"
            
            try:
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    f.write(backup_json)
                results.append(f"📥 自動備份：已儲存到伺服器 ({backup_filename})")
            except:
                results.append("📥 自動備份：無法儲存到伺服器，但可下載")
            
            st.download_button(
                label=f"📥 下載備份 ({timestamp})",
                data=backup_json,
                file_name=backup_filename,
                mime="application/json",
                key=f"auto_backup_{timestamp}"
            )
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
        
        acc = load_accuracy()
        records = acc.get('records', [])
        total = len([r for r in records if r.get('is_hit') is not None])
        hit = sum(1 for r in records if r.get('is_hit') is True)
        hit_rate = hit/total if total>0 else 0
        if total > 0:
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 已比對預測", total)
            col2.metric("🎯 命中次數", hit)
            col3.metric("📈 整體命中率", f"{hit_rate:.2%}")
    
    st.divider()
    st.subheader("⚡ 單獨執行")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 比對賽果", use_container_width=True):
            updated, msg = update_accuracy_with_results()
            st.success(f"✅ {msg}")
            st.rerun()
    with col2:
        if st.button("⚖️ 調整權重", use_container_width=True):
            result = adjust_model_weights()
            st.success(f"✅ XGB={result['xgb_weight']}, Cat={result['cat_weight']}（命中率 {result['hit_rate']:.2%}）")
            st.rerun()
    with col3:
        if st.button("⏰ 終止過期會員", use_container_width=True):
            users = load_users()
            today = datetime.now()
            expired = []
            for uid, u in users.items():
                if u.get('group') == 'VIP' and u.get('expiry_date'):
                    try:
                        exp = pd.to_datetime(u['expiry_date'])
                        if exp < today:
                            u['group'] = 'free'
                            u['is_paid'] = False
                            u['predictions_limit'] = CONFIG["free_limit"]
                            u['plan'] = None
                            expired.append(uid)
                    except:
                        pass
            if expired:
                save_users(users)
                st.success(f"✅ 已將 {len(expired)} 個過期會員降級：{', '.join(expired)}")
            else:
                st.info("✅ 目前沒有過期會員")
            st.rerun()

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
                          title='每日新增用戶 & 累積用戶', 
                          labels={'value':'用戶數', 'date':'日期'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("未有 created_at 數據，無法顯示增長圖")
    else:
        st.info("暫無用戶")

def admin_finance():
    st.subheader("💰 財務管理")
    finance = load_finance()
    total_income = finance.get('total_income', 0)
    monthly = finance.get('monthly_income', 0)
    yearly = finance.get('yearly_income', 0)
    col1, col2, col3 = st.columns(3)
    col1.metric("總收入 (HKD)", f"${total_income:.2f}")
    col2.metric("本月收入 (HKD)", f"${monthly:.2f}")
    col3.metric("今年收入 (HKD)", f"${yearly:.2f}")
    
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

def admin_promo_codes():
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()
    col1, col2 = st.columns(2)
    with col1:
        st.write("現有優惠碼")
        if promos:
            df = pd.DataFrame.from_dict(promos, orient='index')
            if 'discount_type' not in df.columns:
                df['discount_type'] = 'percentage'
            if 'discount_value' not in df.columns:
                df['discount_value'] = 0
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暫無優惠碼")
    with col2:
        st.write("產生新優惠碼")
        duration = st.number_input("有效期 (天)", min_value=1, value=30, key="promo_duration")
        discount_type = st.selectbox("折扣類型", ["percentage", "fixed", "free"], key="promo_discount_type",
                                     format_func=lambda x: {"percentage": "百分比（%折扣）", "fixed": "固定金額（減$）", "free": "完全免費"}.get(x, x))
        discount_value = st.number_input("折扣數值", min_value=0, value=20, key="promo_discount_value", 
                                         help="百分比：20 = 8折（減20%）；固定金額：減指定金額；免費：無效")
        if st.button("產生優惠碼", key="gen_promo"):
            code = generate_promo_code()
            expiry = (datetime.now() + timedelta(days=duration)).isoformat()
            promos[code] = {
                "used": False,
                "expiry": expiry,
                "created_at": datetime.now().isoformat(),
                "discount_type": discount_type,
                "discount_value": discount_value
            }
            save_promos(promos)
            st.success(f"✅ 優惠碼已產生：`{code}` 有效期 {duration} 天")
            st.rerun()
        
        st.write("---")
        st.write("套用優惠碼")
        code_input = st.text_input("優惠碼", key="apply_promo_code")
        username_input = st.text_input("用戶名稱", key="apply_promo_user")
        if st.button("套用", key="apply_promo"):
            if code_input not in promos:
                st.error("優惠碼不存在")
            elif promos[code_input].get('used', False):
                st.error("優惠碼已被使用")
            else:
                users = load_users()
                if username_input not in users:
                    st.error("用戶不存在")
                else:
                    users[username_input]['is_paid'] = True
                    users[username_input]['group'] = 'paid'
                    users[username_input]['predictions_limit'] = -1
                    promos[code_input]['used'] = True
                    promos[code_input]['used_by'] = username_input
                    save_users(users)
                    save_promos(promos)
                    log_admin_action(st.session_state.username, f"套用優惠碼 {code_input} 給 {username_input}")
                    st.success("✅ 已升級用戶")
                    st.rerun()

def admin_accuracy_monitor():
    st.subheader("📈 預測準確率監控")
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        st.info("暫時未有預測記錄，未能進行監控。")
        return

    try:
        results_df = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
        results_df = standardize_columns_safe(results_df)
        results_df = results_df.loc[:, ~results_df.columns.duplicated()]
        
        if 'race_date' not in results_df.columns or 'race_no' not in results_df.columns or '馬名' not in results_df.columns or 'finish_position' not in results_df.columns:
            if '日期' in results_df.columns:
                results_df.rename(columns={'日期': 'race_date'}, inplace=True)
            if '場次' in results_df.columns:
                results_df.rename(columns={'場次': 'race_no'}, inplace=True)
            if '馬名' not in results_df.columns and 'horse_name' in results_df.columns:
                results_df.rename(columns={'horse_name': '馬名'}, inplace=True)
            if 'finish_position' not in results_df.columns and '名次' in results_df.columns:
                results_df.rename(columns={'名次': 'finish_position'}, inplace=True)
        
        if 'race_date' in results_df.columns and 'race_no' in results_df.columns and '馬名' in results_df.columns and 'finish_position' in results_df.columns:
            results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
            results_df = results_df.dropna(subset=['race_date'])
            for rec in records:
                if rec.get('actual_result') is not None:
                    continue
                date_str = rec['date']
                race_no = rec['race']
                horse = rec['horse']
                matched = results_df[(results_df['race_date'].dt.strftime('%Y-%m-%d') == date_str) & 
                                     (results_df['race_no'] == race_no) & 
                                     (results_df['馬名'] == horse)]
                if not matched.empty:
                    pos = matched.iloc[0]['finish_position']
                    rec['actual_result'] = int(pos) if pd.notna(pos) else None
                    rec['is_hit'] = (rec['actual_result'] == 1) if rec['actual_result'] is not None else None
            save_accuracy(acc)
            st.success("✅ 已自動比對賽果")
        else:
            st.warning("ALL_DATA_MERGED.csv 缺少必要欄位，請確保包含：race_date, race_no, 馬名, finish_position")
    except Exception as e:
        st.error(f"自動比對失敗：{e}")

    df_records = pd.DataFrame(records)
    if df_records.empty:
        return
    total = len(df_records)
    hit = df_records[df_records['is_hit'] == True].shape[0] if 'is_hit' in df_records else 0
    hit_rate = hit/total if total>0 else 0
    roi = (hit * 400 - total * 100) / (total * 100) if total>0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("總預測記錄", total)
    col2.metric("命中次數", hit)
    col3.metric("命中率", f"{hit_rate:.2%}")
    st.metric("ROI (模擬)", f"{roi:.2%}")

    if 'date' in df_records:
        df_records['date'] = pd.to_datetime(df_records['date'])
        daily = df_records.groupby(df_records['date'].dt.date).agg(
            total=('is_hit', 'count'),
            hit=('is_hit', lambda x: (x==True).sum())
        ).reset_index()
        daily['hit_rate'] = daily['hit'] / daily['total']
        fig = px.line(daily, x='date', y='hit_rate', title='每日命中率趨勢')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 查看所有記錄"):
        st.dataframe(df_records, use_container_width=True)

    st.divider()
    st.subheader("🔧 管理員操作")
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
                st.success(f"✅ 權重已調整：XGBoost = {result['xgb_weight']}, CatBoost = {result['cat_weight']}（命中率 {result['hit_rate']:.2%}，共 {result['total']} 場）")
                st.rerun()
    st.caption("🔒 此操作僅限管理員使用，會影響系統預測權重")

def admin_subscription():
    st.subheader("⏰ 訂閱管理 & 到期提醒")
    users = load_users()
    paid_users = {u: data for u, data in users.items() if data.get('is_paid', False) or data.get('group') in ['VIP', 'super_admin']}
    if not paid_users:
        st.info("暫時沒有付費用戶")
    else:
        df_paid = pd.DataFrame.from_dict(paid_users, orient='index')
        required_cols = ['is_paid', 'group', 'plan', 'paid_date', 'expiry_date']
        for col in required_cols:
            if col not in df_paid.columns:
                df_paid[col] = None
        df_paid['expiry_date'] = pd.to_datetime(df_paid['expiry_date'], errors='coerce')
        today = datetime.now()
        df_paid['days_left'] = (df_paid['expiry_date'] - today).dt.days
        df_paid['status'] = df_paid['days_left'].apply(lambda x: '🟢 有效' if x > 7 else ('🟡 快到期' if x > 0 else '🔴 已過期') if pd.notna(x) else '⚪ 未設定')
        display_cols = ['is_paid', 'group', 'plan', 'paid_date', 'expiry_date', 'days_left', 'status']
        st.dataframe(df_paid[display_cols], use_container_width=True)

    auto = load_json(AUTOMATION_FILE)
    remind_days = auto.get('remind_days', 3)
    new_remind = st.number_input("提前幾天提醒", min_value=1, value=remind_days, key="remind_days_sub")
    if st.button("儲存提醒設定", key="save_remind_sub"):
        auto['remind_days'] = new_remind
        save_json(AUTOMATION_FILE, auto)
        st.success(f"✅ 已設為提前 {new_remind} 天提醒")
        log_admin_action(st.session_state.username, f"設定提醒天數為 {new_remind}")

    st.divider()
    st.subheader("⏰ 自動終止過期會員")
    
    if st.button("🔍 檢查並終止過期會員", key="check_expired"):
        users = load_users()
        today = datetime.now()
        expired = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    exp = pd.to_datetime(u['expiry_date'])
                    if exp < today:
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        u['plan'] = None
                        u['note'] = (u.get('note', '') + f' [於 {today.strftime("%Y-%m-%d")} 自動降級]').strip()
                        expired.append(uid)
                except Exception as e:
                    st.warning(f"⚠️ 檢查 {uid} 時出錯：{e}")
        if expired:
            save_users(users)
            st.success(f"✅ 已將 {len(expired)} 個過期會員降級：{', '.join(expired)}")
            log_admin_action(st.session_state.username, f"自動終止過期會員：{', '.join(expired)}")
        else:
            st.info("✅ 目前沒有過期會員")

    st.subheader("✏️ 手動續期")
    username = st.selectbox("選擇用戶", list(users.keys()), key="renew_user_select")
    if username:
        new_expiry = st.date_input("新的到期日", value=pd.to_datetime(datetime.now() + timedelta(days=30)), key="renew_date")
        if st.button("確認續期", key="renew_confirm"):
            users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
            save_users(users)
            log_admin_action(st.session_state.username, f"續期用戶 {username} 至 {new_expiry}")
            st.success(f"✅ {username} 已續期至 {new_expiry}")
            st.rerun()

def admin_monitoring():
    st.subheader("📡 系統監控")
    files = ['ALL_DATA_MERGED.csv', 'HKCJ_FULL_YEAR_DATA.csv', 'horse_name_mapping.csv',
             'hk_racing_model.pkl', 'hk_catboost_model.cbm', 'hk_ranking_model.pkl']
    for f in files:
        if os.path.exists(f):
            size = os.path.getsize(f)/1024
            st.success(f"✅ {f} 存在 ({size:.1f} KB)")
        else:
            st.error(f"❌ {f} 不存在")
    logs = load_logs()
    if logs.get('logs'):
        df_log = pd.DataFrame(logs['logs'][-20:])
        st.dataframe(df_log, use_container_width=True)

def admin_content():
    st.subheader("📝 內容管理")
    content = load_json(CONTENT_FILE)
    
    with st.expander("📢 發佈新公告", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("公告標題", placeholder="例如：今日沙田日馬", key="ann_title")
            content_text = st.text_area("公告內容", height=80, placeholder="輸入公告詳細內容...", key="ann_content")
        with col2:
            ann_type = st.selectbox("公告類型", ["一般", "重要", "緊急"], key="ann_type")
            target_group = st.selectbox("顯示對象", ["全部用戶", "免費用戶", "付費用戶", "VIP"], key="ann_target")
            start_date = st.date_input("開始日期", value=datetime.now().date(), key="ann_start")
            end_date = st.date_input("結束日期（留空 = 永久）", value=None, key="ann_end")
        if st.button("📤 發佈公告", type="primary", key="publish_ann"):
            if not title or not content_text:
                st.warning("請填寫標題同內容")
            else:
                if 'announcements' not in content:
                    content['announcements'] = []
                new_ann = {
                    "id": len(content['announcements']) + 1,
                    "title": title,
                    "content": content_text,
                    "type": ann_type,
                    "target": target_group,
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d') if end_date else None,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "active"
                }
                content['announcements'].append(new_ann)
                save_json(CONTENT_FILE, content)
                log_admin_action(st.session_state.username, f"發佈公告：{title}")
                st.success("✅ 公告已發佈！")
                st.rerun()
    
    st.subheader("📋 現有公告")
    announcements = content.get('announcements', [])
    today = datetime.now().date()
    for ann in announcements:
        if ann.get('status') == 'active' and ann.get('end_date'):
            end = datetime.strptime(ann['end_date'], '%Y-%m-%d').date()
            if end < today:
                ann['status'] = 'expired'
    save_json(CONTENT_FILE, content)
    content = load_json(CONTENT_FILE)
    active_anns = [a for a in content.get('announcements', []) if a.get('status') == 'active']
    
    if active_anns:
        for ann in active_anns:
            type_icon = {"一般": "💡", "重要": "⚠️", "緊急": "🚨"}.get(ann.get('type', '一般'), "💡")
            target_label = ann.get('target', '全部用戶')
            end_display = "永久" if ann.get('end_date') is None else ann.get('end_date')
            col1, col2, col3 = st.columns([5, 3, 1])
            with col1:
                st.markdown(f"**{type_icon} {ann.get('title', '無標題')}**")
                st.caption(ann.get('content', ''))
            with col2:
                st.write(f"🎯 {target_label}")
                st.write(f"📅 {ann.get('start_date', '')} → {end_display}")
            with col3:
                if st.button("🗑️ 刪除", key=f"del_ann_{ann.get('id')}"):
                    ann['status'] = 'deleted'
                    save_json(CONTENT_FILE, content)
                    st.rerun()
            st.divider()
    else:
        st.info("暫時冇生效中嘅公告")
    
    with st.expander("📋 公告歷史（已過期/已刪除）"):
        inactive = [a for a in content.get('announcements', []) if a.get('status') in ['expired', 'deleted']]
        if inactive:
            df = pd.DataFrame(inactive)
            st.dataframe(df[['id', 'title', 'type', 'target', 'start_date', 'end_date', 'status', 'created_at']], use_container_width=True)
        else:
            st.info("暫無歷史記錄")
    
    st.write("---")
    st.write("上傳排位表")
    uploaded = st.file_uploader("選擇 CSV 排位表", type=['csv'], key="upload_racecard")
    if uploaded:
        with open('HKCJ_FULL_YEAR_DATA.csv', 'wb') as f:
            f.write(uploaded.getbuffer())
        st.success("✅ 排位表已更新")

def admin_automation():
    st.subheader("🤖 自動化工具")
    auto = load_json(AUTOMATION_FILE)
    days = st.number_input(
        "提前幾天提醒",
        min_value=1,
        value=auto.get('remind_days', 3),
        key="remind_days_auto"
    )
    if st.button("儲存設定", key="save_remind_auto"):
        auto['remind_days'] = days
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")

def admin_automation():
    st.subheader("🤖 自動化工具")
    auto = load_json(AUTOMATION_FILE)
    days = st.number_input(
        "提前幾天提醒",
        min_value=1,
        value=auto.get('remind_days', 3),
        key="remind_days_auto"
    )
    if st.button("儲存設定", key="save_remind_auto"):
        auto['remind_days'] = days
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")

def admin_security():
    st.subheader("🔐 安全與權限")
    st.write("操作日誌")
    logs = load_logs()
    if logs.get('logs'):
        df_log = pd.DataFrame(logs['logs'][-20:])
        st.dataframe(df_log, use_container_width=True)
    st.write("多管理員管理")
    users = load_users()
    admin_list = [u for u, d in users.items() if d.get('group') == 'super_admin']
    st.write("現有超級管理員：", ", ".join(admin_list) if admin_list else "無")
    new_admin = st.text_input("新增超級管理員用戶名", key="new_admin_name")
    if st.button("設為超級管理員", key="add_admin"):
        if new_admin in users:
            users[new_admin]['group'] = 'super_admin'
            users[new_admin]['is_admin'] = True
            users[new_admin]['predictions_limit'] = -1
            save_users(users)
            log_admin_action(st.session_state.username, f"新增超級管理員 {new_admin}")
            st.success(f"✅ {new_admin} 已設為超級管理員")
            st.rerun()
        else:
            st.error("用戶不存在")

def admin_system_settings():
    users = load_users()
    admin_username = st.session_state.get('admin_username', 'admin')
    user_group = users.get(admin_username, {}).get('group', 'free')
    if user_group != 'super_admin':
        st.error("⛔ 只有超級管理員可以修改系統設定")
        return
    
    st.subheader("⚙️ 系統設定")
    st.info("修改設定後，撳「儲存設定」會自動重新整理頁面，新設定即時生效。")
    
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
        currency = st.text_input("貨幣單位", value=config.get("currency", "HKD"))
        admin_password = st.text_input("管理員密碼", value=config.get("admin_password", "z54060437K"), type="password")
        
        st.markdown("#### 🧩 後台模組開關")
        module_user_management = st.checkbox("用戶管理模組", value=config.get("module_user_management", True))
        module_analytics = st.checkbox("數據分析模組", value=config.get("module_analytics", True))
        module_finance = st.checkbox("財務管理模組", value=config.get("module_finance", True))
        module_monitoring = st.checkbox("系統監控模組", value=config.get("module_monitoring", True))
        module_content = st.checkbox("內容管理模組", value=config.get("module_content", True))
        module_automation = st.checkbox("自動化工具模組", value=config.get("module_automation", True))
        module_security = st.checkbox("安全與權限模組", value=config.get("module_security", True))
        module_promo = st.checkbox("優惠碼模組", value=config.get("module_promo", True))
        
        st.markdown("#### 📢 每日免費重心推介")
        enable_daily_free_tip = st.checkbox("啟用每日免費重心推介", value=config.get("enable_daily_free_tip", True))
    
    st.divider()
    if st.button("💾 儲存設定", type="primary"):
        new_config = {
            "enable_registration": enable_registration,
            "enable_payment": enable_payment,
            "enable_admin": enable_admin,
            "currency": currency,
            "free_limit": free_limit,
            "admin_password": admin_password,
            "price_day": price_day,
            "price_month": price_month,
            "price_quarter": price_quarter,
            "verification_expiry": verification_expiry,
            "enable_vip_content": enable_vip_content,
            "module_user_management": module_user_management,
            "module_analytics": module_analytics,
            "module_finance": module_finance,
            "module_monitoring": module_monitoring,
            "module_content": module_content,
            "module_automation": module_automation,
            "module_security": module_security,
            "module_promo": module_promo,
            "enable_daily_free_tip": enable_daily_free_tip,
            "enable_invite_reward": enable_invite_reward,
            "invite_reward_inviter": invite_reward_inviter,
            "invite_reward_invitee": invite_reward_invitee,
        }
        if save_system_config(new_config):
            st.success("✅ 設定已儲存！頁面將會重新整理以套用新設定。")
            import time
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 儲存失敗，請檢查檔案權限。")

# ============================================================
# 後台頁面
# ============================================================
def admin_page():
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔐 後台管理 - 身份驗證")
        st.markdown("請輸入管理員密碼以進入後台")
        admin_pw = st.text_input("管理員密碼", type="password", key="admin_login_pw")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 解鎖後台", type="primary", key="unlock_admin"):
                if admin_pw == CONFIG["admin_password"]:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_username = "admin"
                    log_admin_action("admin", "登入後台")
                    st.success("✅ 密碼正確！")
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
        "👥 用戶管理": admin_user_management if CONFIG.get("module_user_management", True) else lambda: st.info("模組已關閉"),
        "📊 次數管理": admin_manage_predictions,
        "📊 數據分析": admin_analytics if CONFIG.get("module_analytics", True) else lambda: st.info("模組已關閉"),
        "🏇 馬匹排行榜": admin_horse_ranking,
        "👨‍🏫 騎師排行榜": admin_jockey_ranking,
        "👨‍🏫 練馬師排行榜": admin_trainer_ranking,
        "📊 場地/路程分析": admin_course_analysis,
        "📅 每月報告": admin_monthly_report,
        "💰 財務": admin_finance if CONFIG.get("module_finance", True) else lambda: st.info("模組已關閉"),
        "🎟️ 優惠碼": admin_promo_codes if CONFIG.get("module_promo", True) else lambda: st.info("模組已關閉"),
        "📈 預測監控": admin_accuracy_monitor,
        "⏰ 訂閱管理": admin_subscription,
        "📤 付款審核": admin_payment_review,
        "📡 監控": admin_monitoring if CONFIG.get("module_monitoring", True) else lambda: st.info("模組已關閉"),
        "📝 內容": admin_content if CONFIG.get("module_content", True) else lambda: st.info("模組已關閉"),
        "🤖 自動維護": admin_auto_maintenance,
        "🤖 自動化": admin_automation if CONFIG.get("module_automation", True) else lambda: st.info("模組已關閉"),
        "🔐 安全": admin_security if CONFIG.get("module_security", True) else lambda: st.info("模組已關閉"),
    }
    
    base_tabs = ["📊 儀表板", "👥 用戶管理", "📊 次數管理", "📊 數據分析", 
                 "🏇 馬匹排行榜", "👨‍🏫 騎師排行榜", "👨‍🏫 練馬師排行榜", 
                 "📊 場地/路程分析", "📅 每月報告",
                 "💰 財務", "🎟️ 優惠碼", "📈 預測監控", "⏰ 訂閱管理", 
                 "📤 付款審核", "📡 監控", "📝 內容", "🤖 自動維護", 
                 "🤖 自動化", "🔐 安全"]
    
    if is_super_admin:
        tab_names = base_tabs + ["⚙️ 系統設定"]
        tab_functions["⚙️ 系統設定"] = admin_system_settings
    else:
        tab_names = base_tabs
    
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

    content = load_json(CONTENT_FILE)
    announcements = content.get('announcements', [])
    today = datetime.now().date()
    active_anns = []
    for ann in announcements:
        if ann.get('status') != 'active':
            continue
        start = datetime.strptime(ann['start_date'], '%Y-%m-%d').date()
        if start > today:
            continue
        end = ann.get('end_date')
        if end:
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
            if end_date < today:
                continue
        target = ann.get('target', '全部用戶')
        if target != '全部用戶':
            if not st.session_state.get('logged_in', False):
                continue
            user = load_users().get(st.session_state.username, {})
            group = user.get('group', 'free')
            if target == '付費用戶' and group not in ['paid', 'VIP', 'super_admin']:
                continue
            if target == 'VIP' and group not in ['VIP', 'super_admin']:
                continue
            if target == '免費用戶' and group != 'free':
                continue
        active_anns.append(ann)

    for ann in active_anns:
        ann_type = ann.get('type', '一般')
        if ann_type == '緊急':
            st.error(f"🚨 {ann['title']}：{ann['content']}")
        elif ann_type == '重要':
            st.warning(f"⚠️ {ann['title']}：{ann['content']}")
        else:
            st.info(f"💡 {ann['title']}：{ann['content']}")

    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        return

    if CONFIG.get("enable_daily_free_tip", True):
        try:
            df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
            df_sched = standardize_columns_safe(df_sched)
            if 'race_date' in df_sched.columns:
                df_sched['race_date'] = pd.to_datetime(df_sched['race_date'], errors='coerce')
                df_sched = df_sched.dropna(subset=['race_date'])
                today_dt = datetime.now().date()
                day_races = df_sched[df_sched['race_date'].dt.date == today_dt]
                if not day_races.empty:
                    first_race = day_races.sort_values('race_no').iloc[0]
                    race_date_str = first_race['race_date'].strftime('%Y-%m-%d')
                    race_no = int(first_race['race_no'])
                    result, pool = run_prediction(race_date_str, race_no)
                    if result is not None and not result.empty:
                        top1 = result.iloc[0]
                        st.markdown("---")
                        st.markdown("### 🌟 今日免費重心推介")
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #fff8e1, #ffecb3);border-radius:16px;padding:15px 20px;border:2px solid #ffb300;box-shadow:0 2px 8px rgba(255,179,0,0.2);">
                            <div style="display:flex;align-items:center;gap:15px;flex-wrap:wrap;">
                                <span style="font-size:28px;">🏇</span>
                                <div>
                                    <span style="font-size:18px;font-weight:bold;">{top1['馬匹名稱']}</span>
                                    <span style="font-size:14px;color:#555;">（第 {race_no} 場）</span><br>
                                    <span style="font-size:14px;color:#888;">勝率 <b style="color:#2e7d32;">{top1['預測勝率']:.2%}</b>　檔位 {top1['檔位']}</span>
                                </div>
                                <div style="margin-left:auto;">
                                    <span style="background:#ff6f00;color:white;padding:4px 14px;border-radius:20px;font-size:12px;">🎯 每日重心</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("---")
        except:
            pass

    col1, col2, col3 = st.columns([5, 1, 1])
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
            if st.button("🚪 登出", use_container_width=True, key="logout_main"):
                for key in ['logged_in', 'username', 'role', 'usage_count', 'show_history']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    if CONFIG["enable_registration"] and st.session_state.logged_in:
        show_user_dashboard(st.session_state.username)
    elif not CONFIG["enable_registration"]:
        st.info("🔓 目前為公開模式，任何人皆可使用")

    st.markdown("---")
    st.subheader("🧠 模型自我學習 & 表現分析")
    acc = load_accuracy()
    records = acc.get('records', [])
    if records:
        total = len([r for r in records if r.get('is_hit') is not None])
        hit = sum(1 for r in records if r.get('is_hit') is True)
        hit_rate = hit/total if total>0 else 0
        roi = (hit * 400 - total * 100) / (total * 100) if total>0 else 0
        config = load_system_config()
        xgb_w = config.get('xgb_weight', 25)
        cat_w = config.get('cat_weight', 1)
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        col_stat1.metric("📊 總預測", total)
        col_stat2.metric("🎯 命中次數", hit)
        col_stat3.metric("📈 命中率", f"{hit_rate:.2%}")
        col_stat4.metric("💰 ROI (模擬)", f"{roi:.2%}")
        
        if len(records) >= 10:
            recent = records[-10:]
            hit_seq = [1 if r.get('is_hit') is True else 0 for r in recent]
            st.caption("📊 最近 10 場命中情況： " + "".join(["✅" if h else "❌" for h in hit_seq]))
        
        st.caption(f"⚙️ 當前模型融合權重：XGBoost **{xgb_w}** : CatBoost **{cat_w}**")
        
        with st.expander("📊 特徵重要性分析（CatBoost）"):
            try:
                cat_model = CatBoostClassifier()
                cat_model.load_model('hk_catboost_model.cbm')
                importances = cat_model.get_feature_importance()
                feature_names = EXPECTED_FEATURES
                if len(importances) == len(feature_names):
                    df_imp = pd.DataFrame({
                        '特徵': feature_names,
                        '重要性': importances
                    }).sort_values('重要性', ascending=False).head(15)
                    fig = px.bar(df_imp, x='重要性', y='特徵', orientation='h', 
                                title='Top 15 特徵重要性',
                                color='重要性', color_continuous_scale='Blues')
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("特徵數量不匹配")
            except Exception as e:
                st.info(f"無法載入 CatBoost 模型：{e}")
        
        with st.expander("📈 命中率趨勢圖"):
            if records:
                df_records = pd.DataFrame(records)
                if 'date' in df_records.columns and 'is_hit' in df_records.columns:
                    df_records['date'] = pd.to_datetime(df_records['date'])
                    df_records = df_records.dropna(subset=['date', 'is_hit'])
                    if not df_records.empty:
                        daily = df_records.groupby(df_records['date'].dt.date).agg(
                            total=('is_hit', 'count'),
                            hit=('is_hit', lambda x: (x==True).sum())
                        ).reset_index()
                        daily['hit_rate'] = daily['hit'] / daily['total']
                        fig2 = px.line(daily, x='date', y='hit_rate', 
                                       title='每日命中率趨勢',
                                       markers=True)
                        fig2.update_layout(yaxis_tickformat='.0%')
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("未有足夠數據")
                else:
                    st.info("未有日期或命中數據")
            else:
                st.info("暫時未有預測記錄")
    else:
        st.info("暫時未有預測記錄，未能進行自我學習分析。請先執行預測。")

    st.markdown("---")
    st.subheader("🎯 賽事預測控制")
    col_date, col_race, col_btn = st.columns([2, 2, 1])
    with col_date:
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"), key="predict_date_mid")
    with col_race:
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8, key="predict_race_mid")
    with col_btn:
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True, key="predict_btn_mid")

    with st.sidebar:
        st.header("🎯 用戶資訊")
        if CONFIG["enable_registration"] and st.session_state.logged_in:
            st.write(f"👤 用戶：{st.session_state.username}")
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            limit = user_data.get('predictions_limit', CONFIG['free_limit'])
            if limit == -1:
                st.success("♾️ 無限預測次數")
            else:
                used = user_data.get('free_usage', 0)
                remain = max(0, limit - used)
                st.info(f"📊 剩餘免費場次：{remain} 場")
            if st.button("📋 我的預測記錄", key="show_history_btn_side"):
                st.session_state.show_history = not st.session_state.show_history
            if st.button("🚪 登出", key="logout_btn_side"):
                for key in ['logged_in', 'username', 'role', 'usage_count', 'show_history']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            
            st.divider()
            st.caption("💬 聯絡管理員")
            st.markdown("Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**")
            st.markdown("[🔗 點擊連結搵我哋](https://t.me/bryhjdjbrbxibvrjskofndhiebdpaq)")
            
            st.divider()
            st.subheader("📌 導航")
            is_super_admin = user_data.get('group') == 'super_admin'
            pages = ["主頁面", "預測", "賽程", "馬匹查詢", "騎師查詢", "對比", "趨勢", "用戶儀表板", "預測歷史"]
            if is_super_admin:
                pages.append("後台管理")
            selected = st.selectbox("前往", pages, index=0, key="nav_select_side")
            if selected != st.session_state.get('page', '主頁面'):
                st.session_state.page = selected
                st.rerun()

    if CONFIG["enable_registration"] and st.session_state.logged_in and st.session_state.get('show_history', False):
        st.subheader("📋 我的預測記錄")
        show_prediction_history(st.session_state.username)
        st.divider()

    if predict_btn:
        users = load_users()
        user_data = users.get(st.session_state.username, {})
        limit = user_data.get('predictions_limit', CONFIG['free_limit'])
        used = user_data.get('free_usage', 0)
        user_group = user_data.get('group', 'free')
        
        if CONFIG.get("enable_vip_content", True):
            is_vip = user_group in ['VIP', 'super_admin']
        else:
            is_vip = True
        
        if CONFIG["enable_payment"] and limit != -1 and used >= limit:
            show_paywall()
        else:
            date_str = date.strftime('%Y-%m-%d')
            with st.spinner(f"執行預測 {date_str} 第 {race_no} 場..."):
                result, pool = run_prediction(date_str, race_no)
                if result is not None:
                    st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
                    
                    top4 = result.head(4)
                    top1 = top4.iloc[0]
                    
                    st.markdown("---")
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#1a237e,#0d47a1,#1565c0);border-radius:20px;padding:25px 30px;text-align:center;box-shadow:0 8px 32px rgba(21,101,192,0.4);border:2px solid rgba(255,215,0,0.3);position:relative;overflow:hidden;">
                        <div style="position:absolute;top:-30px;right:-30px;font-size:100px;opacity:0.1;">🏆</div>
                        <div style="position:absolute;bottom:-20px;left:-20px;font-size:80px;opacity:0.08;">⭐</div>
                        <span style="font-size:16px;color:#ffd54f;font-weight:bold;letter-spacing:3px;background:rgba(255,215,0,0.15);padding:4px 16px;border-radius:20px;">🏆 獨贏首選</span><br>
                        <span style="font-size:48px;color:#ffffff;font-weight:900;letter-spacing:3px;text-shadow:0 2px 8px rgba(0,0,0,0.3);display:inline-block;margin-top:8px;">{top1['馬匹名稱']}</span><br>
                        <div style="display:flex;justify-content:center;gap:30px;margin-top:10px;flex-wrap:wrap;">
                            <span style="font-size:18px;color:#bbdefb;">檔位 <b style="color:#ffffff;font-size:22px;">{top1['檔位']}</b></span>
                            <span style="font-size:18px;color:#bbdefb;">勝率 <b style="color:#69f0ae;font-size:22px;">{top1['預測勝率']:.2%}</b></span>
                            <span style="font-size:18px;color:#bbdefb;">值博指數 <b style="color:#ffd54f;font-size:22px;">{top1['值博指數']:.4f}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<h3 style='margin-top:25px;margin-bottom:10px;'>🔗 連贏推薦</h3>", unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        <div style="background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-radius:14px;padding:16px 20px;text-align:center;box-shadow:0 4px 12px rgba(13,71,161,0.15);border-left:5px solid #0d47a1;">
                            <span style="font-size:28px;">🏇</span>
                            <h4 style="margin:4px 0 2px 0;color:#0d47a1;">{top4.iloc[0]['馬匹名稱']}</h4>
                            <div style="display:flex;justify-content:center;gap:20px;font-size:14px;color:#555;">
                                <span>檔位 <b>{top4.iloc[0]['檔位']}</b></span>
                                <span>勝率 <b style="color:#2e7d32;">{top4.iloc[0]['預測勝率']:.2%}</b></span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div style="background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-radius:14px;padding:16px 20px;text-align:center;box-shadow:0 4px 12px rgba(13,71,161,0.15);border-left:5px solid #0d47a1;">
                            <span style="font-size:28px;">🏇</span>
                            <h4 style="margin:4px 0 2px 0;color:#0d47a1;">{top4.iloc[1]['馬匹名稱']}</h4>
                            <div style="display:flex;justify-content:center;gap:20px;font-size:14px;color:#555;">
                                <span>檔位 <b>{top4.iloc[1]['檔位']}</b></span>
                                <span>勝率 <b style="color:#2e7d32;">{top4.iloc[1]['預測勝率']:.2%}</b></span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.caption("💡 連贏：揀 2 隻馬，跑出前 2 名（不分順序）即中")
                    
                    if is_vip:
                        st.markdown("<h3 style='margin-top:25px;margin-bottom:10px;'>🥉 三重彩推薦（4 隻複式）</h3>", unsafe_allow_html=True)
                        cols = st.columns(4)
                        colors = ['#fce4ec', '#f3e5f5', '#e8eaf6', '#e0f7fa']
                        for i in range(4):
                            row = top4.iloc[i]
                            with cols[i]:
                                st.markdown(f"""
                                <div style="background:{colors[i]};border-radius:12px;padding:14px 10px;text-align:center;box-shadow:0 3px 10px rgba(0,0,0,0.08);border:1px solid rgba(0,0,0,0.05);">
                                    <span style="font-size:24px;">🏇</span>
                                    <h5 style="margin:2px 0;color:#333;font-size:15px;">{row['馬匹名稱']}</h5>
                                    <div style="font-size:13px;color:#555;">檔位 <b>{row['檔位']}</b><br>勝率 <b style="color:#2e7d32;">{row['預測勝率']:.2%}</b></div>
                                </div>
                                """, unsafe_allow_html=True)
                        st.caption("💡 三重彩：揀 3 隻馬，順序估中冠亞季軍。以上 4 隻馬可做複式三重彩（4 選 3）")
                    else:
                        st.markdown("""
                        <div style="background:linear-gradient(135deg,#fff3e0,#ffe0b2);border-radius:16px;padding:30px 20px;text-align:center;border:2px dashed #ff6f00;margin:10px 0;">
                            <span style="font-size:48px;">🔒</span>
                            <h3 style="color:#e65100;margin:10px 0;">三重彩推薦</h3>
                            <p style="color:#bf360c;font-size:16px;">此內容僅限 <b>VIP 會員</b> 查看</p>
                            <p style="color:#888;font-size:14px;">升級 VIP 即可解鎖三重彩、四重彩等獨家彩池推薦</p>
                            <div style="margin-top:15px;"><span style="background:#ff6f00;color:white;padding:8px 24px;border-radius:20px;font-weight:bold;font-size:14px;">💎 立即升級 VIP</span></div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if is_vip:
                        st.markdown("<h3 style='margin-top:25px;margin-bottom:10px;'>🏅 四重彩推薦（4 隻複式）</h3>", unsafe_allow_html=True)
                        cols = st.columns(4)
                        colors2 = ['#e8f5e9', '#e0f2f1', '#fff3e0', '#fbe9e7']
                        for i in range(4):
                            row = top4.iloc[i]
                            with cols[i]:
                                st.markdown(f"""
                                <div style="background:{colors2[i]};border-radius:12px;padding:14px 10px;text-align:center;box-shadow:0 3px 10px rgba(0,0,0,0.08);border:1px solid rgba(0,0,0,0.05);">
                                    <span style="font-size:24px;">🏇</span>
                                    <h5 style="margin:2px 0;color:#333;font-size:15px;">{row['馬匹名稱']}</h5>
                                    <div style="font-size:13px;color:#555;">檔位 <b>{row['檔位']}</b><br>勝率 <b style="color:#2e7d32;">{row['預測勝率']:.2%}</b></div>
                                </div>
                                """, unsafe_allow_html=True)
                        st.caption("💡 四重彩：揀 4 隻馬，順序估中冠亞季殿軍。以上 4 隻馬可做複式四重彩（4 選 4）")
                    else:
                        st.markdown("""
                        <div style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:16px;padding:20px 20px;text-align:center;border:2px dashed #2e7d32;margin:10px 0;">
                            <span style="font-size:36px;">🔒</span>
                            <h4 style="color:#1b5e20;margin:5px 0;">四重彩推薦</h4>
                            <p style="color:#555;font-size:14px;">升級 VIP 即可解鎖四重彩推薦</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.divider()
                    st.markdown("""
                    <h3 style='margin-bottom:10px;'>📋 總結投注建議</h3>
                    <div style="background:linear-gradient(135deg,#f1f8e9,#dcedc8);border-radius:16px;padding:20px 24px;border:2px solid #2e7d32;box-shadow:0 4px 16px rgba(46,125,50,0.15);">
                    """, unsafe_allow_html=True)
                    
                    if is_vip:
                        st.markdown(f"""
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 30px;font-size:15px;">
                            <div>🏆 <b>獨贏</b>：<span style="color:#1a237e;font-weight:bold;">{top4.iloc[0]['馬匹名稱']}</span></div>
                            <div>🔗 <b>連贏</b>：<span style="color:#0d47a1;font-weight:bold;">{top4.iloc[0]['馬匹名稱']} + {top4.iloc[1]['馬匹名稱']}</span></div>
                            <div style="grid-column:span 2;">🥉 <b>三重彩</b>：<span style="color:#4a148c;font-weight:bold;">{top4.iloc[0]['馬匹名稱']}、{top4.iloc[1]['馬匹名稱']}、{top4.iloc[2]['馬匹名稱']}、{top4.iloc[3]['馬匹名稱']}</span>（複式 4 選 3）</div>
                            <div style="grid-column:span 2;">🏅 <b>四重彩</b>：<span style="color:#1b5e20;font-weight:bold;">{top4.iloc[0]['馬匹名稱']}、{top4.iloc[1]['馬匹名稱']}、{top4.iloc[2]['馬匹名稱']}、{top4.iloc[3]['馬匹名稱']}</span>（複式 4 選 4）</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="font-size:15px;">
                            <div>🏆 <b>獨贏</b>：<span style="color:#1a237e;font-weight:bold;">{top4.iloc[0]['馬匹名稱']}</span></div>
                            <div>🔗 <b>連贏</b>：<span style="color:#0d47a1;font-weight:bold;">{top4.iloc[0]['馬匹名稱']} + {top4.iloc[1]['馬匹名稱']}</span></div>
                            <div style="margin-top:12px;padding:12px;background:#fff3e0;border-radius:10px;text-align:center;border:1px dashed #ff6f00;">
                                <span style="font-size:20px;">🔒</span>
                                <span style="color:#e65100;font-weight:bold;"> 三重彩及四重彩推薦僅限 VIP 會員查看</span>
                                <br><span style="font-size:13px;color:#888;">升級 VIP 即可解鎖完整投注建議</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.subheader("🎯 彩池推薦（詳細）")
                    st.text(pool)

                    if CONFIG["enable_registration"] and st.session_state.logged_in:
                        winner_name = top4.iloc[0]['馬匹名稱']
                        prob = top4.iloc[0]['預測勝率']
                        record_prediction(st.session_state.username, date_str, race_no, winner_name, prob)
                        users = load_users()
                        if st.session_state.username in users:
                            users[st.session_state.username]['free_usage'] = users[st.session_state.username].get('free_usage', 0) + 1
                            users[st.session_state.username]['total_usage'] = users[st.session_state.username].get('total_usage', 0) + 1
                            save_users(users)
                        st.session_state.usage_count += 1
                        st.info("📝 預測已記錄到你的歷史")

    st.markdown("---")
    st.subheader("💳 付款功能")
    
    if st.session_state.get('logged_in'):
        show_paywall()
    else:
        st.info("請先登入以使用付款功能")
        if st.button("前往登入"):
            st.session_state.page_mode = "login"
            st.rerun()

    st.subheader("📅 今日賽程")
    try:
        df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df_sched = standardize_columns_safe(df_sched)
        if 'race_date' in df_sched.columns:
            df_sched['race_date'] = pd.to_datetime(df_sched['race_date'], errors='coerce')
            df_sched = df_sched.dropna(subset=['race_date'])
            today = datetime.now().date()
            day_races = df_sched[df_sched['race_date'].dt.date == today]
            if day_races.empty:
                st.info("今日沒有賽事")
            else:
                for course in day_races['race_course'].unique():
                    races = day_races[day_races['race_course'] == course]['race_no'].unique()
                    st.write(f"🏟️ **{course}**：第 {', '.join(map(str, sorted(races)))} 場")
        else:
            st.info("今日沒有賽事")
    except:
        st.info("今日沒有賽事")

    st.divider()
    st.warning("⚠️ **免責聲明**：本系統提供之預測僅供參考，不構成投注建議。賽馬活動涉及風險，用戶應量力而為，本系統不對任何投注損失負責。用戶必須年滿18歲。使用本服務即表示同意以上條款。")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col_f2:
        st.caption("🔐 數據來源：HKJC | 系統版本：v14.0-用戶體驗版")
    with col_f3:
        st.caption("💬 Telegram：@bryhjdjbrbxibvrjskofndhiebdpaq")

if __name__ == '__main__':
    main()
