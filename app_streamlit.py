#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整版 (v18.4)
包含抽獎、商城、管理員贈送、額外抽獎次數管理
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import json
import re
import string
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier
import plotly.express as px
import plotly.graph_objects as go
import random
from PIL import Image

st.set_page_config(page_title="🏇 賽馬預測系統", page_icon="🐎", layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

st.markdown("""
<style>
    div[data-testid="stToolbar"] { display: none !important; }
    .stAppDeployButton { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    button[kind="share"] { display: none !important; }
    a[href*="streamlit.io"] { display: none !important; }
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
    "verification_expiry": 5, "enable_vip_content": True,
    "enable_invite_reward": True, "invite_reward_inviter": 1, "invite_reward_invitee": 1,
    "xgb_weight": 25, "cat_weight": 1,
    "daily_virtual_coin": 1000, "virtual_coin_enabled": True,
}

def load_system_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config: config[key] = value
            return config
        except: return DEFAULT_CONFIG.copy()
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_CONFIG.copy()

def save_system_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except: return False

CONFIG = load_system_config()

def load_json(file_path, default=None):
    if default is None: default = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return default
    return default

def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

USER_DATA_FILE = 'users.json'
FINANCE_FILE = 'finance.json'
PROMO_FILE = 'promo_codes.json'
LOG_FILE = 'admin_log.json'
ACCURACY_FILE = 'accuracy.json'
CONTENT_FILE = 'content.json'
AUTOMATION_FILE = 'automation.json'
PAYMENT_PROOFS_FILE = 'payment_proofs.json'
ACTIVITY_LOG_FILE = 'user_activity_log.json'
LOTTERY_CONFIG_FILE = 'lottery_config.json'
LOTTERY_RECORDS_FILE = 'lottery_records.json'
SHOP_CONFIG_FILE = 'shop_config.json'
SHOP_PURCHASES_FILE = 'shop_purchases.json'

if not os.path.exists('payment_proofs'): os.makedirs('payment_proofs')
if 'payment_requests' not in st.session_state: st.session_state.payment_requests = {"requests": []}

# ============================================================
# 用戶活動日誌
# ============================================================
def log_user_activity(username, action, details=""):
    log = load_json(ACTIVITY_LOG_FILE)
    if 'logs' not in log: log['logs'] = []
    log['logs'].append({'timestamp': datetime.now().isoformat(), 'username': username, 'action': action, 'details': details})
    if len(log['logs']) > 10000: log['logs'] = log['logs'][-10000:]
    save_json(ACTIVITY_LOG_FILE, log)

def get_user_activity_logs(username=None, days=30, action=None):
    log = load_json(ACTIVITY_LOG_FILE)
    logs = log.get('logs', [])
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for entry in logs:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            if dt < cutoff: continue
            if username and entry.get('username') != username: continue
            if action and entry.get('action') != action: continue
            filtered.append(entry)
        except: continue
    return filtered

# ============================================================
# 🎰 每日抽獎系統
# ============================================================
DEFAULT_LOTTERY_CONFIG = {
    "enabled": True, "draws_per_day": 1, "allow_admin_gift": True,
    "prizes": [
        {"id": 1, "name": "💰 100 虛擬幣", "type": "virtual_coin", "value": 100, "weight": 30, "stock": -1, "icon": "💰"},
        {"id": 2, "name": "💰 500 虛擬幣", "type": "virtual_coin", "value": 500, "weight": 15, "stock": -1, "icon": "💰"},
        {"id": 3, "name": "💰 1000 虛擬幣", "type": "virtual_coin", "value": 1000, "weight": 5, "stock": -1, "icon": "💎"},
        {"id": 4, "name": "👑 VIP 1 天", "type": "vip_days", "value": 1, "weight": 10, "stock": -1, "icon": "👑"},
        {"id": 5, "name": "🎯 免費預測 3 次", "type": "free_predictions", "value": 3, "weight": 20, "stock": -1, "icon": "🎯"},
        {"id": 6, "name": "🎟️ 20% 折扣優惠碼", "type": "promo_code", "value": "auto", "weight": 10, "stock": -1, "icon": "🎟️",
         "discount_type": "percentage", "discount_value": 20, "valid_days": 7},
        {"id": 7, "name": "😢 謝謝參與", "type": "nothing", "value": 0, "weight": 10, "stock": -1, "icon": "😢"}
    ]
}

def load_lottery_config():
    if os.path.exists(LOTTERY_CONFIG_FILE):
        try:
            with open(LOTTERY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_LOTTERY_CONFIG.items():
                if key not in config: config[key] = value
            return config
        except: return DEFAULT_LOTTERY_CONFIG.copy()
    else:
        with open(LOTTERY_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_LOTTERY_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_LOTTERY_CONFIG.copy()

def save_lottery_config(config):
    try:
        with open(LOTTERY_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except: return False

def load_lottery_records():
    if os.path.exists(LOTTERY_RECORDS_FILE):
        try:
            with open(LOTTERY_RECORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {"records": []}
    return {"records": []}

def save_lottery_records(data):
    try:
        with open(LOTTERY_RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

def get_user_draws_today(username):
    records = load_lottery_records()
    today = datetime.now().strftime('%Y-%m-%d')
    return sum(1 for r in records.get('records', []) if r.get('username') == username and r.get('draw_date') == today)

def user_can_draw_today(username):
    config = load_lottery_config()
    if not config.get('enabled', True): return False, "抽獎活動已關閉"
    max_draws = config.get('draws_per_day', 1)
    users = load_users()
    extra = users.get(username, {}).get('extra_lottery_draws', 0)
    max_draws += extra
    drawn = get_user_draws_today(username)
    if drawn >= max_draws: return False, f"今日已抽 {drawn}/{max_draws} 次"
    return True, f"今日可抽 {max_draws - drawn} 次"

def generate_promo_code_for_prize():
    promos = load_promos()
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    while code in promos:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return code

def apply_prize_to_user(username, prize):
    users = load_users()
    if username not in users: return False, "用戶不存在"
    prize_type = prize.get('type', 'nothing')
    prize_value = prize.get('value', 0)
    message = ""
    if prize_type == 'virtual_coin':
        users[username]['virtual_balance'] = users[username].get('virtual_balance', 0) + prize_value
        message = f"獲得 {prize_value} 虛擬幣！"
    elif prize_type == 'vip_days':
        current_expiry = users[username].get('expiry_date')
        if current_expiry:
            try:
                base_date = pd.to_datetime(current_expiry)
                if base_date < datetime.now(): base_date = datetime.now()
            except: base_date = datetime.now()
        else: base_date = datetime.now()
        new_expiry = base_date + timedelta(days=prize_value)
        users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
        users[username]['group'] = 'VIP'
        users[username]['is_paid'] = True
        users[username]['predictions_limit'] = -1
        message = f"獲得 VIP {prize_value} 天！"
    elif prize_type == 'free_predictions':
        if users[username].get('predictions_limit', 0) != -1:
            users[username]['predictions_limit'] = users[username].get('predictions_limit', 0) + prize_value
        message = f"獲得 {prize_value} 次免費預測！"
    elif prize_type == 'promo_code':
        discount_type = prize.get('discount_type', 'percentage')
        discount_value = prize.get('discount_value', 20)
        valid_days = prize.get('valid_days', 7)
        code = generate_promo_code_for_prize()
        promos = load_promos()
        expiry = (datetime.now() + timedelta(days=valid_days)).isoformat()
        promos[code] = {"used": False, "expiry": expiry, "created_at": datetime.now().isoformat(), "discount_type": discount_type, "discount_value": discount_value, "used_by": None, "source": f"抽獎獲得（{username}）"}
        save_promos(promos)
        if discount_type == 'percentage': discount_text = f"{discount_value}% 折扣"
        elif discount_type == 'fixed': discount_text = f"減 ${discount_value}"
        else: discount_text = "全免"
        message = f"🎟️ 獲得優惠碼：`{code}`（{discount_text}，{valid_days} 天內有效）"
    elif prize_type == 'custom': message = f"獲得：{prize_value}"
    elif prize_type == 'nothing': message = "謝謝參與！"
    save_users(users)
    return True, message

def draw_lottery(username):
    config = load_lottery_config()
    if not config.get('enabled', True): return False, "抽獎活動已關閉", None
    can_draw, msg = user_can_draw_today(username)
    if not can_draw: return False, msg, None
    prizes = config.get('prizes', [])
    available = [p for p in prizes if p.get('stock', -1) == -1 or p.get('stock', 0) > 0]
    if not available: return False, "所有獎品已派完", None
    weights = [p.get('weight', 1) for p in available]
    total = sum(weights)
    if total == 0: return False, "抽獎設定錯誤", None
    rand = random.uniform(0, total)
    cumulative = 0
    chosen = available[-1]
    for i, p in enumerate(available):
        cumulative += weights[i]
        if rand <= cumulative: chosen = p; break
    if chosen.get('stock', -1) > 0:
        for p in config['prizes']:
            if p.get('id') == chosen.get('id'):
                p['stock'] = p.get('stock', 1) - 1
                break
        save_lottery_config(config)
    success, message = apply_prize_to_user(username, chosen)
    records = load_lottery_records()
    records['records'].append({"username": username, "draw_date": datetime.now().strftime('%Y-%m-%d'), "draw_time": datetime.now().isoformat(), "prize_id": chosen.get('id'), "prize_name": chosen.get('name'), "prize_type": chosen.get('type'), "prize_value": chosen.get('value'), "source": "抽獎"})
    if len(records['records']) > 5000: records['records'] = records['records'][-5000:]
    save_lottery_records(records)
    log_user_activity(username, 'lottery', f"抽中 {chosen.get('name')}")
    return True, message, chosen

def admin_gift_prize(admin_username, target_user, prize):
    config = load_lottery_config()
    if not config.get('allow_admin_gift', True): return False, "管理員贈送功能已關閉"
    success, message = apply_prize_to_user(target_user, prize)
    if not success: return False, message
    records = load_lottery_records()
    records['records'].append({"username": target_user, "draw_date": datetime.now().strftime('%Y-%m-%d'), "draw_time": datetime.now().isoformat(), "prize_id": prize.get('id'), "prize_name": prize.get('name'), "prize_type": prize.get('type'), "prize_value": prize.get('value'), "source": f"管理員 {admin_username} 贈送"})
    save_lottery_records(records)
    log_admin_action(admin_username, f"贈送 {prize.get('name')} 給 {target_user}")
    return True, f"✅ 已贈送 {prize.get('name')} 給 {target_user}"

def show_lottery_interface(username):
    if not username: st.info("請先登入"); return
    config = load_lottery_config()
    if not config.get('enabled', True): st.warning("🎰 抽獎活動暫時關閉"); return
    st.subheader("🎰 每日抽獎")
    can_draw, msg = user_can_draw_today(username)
    max_draws = config.get('draws_per_day', 1)
    users = load_users()
    extra = users.get(username, {}).get('extra_lottery_draws', 0)
    max_draws += extra
    drawn = get_user_draws_today(username)
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.metric("今日已抽", f"{drawn}/{max_draws}")
    col_info2.metric("狀態", "✅ 可抽獎" if can_draw else "⏰ 已抽完")
    col_info3.metric("獎品數量", len(config.get('prizes', [])))
    if can_draw:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""<div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #ffd700, #ff8c00); border-radius: 20px; color: white;"><div style="font-size: 60px;">🎁</div><div style="font-size: 24px; font-weight: bold; margin-top: 10px;">試吓你嘅運氣！</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🎰 立即抽獎", type="primary", use_container_width=True, key="btn_draw_lottery"):
                success, message, prize = draw_lottery(username)
                if success:
                    st.balloons()
                    st.success(f"🎉 {message}")
                    if prize:
                        st.markdown(f"""<div style="text-align: center; padding: 20px; background: #f0fdf4; border-radius: 12px; border: 2px solid #22c55e;"><div style="font-size: 48px;">{prize.get('icon', '🎁')}</div><div style="font-size: 20px; font-weight: bold; color: #15803d; margin-top: 10px;">{prize.get('name', '')}</div></div>""", unsafe_allow_html=True)
                    st.rerun()
                else: st.warning(message)
    else: st.info(f"⏰ {msg}，聽日再嚟啦！")
    st.divider()
    st.subheader("🎁 獎品一覽")
    prizes = config.get('prizes', [])
    if prizes:
        cols = st.columns(4)
        for idx, p in enumerate(prizes):
            with cols[idx % 4]:
                stock = p.get('stock', -1)
                stock_text = "無限" if stock == -1 else f"剩 {stock} 份"
                st.markdown(f"""<div style="padding: 12px; background: #f8fafc; border-radius: 10px; text-align: center; margin-bottom: 10px;"><div style="font-size: 30px;">{p.get('icon', '🎁')}</div><div style="font-size: 13px; font-weight: bold; margin-top: 5px;">{p.get('name', '')}</div><div style="font-size: 11px; color: #64748b; margin-top: 3px;">{stock_text}</div></div>""", unsafe_allow_html=True)
    st.divider()
    st.subheader("📋 我嘅抽獎記錄")
    records = load_lottery_records()
    user_records = [r for r in records.get('records', []) if r.get('username') == username]
    if user_records:
        df_records = pd.DataFrame(user_records[-20:][::-1])
        display_cols = ['draw_date', 'prize_name', 'source']
        available_cols = [c for c in display_cols if c in df_records.columns]
        st.dataframe(df_records[available_cols], use_container_width=True, hide_index=True)
    else: st.info("📭 尚未抽過獎")

# ============================================================
# 🛍️ 虛擬商城系統
# ============================================================
DEFAULT_SHOP_CONFIG = {
    "enabled": True,
    "items": [
        {"id": 1, "name": "🎯 額外預測 1 次", "type": "predictions", "value": 1, "price": 500, "stock": -1, "icon": "🎯", "desc": "增加 1 次預測機會"},
        {"id": 2, "name": "👑 VIP 1 天體驗", "type": "vip_days", "value": 1, "price": 5000, "stock": -1, "icon": "👑", "desc": "VIP 會員 1 天"},
        {"id": 3, "name": "👑 VIP 3 天體驗", "type": "vip_days", "value": 3, "price": 12000, "stock": -1, "icon": "👑", "desc": "VIP 會員 3 天"},
        {"id": 4, "name": "🎰 額外抽獎 1 次", "type": "lottery_draws", "value": 1, "price": 1000, "stock": -1, "icon": "🎰", "desc": "增加 1 次抽獎機會"},
        {"id": 5, "name": "💎 「鑽石會員」稱號", "type": "title", "value": "💎 鑽石會員", "price": 10000, "stock": -1, "icon": "💎", "desc": "個人中心顯示特殊稱號"},
        {"id": 6, "name": "🎁 神秘禮盒", "type": "mystery_box", "value": 0, "price": 3000, "stock": -1, "icon": "🎁", "desc": "隨機獲得獎品"}
    ]
}

def load_shop_config():
    if os.path.exists(SHOP_CONFIG_FILE):
        try:
            with open(SHOP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_SHOP_CONFIG.items():
                if key not in config: config[key] = value
            return config
        except: return DEFAULT_SHOP_CONFIG.copy()
    else:
        with open(SHOP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_SHOP_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_SHOP_CONFIG.copy()

def save_shop_config(config):
    try:
        with open(SHOP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except: return False

def load_shop_purchases():
    if os.path.exists(SHOP_PURCHASES_FILE):
        try:
            with open(SHOP_PURCHASES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {"purchases": []}
    return {"purchases": []}

def save_shop_purchases(data):
    try:
        with open(SHOP_PURCHASES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

def get_user_real_balance_shop(username):
    users = load_users()
    if username not in users: return 0
    base_balance = users[username].get('virtual_balance', 0)
    purchases = load_shop_purchases()
    user_purchases = [p for p in purchases.get('purchases', []) if p.get('username') == username]
    total_spent = sum(p.get('price', 0) for p in user_purchases)
    return base_balance - total_spent

def purchase_item(username, item):
    item_price = item.get('price', 0)
    current_balance = get_user_real_balance_shop(username)
    if current_balance < item_price:
        return False, f"❌ 餘額不足（餘額：${current_balance:,.0f}，需要：${item_price:,.0f}）"
    purchases = load_shop_purchases()
    purchases['purchases'].append({"username": username, "item_id": item.get('id'), "item_name": item.get('name'), "item_type": item.get('type'), "item_value": item.get('value'), "price": item_price, "purchased_at": datetime.now().isoformat()})
    if not save_shop_purchases(purchases): return False, "❌ 購買記錄儲存失敗"
    users = load_users()
    if username not in users: return False, "❌ 用戶不存在"
    item_type = item.get('type')
    item_value = item.get('value')
    if item_type == 'predictions':
        if users[username].get('predictions_limit', 0) != -1:
            users[username]['predictions_limit'] = users[username].get('predictions_limit', 0) + item_value
        msg = f"✅ 獲得 {item_value} 次預測機會！"
    elif item_type == 'vip_days':
        current_expiry = users[username].get('expiry_date')
        if current_expiry:
            try:
                base_date = pd.to_datetime(current_expiry)
                if base_date < datetime.now(): base_date = datetime.now()
            except: base_date = datetime.now()
        else: base_date = datetime.now()
        new_expiry = base_date + timedelta(days=item_value)
        users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
        users[username]['group'] = 'VIP'
        users[username]['is_paid'] = True
        users[username]['predictions_limit'] = -1
        msg = f"✅ VIP 延長至 {new_expiry.strftime('%Y-%m-%d')}！"
    elif item_type == 'lottery_draws':
        extra = users[username].get('extra_lottery_draws', 0)
        users[username]['extra_lottery_draws'] = extra + item_value
        msg = f"✅ 獲得 {item_value} 次額外抽獎！"
    elif item_type == 'title':
        if 'titles' not in users[username]: users[username]['titles'] = []
        if item_value not in users[username]['titles']: users[username]['titles'].append(item_value)
        users[username]['current_title'] = item_value
        msg = f"✅ 已購買稱號：{item_value}"
    elif item_type == 'mystery_box':
        rewards = [("💰 100 虛擬幣", 100, 'virtual_coin'), ("💰 500 虛擬幣", 500, 'virtual_coin'), ("🎯 免費預測 3 次", 3, 'predictions'), ("👑 VIP 1 天", 1, 'vip_days')]
        reward_name, reward_value, reward_type = random.choice(rewards)
        if reward_type == 'virtual_coin':
            users[username]['virtual_balance'] = users[username].get('virtual_balance', 0) + reward_value
            purchases['purchases'].append({"username": username, "item_id": -1, "item_name": f"神秘禮盒：{reward_name}", "item_type": "reward", "item_value": reward_value, "price": -reward_value, "purchased_at": datetime.now().isoformat()})
            save_shop_purchases(purchases)
        elif reward_type == 'predictions':
            if users[username].get('predictions_limit', 0) != -1:
                users[username]['predictions_limit'] = users[username].get('predictions_limit', 0) + reward_value
        elif reward_type == 'vip_days':
            current_expiry = users[username].get('expiry_date')
            if current_expiry:
                try:
                    base_date = pd.to_datetime(current_expiry)
                    if base_date < datetime.now(): base_date = datetime.now()
                except: base_date = datetime.now()
            else: base_date = datetime.now()
            new_expiry = base_date + timedelta(days=reward_value)
            users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
            users[username]['group'] = 'VIP'
            users[username]['is_paid'] = True
            users[username]['predictions_limit'] = -1
        msg = f"🎁 神秘禮盒開出：{reward_name}！"
    else: msg = f"✅ 已購買"
    save_users(users)
    log_user_activity(username, 'purchase', f"購買 {item.get('name')} - ${item_price}")
    return True, msg

def show_shop_interface(username):
    if not username: st.info("請先登入"); return
    config = load_shop_config()
    if not config.get('enabled', True): st.warning("🛍️ 商城暫時關閉"); return
    st.subheader("🛍️ 虛擬商城")
    balance = get_user_real_balance_shop(username)
    col1, col2, col3 = st.columns(3)
    col1.metric("💎 你的餘額", f"${balance:,.0f}")
    col2.metric("📦 已購買", len([p for p in load_shop_purchases().get('purchases', []) if p.get('username') == username]))
    col3.metric("🎁 可購買物品", len(config.get('items', [])))
    st.divider()
    items = config.get('items', [])
    if not items: st.info("商城暫無物品"); return
    st.subheader("🎁 商品列表")
    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            st.markdown(f"""<div style="padding: 15px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center; margin-bottom: 10px;"><div style="font-size: 40px;">{item.get('icon', '🎁')}</div><div style="font-size: 16px; font-weight: bold; margin-top: 8px;">{item.get('name', '')}</div><div style="font-size: 12px; color: #64748b; margin-top: 5px;">{item.get('desc', '')}</div><div style="font-size: 20px; font-weight: bold; color: #f59e0b; margin-top: 10px;">${item.get('price', 0):,.0f} 幣</div></div>""", unsafe_allow_html=True)
            if st.button(f"🛒 購買", key=f"buy_{item.get('id')}", use_container_width=True):
                success, msg = purchase_item(username, item)
                if success:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else: st.error(msg)
    st.divider()
    st.subheader("📋 我的購買記錄")
    purchases = load_shop_purchases()
    user_purchases = [p for p in purchases.get('purchases', []) if p.get('username') == username]
    if user_purchases:
        df_purchases = pd.DataFrame(user_purchases[-20:][::-1])
        display_cols = ['purchased_at', 'item_name', 'price']
        available_cols = [c for c in display_cols if c in df_purchases.columns]
        df_display = df_purchases[available_cols].copy()
        df_display.columns = ['時間', '物品', '價格'][:len(df_display.columns)]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else: st.info("📭 尚未購買任何物品")

# ============================================================
# 用戶等級/勳章系統
# ============================================================
def get_level_info(exp):
    levels = [(0, "🥉 銅牌會員"), (100, "🥈 銀牌會員"), (500, "🥇 金牌會員"), (1500, "💎 鑽石會員"), (5000, "👑 傳說會員")]
    current_level = levels[0][1]
    next_level_exp = None
    for threshold, level_name in levels:
        if exp >= threshold: current_level = level_name
        else: next_level_exp = threshold; break
    return current_level, next_level_exp

def check_badges(username, hit_rate=None):
    users = load_users()
    if username not in users: return
    user = users[username]
    history = user.get('history', [])
    badges = user.get('badges', [])
    total_predictions = len(history)
    hits = sum(1 for h in history if h.get('is_hit') is True)
    hit_rate = hits / total_predictions if total_predictions > 0 else 0
    consecutive_hits = 0; max_consecutive = 0
    for h in history:
        if h.get('is_hit') is True:
            consecutive_hits += 1
            max_consecutive = max(max_consecutive, consecutive_hits)
        else: consecutive_hits = 0
    badge_conditions = {
        "🏆 首勝": (total_predictions >= 1 and hits >= 1, ""),
        "🔥 三連勝": (max_consecutive >= 3, ""),
        "⚡ 五連勝": (max_consecutive >= 5, ""),
        "💯 百場預測": (total_predictions >= 100, ""),
        "🎯 命中大師": (total_predictions >= 20 and hit_rate >= 0.5, ""),
        "👥 社交達人": (user.get('invite_count', 0) >= 5, ""),
        "💰 付費會員": (user.get('is_paid', False) or user.get('group') == 'VIP', ""),
        "🏇 馬匹專家": (len(set(h.get('horse') for h in history)) >= 5, ""),
        "🎰 抽獎達人": (len([r for r in load_lottery_records().get('records', []) if r.get('username') == username]) >= 10, ""),
        "🛍️ 購物達人": (len([p for p in load_shop_purchases().get('purchases', []) if p.get('username') == username]) >= 5, ""),
    }
    new_badges = []
    for badge_name, (condition, description) in badge_conditions.items():
        if condition and badge_name not in badges: new_badges.append(badge_name)
    if new_badges:
        badges.extend(new_badges)
        user['badges'] = badges
        save_users(users)
    return badges

def update_user_exp(username, is_hit=False):
    users = load_users()
    if username not in users: return
    user = users[username]
    exp = user.get('exp', 0) + 10
    if is_hit: exp += 20
    user['exp'] = exp
    save_users(users)
    check_badges(username)

def claim_daily_virtual_coin(username):
    if not CONFIG.get("virtual_coin_enabled", True): return 0, "虛擬幣功能已關閉"
    users = load_users()
    if username not in users: return 0, "用戶不存在"
    user = users[username]
    today = datetime.now().strftime('%Y-%m-%d')
    if user.get('last_claim_date', '') == today: return 0, "今日已領取"
    daily_amount = CONFIG.get("daily_virtual_coin", 1000)
    user['virtual_balance'] = user.get('virtual_balance', 0) + daily_amount
    user['last_claim_date'] = today
    save_users(users)
    return daily_amount, f"已領取 ${daily_amount} 虛擬幣"

# ============================================================
# 用戶系統
# ============================================================
def load_users():
    users = load_json(USER_DATA_FILE)
    if not users or "admin" not in users:
        users = {"admin": {"username": "admin", "password": CONFIG["admin_password"], "is_paid": False, "paid_date": None, "expiry_date": None, "free_usage": 0, "total_usage": 0, "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "note": "系統超級管理員", "group": "super_admin", "phone": "", "plan": None, "predictions_limit": -1, "history": [], "terms_agreed": datetime.now().isoformat(), "invite_code": "ADMIN001", "invited_by": None, "invite_rewards": 0, "invite_count": 0, "level": "👑 超級管理員", "exp": 0, "badges": [], "virtual_balance": 10000, "last_claim_date": "", "extra_lottery_draws": 0, "titles": [], "current_title": None}}
        save_users(users)
    else:
        if "admin" in users:
            users["admin"]["group"] = "super_admin"
            users["admin"]["predictions_limit"] = -1
            if "level" not in users["admin"]: users["admin"]["level"] = "👑 超級管理員"; users["admin"]["exp"] = 0; users["admin"]["badges"] = []
            if "virtual_balance" not in users["admin"]: users["admin"]["virtual_balance"] = 10000
            if "last_claim_date" not in users["admin"]: users["admin"]["last_claim_date"] = ""
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
            if 'invite_code' not in u: u['invite_code'] = uid.upper() + str(random.randint(100, 999))
            if 'invited_by' not in u: u['invited_by'] = None
            if 'invite_rewards' not in u: u['invite_rewards'] = 0
            if 'invite_count' not in u: u['invite_count'] = 0
            if 'predictions_limit' not in u:
                u['predictions_limit'] = -1 if u.get('group') in ['super_admin', 'VIP', 'paid'] else CONFIG["free_limit"]
            if 'level' not in u: u['level'] = '🥉 銅牌會員'
            if 'exp' not in u: u['exp'] = 0
            if 'badges' not in u: u['badges'] = []
            if 'virtual_balance' not in u: u['virtual_balance'] = 1000
            if 'last_claim_date' not in u: u['last_claim_date'] = ''
            if 'extra_lottery_draws' not in u: u['extra_lottery_draws'] = 0
            if 'titles' not in u: u['titles'] = []
            if 'current_title' not in u: u['current_title'] = None
        save_users(users)
    return users

def save_users(users):
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except: return False

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password: return users[username]
    return None

def log_admin_action(admin, action):
    logs = load_logs()
    if 'logs' not in logs: logs['logs'] = []
    logs['logs'].append({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'admin': admin, 'action': action})
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
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)).upper()

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
    if 'proof_records' not in proof: proof['proof_records'] = []
    new_id = len(proof['proof_records']) + 1
    new_request = {"id": new_id, "username": username, "plan": plan, "plan_name": get_plan_name(plan), "final_price": final_price, "discount_desc": discount_desc, "promo_code": promo_code_used, "submitted_at": datetime.now().isoformat(), "status": "pending"}
    proof['proof_records'].append(new_request)
    save_payment_proofs(proof)
    if promo_code_used:
        promos = load_promos()
        if promo_code_used in promos:
            promos[promo_code_used]['used'] = True
            promos[promo_code_used]['used_by'] = username
            promos[promo_code_used]['used_at'] = datetime.now().isoformat()
            save_promos(promos)
    log_user_activity(username, 'payment_submit', f"{get_plan_name(plan)} 金額${final_price}")
    return True, "申請已提交"

def get_all_pending_requests():
    proof = load_payment_proofs()
    return [{"username": req.get('username', ''), "request": req} for req in proof.get('proof_records', []) if req.get('status') == 'pending']

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
                log_admin_action(admin_username, f"批准付款 {username}（{plan}）")
                return True, f"已批准，到期日 {expiry}"
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
            log_admin_action(admin_username, f"拒絕 {username} 的付款")
            return True, "已拒絕"
    return False, "找不到該申請"

def show_paywall():
    st.subheader("💳 選擇你嘅方案")
    plan_options = {"day": f"☀️ 日費  ${CONFIG['price_day']}   (1天)", "month": f"📆 月費  ${CONFIG['price_month']}  (30天)", "quarter": f"📅 季費  ${CONFIG['price_quarter']} (90天)"}
    if st.session_state.get('payment_just_submitted', False):
        st.success("✅ 付款申請已成功提交！")
        st.info("📩 提交後請 Telegram 通知管理員")
        st.markdown("💬 Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**")
        if 'payment_detail' in st.session_state: st.write(st.session_state['payment_detail'])
        if st.button("返回主頁"):
            for key in ['payment_just_submitted', 'payment_detail']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
        st.stop()
    if 'applied_promo' not in st.session_state: st.session_state.applied_promo = None
    if 'applied_discount' not in st.session_state: st.session_state.applied_discount = 0
    if 'applied_final_price' not in st.session_state: st.session_state.applied_final_price = None
    with st.form(key="payment_form"):
        plan_choice = st.radio("請選擇付費方案：", options=list(plan_options.keys()), format_func=lambda x: plan_options[x], horizontal=True, key="plan_radio")
        original_price = get_plan_price(plan_choice) if plan_choice else 0
        if plan_choice: st.info(f"💰 原價：${original_price}")
        promo_input = st.text_input("優惠碼（如有）", key="promo_input")
        col_promo1, col_promo2 = st.columns([1, 3])
        with col_promo1: apply_promo_btn = st.form_submit_button("🎁 套用優惠碼")
        with col_promo2:
            if st.session_state.applied_promo: st.success(f"✅ 已套用：{st.session_state.applied_promo}")
        if apply_promo_btn and promo_input:
            promos = load_promos()
            code = promo_input.strip().upper()
            promo_data = promos.get(code)
            if not promo_data: st.error(f"❌ 優惠碼「{code}」不存在")
            elif promo_data.get('used', False): st.error(f"❌ 優惠碼「{code}」已被使用")
            else:
                expiry = promo_data.get('expiry')
                if expiry:
                    try:
                        if datetime.fromisoformat(expiry) < datetime.now():
                            st.error(f"❌ 優惠碼已過期"); st.stop()
                    except: pass
                discount_type = promo_data.get('discount_type', 'percentage')
                discount_value = promo_data.get('discount_value', 0)
                final_price = original_price
                if discount_type == 'percentage': final_price = original_price * (1 - discount_value / 100)
                elif discount_type == 'fixed': final_price = max(0, original_price - discount_value)
                elif discount_type == 'free': final_price = 0
                final_price = round(final_price, 2)
                st.session_state.applied_promo = code
                st.session_state.applied_discount = original_price - final_price
                st.session_state.applied_final_price = final_price
                st.success(f"✅ 優惠碼「{code}」已套用！")
                st.rerun()
        elif apply_promo_btn: st.warning("請輸入優惠碼")
        if st.session_state.applied_promo and st.session_state.applied_final_price is not None:
            st.markdown(f"""<div style="background: #f0fdf4; padding: 15px; border-radius: 10px; border: 2px solid #22c55e; margin: 10px 0;"><div style="font-size: 14px; color: #15803d;">💰 折扣後價格</div><div style="font-size: 24px; font-weight: bold; color: #15803d;">${st.session_state.applied_final_price:.2f}</div><div style="font-size: 12px; color: #64748b; margin-top: 5px;">已節省 ${st.session_state.applied_discount:.2f}</div></div>""", unsafe_allow_html=True)
        st.divider()
        st.markdown("**📤 FPS 轉數快 `12345678`（SHTSN SYSTEM）**")
        submitted = st.form_submit_button("📩 提交付款申請", type="primary")
        if submitted:
            if not plan_choice: st.error("❌ 請選擇方案"); return
            if not st.session_state.get('logged_in'): st.error("❌ 請先登入"); return
            username = st.session_state.username
            final_price = st.session_state.applied_final_price if st.session_state.applied_final_price is not None else original_price
            success, msg = submit_payment_request(username, plan_choice, final_price, "", st.session_state.applied_promo)
            if success:
                st.session_state.applied_promo = None
                st.session_state.applied_discount = 0
                st.session_state.applied_final_price = None
                st.session_state['payment_just_submitted'] = True
                st.session_state['payment_detail'] = f"方案：{get_plan_name(plan_choice)}，金額：${final_price}"
                st.rerun()

# ============================================================
# AI 自我學習
# ============================================================
def update_accuracy_with_results():
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records: return 0, "沒有預測記錄"
    try:
        results_df = pd.read_csv('race_results_clean.csv', encoding='utf-8-sig')
        required = ['race_date', 'race_no', 'horse_name', 'finish_position']
        for col in required:
            if col not in results_df.columns: return 0, f"缺少欄位：{col}"
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
        results_df = results_df.dropna(subset=['race_date'])
        updated = 0
        for rec in records:
            if rec.get('actual_result') is not None: continue
            date_str = rec.get('date'); race_no = rec.get('race'); horse = rec.get('horse')
            if not date_str or not race_no or not horse: continue
            mask = (results_df['race_date'].dt.strftime('%Y-%m-%d') == date_str) & (results_df['race_no'] == race_no) & (results_df['horse_name'] == horse)
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
                                    h['is_hit'] = True; break
                            save_users(users)
                        update_user_exp(username, is_hit=True)
                    check_badges(username)
        if updated > 0: save_accuracy(acc)
        return updated, f"成功比對 {updated} 條"
    except Exception as e: return 0, f"比對失敗：{str(e)}"

def adjust_model_weights():
    acc = load_accuracy()
    records = acc.get('records', [])
    total = len([r for r in records if r.get('is_hit') is not None])
    hit = sum(1 for r in records if r.get('is_hit') is True)
    hit_rate = hit / total if total > 0 else 0
    config = load_system_config()
    current_xgb = config.get('xgb_weight', 25)
    current_cat = config.get('cat_weight', 1)
    if hit_rate >= 0.6: new_xgb, new_cat = min(40, current_xgb + 3), max(1, current_cat - 1)
    elif hit_rate >= 0.5: new_xgb, new_cat = min(35, current_xgb + 1), max(1, current_cat)
    elif hit_rate >= 0.4: new_xgb, new_cat = max(15, current_xgb - 2), min(10, current_cat + 2)
    elif hit_rate >= 0.3: new_xgb, new_cat = max(10, current_xgb - 5), min(15, current_cat + 5)
    else: new_xgb, new_cat = max(5, current_xgb - 8), min(20, current_cat + 8)
    config['xgb_weight'] = max(1, min(50, new_xgb))
    config['cat_weight'] = max(1, min(30, new_cat))
    config['last_weight_update'] = datetime.now().isoformat()
    config['last_hit_rate'] = hit_rate
    save_system_config(config)
    return {'xgb_weight': config['xgb_weight'], 'cat_weight': config['cat_weight'], 'hit_rate': hit_rate, 'total': total, 'hit': hit}

def update_ai_accuracy():
    ai_file = "ai_predictions.json"
    results_file = "race_results_clean.csv"
    if not os.path.exists(ai_file): return 0, "未有 AI 預測記錄"
    if not os.path.exists(results_file): return 0, "未有賽果數據"
    with open(ai_file, 'r', encoding='utf-8') as f: ai_data = json.load(f)
    results_df = pd.read_csv(results_file, encoding='utf-8-sig')
    if not all(col in results_df.columns for col in ['race_date', 'race_no', 'horse_name', 'finish_position']): return 0, "賽果檔案欄位不正確"
    results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
    results_df['race_date_str'] = results_df['race_date'].dt.strftime('%Y-%m-%d')
    hit_count = 0; total_count = 0
    for key, pred in ai_data.items():
        date_str = pred.get('date'); race_no = pred.get('race'); top_horse = pred.get('top_horse')
        if not date_str or not race_no or not top_horse: continue
        matched = results_df[(results_df['race_date_str'] == date_str) & (results_df['race_no'] == race_no) & (results_df['horse_name'] == top_horse)]
        total_count += 1
        if not matched.empty:
            finish_pos = matched.iloc[0].get('finish_position')
            if pd.notna(finish_pos) and finish_pos == 1: hit_count += 1; pred['is_hit'] = True
            else: pred['is_hit'] = False
        else: pred['is_hit'] = None
    with open(ai_file, 'w', encoding='utf-8') as f: json.dump(ai_data, f, ensure_ascii=False, indent=2)
    hit_rate = hit_count / total_count if total_count > 0 else 0
    return hit_count, f"命中 {hit_count}/{total_count} ({hit_rate:.1%})"

# ============================================================
# 特徵工程
# ============================================================
def standardize_columns_safe(df):
    rename_map = {'騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance', '場地': 'going', '檔位': 'draw', '評分': 'rtg', '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_no', '馬匹id': 'horse_id', 'horse': 'horse_id', '場次': 'race_no', '馬場': 'race_course', '實際負磅': 'act_wt', '名次': 'finish_position', '最終名次': 'finish_position', '馬名': 'horse_name', '賠率': 'win_odds', '獨贏賠率': 'win_odds'}
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    if '比賽日期' in df.columns and 'race_date' not in df.columns: df.rename(columns={'比賽日期': 'race_date'}, inplace=True)
    return df

def generate_pool_recommendations(df):
    if df.empty: return "⚠️ 無數據"
    horse_names = df['horse_name'].tolist()
    probs = df['預測勝率'].tolist()
    def combo_score(indices):
        score = 1.0
        for i in indices: score *= probs[i]
        return score / len(indices)
    rec = ""
    if len(horse_names) >= 1:
        rec += "【獨贏】\n"
        rec += f"  {horse_names[0]}（{probs[0]:.1%}）\n"
    rec += "\n【位置】\n"
    for i in range(min(4, len(horse_names))): rec += f"  {horse_names[i]}（{probs[i]:.1%}）\n"
    rec += "\n【連贏】\n"
    pairs = []
    for i in range(min(len(horse_names), 4)):
        for j in range(i+1, min(len(horse_names), 5)): pairs.append((combo_score([i, j]), i, j))
    pairs.sort(reverse=True)
    for _, i, j in pairs[:3]: rec += f"  {horse_names[i]} + {horse_names[j]}\n"
    rec += "\n【位置Q】\n"
    q_pairs = []
    for i in range(min(len(horse_names), 5)):
        for j in range(i+1, min(len(horse_names), 7)):
            if j < len(horse_names): q_pairs.append((combo_score([i, j]), i, j))
    q_pairs.sort(reverse=True)
    for _, i, j in q_pairs[:6]: rec += f"  {horse_names[i]} + {horse_names[j]}\n"
    rec += "\n【三重彩 / 單T】\n"
    tierce = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                if i != j and i != k and j != k: tierce.append((combo_score([i, j, k]), i, j, k))
    tierce.sort(reverse=True)
    for _, i, j, k in tierce[:3]: rec += f"  {horse_names[i]} > {horse_names[j]} > {horse_names[k]}\n"
    rec += "\n【四重彩】\n"
    quartet = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                for l in range(min(len(horse_names), 7)):
                    if len(set([i, j, k, l])) == 4: quartet.append((combo_score([i, j, k, l]), i, j, k, l))
    quartet.sort(reverse=True)
    for _, i, j, k, l in quartet[:3]: rec += f"  {horse_names[i]} > {horse_names[j]} > {horse_names[k]} > {horse_names[l]}\n"
    return rec

def run_prediction(date_str, race_no):
    if not os.path.exists("racecard_uploaded.csv"):
        st.error("❌ 找不到 racecard_uploaded.csv"); return None, None
    try: df = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig')
    except Exception as e: st.error(f"❌ 讀取失敗：{e}"); return None, None
    rename_map = {'馬名': 'horse_name', '檔位': 'draw', '場次': 'race_no', '比賽日期': 'race_date', '騎師': 'jockey', '練馬師': 'trainer', '負磅': 'weight', '馬號': 'horse_no', '賠率': 'win_odds', '獨贏賠率': 'win_odds', 'Odds': 'win_odds'}
    for old, new in rename_map.items():
        if old in df.columns and old != new: df.rename(columns={old: new}, inplace=True)
    if 'race_date' not in df.columns: st.error("❌ 缺少 '比賽日期'"); return None, None
    df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
    df = df.dropna(subset=['race_date'])
    df['race_date_str'] = df['race_date'].dt.strftime('%Y-%m-%d')
    available_dates = sorted(df['race_date_str'].unique())
    if date_str not in available_dates: st.warning(f"⚠️ 改用 {available_dates[-1]}"); date_str = available_dates[-1]
    df_date = df[df['race_date_str'] == date_str]
    if race_no not in df_date['race_no'].unique():
        available_races = sorted(df_date['race_no'].unique())
        if available_races: st.info(f"🔄 改用第 {available_races[0]} 場"); race_no = available_races[0]
        else: st.error("❌ 無場次"); return None, None
    filtered = df_date[df_date['race_no'] == race_no].copy()
    st.success(f"✅ 成功載入 {date_str} 第 {race_no} 場")
    odds_col = None
    for col in ['win_odds', '賠率', '獨贏賠率', 'odds', 'WinOdds', 'Odds']:
        if col in filtered.columns: odds_col = col; break
    if odds_col is not None: win_odds = pd.to_numeric(filtered[odds_col], errors='coerce').fillna(4.0)
    else: st.warning("⚠️ 冇賠率欄位，用預設 4.0"); win_odds = pd.Series([4.0] * len(filtered), index=filtered.index)
    win_odds = win_odds.replace(0, 4.0)
    inv_odds = 1 / win_odds
    final_pred = inv_odds / inv_odds.sum()
    result_df = filtered[['horse_name', 'draw', 'weight', 'jockey', 'trainer']].copy()
    result_df['預測勝率'] = final_pred
    result_df['值博指數'] = result_df['預測勝率'] * 10
    result_df['信心指數'] = result_df['預測勝率'].apply(lambda x: '⭐⭐⭐ 高' if x > 0.2 else '⭐⭐ 中' if x > 0.1 else '⭐ 低')
    result_df = result_df.sort_values('預測勝率', ascending=False)
    result_df['horse_name'] = result_df['horse_name'].fillna('未知').astype(str)
    ai_file = "ai_predictions.json"
    ai_data = {}
    if os.path.exists(ai_file):
        try:
            with open(ai_file, 'r', encoding='utf-8') as f: ai_data = json.load(f)
        except: ai_data = {}
    key = f"{date_str}_{race_no}"
    ai_data[key] = {"date": date_str, "race": int(race_no), "top_horse": str(result_df.iloc[0]['horse_name']), "top_prob": float(result_df.iloc[0]['預測勝率']), "all_horses": result_df['horse_name'].tolist(), "predicted_at": datetime.now().isoformat()}
    try:
        with open(ai_file, 'w', encoding='utf-8') as f: json.dump(ai_data, f, ensure_ascii=False, indent=2)
        st.success(f"✅ AI 預測已儲存（共 {len(ai_data)} 筆）")
        if st.session_state.get('username'): log_user_activity(st.session_state.username, 'predict', f"{date_str} 第{race_no}場")
    except Exception as e: st.error(f"❌ 儲存失敗：{e}")
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
        filtered_lines = []; skip = False
        for line in lines:
            if '【三重彩' in line or '【四重彩' in line: skip = True; continue
            if skip and line.strip() == '': skip = False; continue
            if not skip: filtered_lines.append(line)
        pool_text = '\n'.join(filtered_lines)
        pool_text += "\n\n🔒 三重彩 / 四重彩 為 VIP 專屬內容"
    else: pool_text = full_pool_text
    return result_df, pool_text

def get_user_stats(username):
    users = load_users()
    if username not in users: return {'total_predictions': 0}
    return {'total_predictions': len(users[username].get('history', []))}

def show_user_dashboard(username):
    if not username: return
    stats = get_user_stats(username)
    users = load_users()
    user_data = users.get(username, {})
    group = user_data.get('group', 'free')
    is_paid = user_data.get('is_paid', False)
    level = user_data.get('level', '🥉 銅牌會員')
    exp = user_data.get('exp', 0)
    badges = user_data.get('badges', [])
    next_level_exp = get_level_info(exp)[1]
    virtual_balance = user_data.get('virtual_balance', 0)
    current_title = user_data.get('current_title', None)
    if group == 'super_admin': level_display = "👑 超級管理員"
    elif group == 'VIP': level_display = "👑 VIP"
    elif is_paid: level_display = "💎 付費用戶"
    else: level_display = "🆓 免費用戶"
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👤 用戶", username)
    col2.metric("🏷️ 級別", level_display)
    col3.metric("📊 總預測次數", stats['total_predictions'])
    limit = user_data.get('predictions_limit', CONFIG['free_limit'])
    if limit == -1: col4.metric("📊 剩餘場次", "♾️ 無限")
    else: col4.metric("📊 剩餘場次", max(0, limit - user_data.get('free_usage', 0)))
    col5.metric("💰 虛擬幣", f"${virtual_balance:,.0f}")
    if current_title: st.markdown(f"### {current_title}")
    st.markdown("---")
    st.subheader("🏅 用戶等級 & 勳章")
    col_level1, col_level2, col_level3 = st.columns(3)
    with col_level1: st.metric("🏅 當前等級", level)
    with col_level2:
        if next_level_exp:
            progress = min(100, int((exp / next_level_exp) * 100))
            st.metric("📊 經驗值", f"{exp} / {next_level_exp}")
            st.progress(progress / 100)
        else: st.metric("📊 經驗值", f"{exp}")
    with col_level3: st.metric("🎖️ 勳章數量", len(badges))
    if badges:
        st.write("🏅 已獲得勳章：")
        badge_cols = st.columns(4)
        for idx, badge in enumerate(badges):
            with badge_cols[idx % 4]: st.markdown(f"**{badge}**")
    st.markdown("---")
    if CONFIG.get("enable_invite_reward", True):
        st.subheader("🎁 邀請獎勵")
        col_inv1, col_inv2, col_inv3 = st.columns(3)
        with col_inv1: st.caption(f"邀請碼：**{user_data.get('invite_code', '')}**")
        with col_inv2: st.caption(f"已邀請：**{user_data.get('invite_count', 0)}** 位")
        with col_inv3: st.caption(f"獲得獎勵：**{user_data.get('invite_rewards', 0)}** 次")

def login_page():
    st.title("🔐 登入 / 註冊")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 登入", use_container_width=True): st.session_state.page_mode = "login"
    with col2:
        if st.button("📝 註冊", use_container_width=True): st.session_state.page_mode = "register"
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
                else: st.error("❌ 用戶名稱或密碼錯誤")
    else:
        st.subheader("📝 註冊新帳號")
        with st.form("register_form"):
            new_user = st.text_input("用戶名稱（最少 3 個字）", key="reg_user")
            phone = st.text_input("手機號碼（可選）", key="reg_phone")
            new_pass = st.text_input("密碼", type="password", key="reg_pass")
            new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
            if CONFIG.get("enable_invite_reward", True): invite_code_input = st.text_input("邀請碼（如有）", key="reg_invite_code")
            else: invite_code_input = None
            col1, col2 = st.columns([3, 1])
            with col1: verify_code_input = st.text_input("驗證碼", key="reg_verify", max_chars=6)
            with col2:
                if st.form_submit_button("📨 獲取驗證碼", type="secondary"):
                    code = generate_verification_code()
                    st.session_state['reg_verify_code'] = code
                    st.session_state['reg_verify_expiry'] = datetime.now() + timedelta(minutes=CONFIG.get('verification_expiry', 5))
                    st.info(f"📧 驗證碼：**{code}**")
            agree_terms = st.checkbox("✅ 我同意服務條款", key="agree_terms")
            submitted = st.form_submit_button("註冊")
            if submitted:
                if len(new_user) < 3: st.error("❌ 用戶名稱至少 3 個字")
                elif new_pass != new_pass2: st.error("❌ 密碼不一致")
                elif len(new_pass) < 4: st.error("❌ 密碼至少 4 個字")
                elif 'reg_verify_code' not in st.session_state or verify_code_input != st.session_state['reg_verify_code'] or datetime.now() > st.session_state.get('reg_verify_expiry', datetime.now()): st.error("❌ 驗證碼無效")
                elif not agree_terms: st.error("❌ 請先同意條款")
                else:
                    users = load_users()
                    if new_user in users: st.error("❌ 用戶名稱已被使用")
                    else:
                        invited_by = None
                        if CONFIG.get("enable_invite_reward", True) and invite_code_input:
                            for uid, u in users.items():
                                if u.get('invite_code') == invite_code_input: invited_by = uid; break
                        new_user_data = {'password': new_pass, 'phone': phone, 'is_paid': False, 'paid_date': None, 'expiry_date': None, 'free_usage': 0, 'total_usage': 0, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'note': '', 'group': 'free', 'plan': None, 'predictions_limit': CONFIG["free_limit"], 'history': [], 'terms_agreed': datetime.now().isoformat(), 'invite_code': new_user.upper() + str(random.randint(100, 999)), 'invited_by': invited_by, 'invite_rewards': 0, 'invite_count': 0, 'level': '🥉 銅牌會員', 'exp': 0, 'badges': [], 'virtual_balance': CONFIG.get('daily_virtual_coin', 1000), 'last_claim_date': '', 'extra_lottery_draws': 0, 'titles': [], 'current_title': None}
                        users[new_user] = new_user_data
                        save_users(users)
                        if invited_by:
                            inviter = users.get(invited_by)
                            if inviter:
                                if inviter['predictions_limit'] != -1: inviter['predictions_limit'] += CONFIG.get("invite_reward_inviter", 1)
                                inviter['invite_count'] = inviter.get('invite_count', 0) + 1
                                save_users(users)
                        st.success("✅ 註冊成功！")
                        st.session_state.page_mode = "login"
                        st.rerun()

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
    except: pass
    return [], []

def display_race_calendar():
    dates, courses = get_future_races()
    if not dates: st.info("📭 暫時未有未來賽事資料"); return
    next_date = dates[0]
    next_course = courses[0] if courses else "賽馬"
    today = datetime.now().date()
    delta = (next_date - today).days
    if delta > 0: time_str = f"⏳ 仲有 **{delta} 天**"
    elif delta == 0: time_str = f"⏳ 今日開跑！"
    else: time_str = "⏳ 已過期"
    st.markdown(f"""<div style="background: linear-gradient(135deg, #1a237e, #0d47a1); border-radius: 12px; padding: 15px 20px; color: white; margin-bottom: 15px;"><div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;"><div><span style="font-size: 20px;">🏇 下一場賽事</span><br><span style="font-size: 16px; opacity: 0.9;">{next_course}　📅 {next_date.strftime('%Y年%m月%d日')}</span></div><div style="font-size: 22px; font-weight: bold; background: rgba(255,255,255,0.15); padding: 8px 20px; border-radius: 30px;">{time_str}</div></div></div>""", unsafe_allow_html=True)
# ============================================================
# 後台功能
# ============================================================
def admin_dashboard():
    st.subheader("📊 系統儀表板")
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
    col6.metric("⏳ 待審核", pending_payments)
    st.divider()
    st.subheader("⚠️ 待辦事項")
    col_w1, col_w2, col_w3 = st.columns(3)
    with col_w1:
        if pending_payments > 0:
            st.warning(f"⏳ 有 {pending_payments} 筆付款待審核")
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
            st.warning(f"⚠️ 即將到期：{', '.join(vip_expiring)}")
        else:
            st.success("✅ 沒有即將到期 VIP")
    with col_w3:
        files_missing = [f for f in ['users.json', 'system_config.json', 'accuracy.json'] if not os.path.exists(f)]
        if files_missing:
            st.error(f"❌ 缺少：{', '.join(files_missing)}")
        else:
            st.success("✅ 系統檔案正常")

def admin_auto_maintenance():
    st.subheader("🤖 自動維護")
    if st.button("🚀 執行全部維護任務", type="primary", use_container_width=True, key="btn_full_maintenance"):
        results = []
        updated, msg = update_accuracy_with_results()
        results.append(f"🔄 比對賽果：{msg}")
        try:
            weight_result = adjust_model_weights()
            results.append(f"⚖️ 調整權重：XGB={weight_result['xgb_weight']}, Cat={weight_result['cat_weight']}")
        except Exception as e:
            results.append(f"⚖️ 調整權重：失敗 - {str(e)}")
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
        st.success("✅ 自動維護完成！")
        for r in results:
            st.write(r)
    st.divider()
    st.subheader("⚡ 單獨執行")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔄 比對賽果", use_container_width=True, key="btn_compare"):
            updated, msg = update_accuracy_with_results()
            st.success(f"✅ {msg}")
            st.rerun()
    with col2:
        if st.button("⚖️ 調整權重", use_container_width=True, key="btn_adjust_weights"):
            result = adjust_model_weights()
            st.success(f"✅ XGB={result['xgb_weight']}, Cat={result['cat_weight']}")
            st.rerun()
    with col3:
        if st.button("⏰ 終止過期會員", use_container_width=True, key="btn_expire"):
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
                st.success(f"✅ 已降級 {len(expired)} 個")
            else:
                st.info("✅ 沒有過期會員")
            st.rerun()
    with col4:
        if st.button("🎯 更新 AI 命中率", use_container_width=True, key="btn_update_ai"):
            hit_count, msg = update_ai_accuracy()
            st.success(f"✅ {msg}")
            st.rerun()

def admin_user_management():
    st.subheader("👥 用戶管理")
    user_file = "users.json"
    if not os.path.exists(user_file):
        st.error("❌ users.json 不存在！")
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

    # ========== 新增用戶 ==========
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
                        "last_claim_date": '',
                        "extra_lottery_draws": 0, "titles": [], "current_title": None
                    }
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    st.success(f"✅ 用戶 {new_username} 已建立！")
                    st.rerun()

    st.divider()

    # ========== 刪除用戶 ==========
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
                    st.success(f"✅ 已刪除")
                    st.rerun()

    st.divider()

    # ========== 查看用戶視角 ==========
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
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👤 用戶", selected_user)
            col2.metric("🏷️ 級別", user_data.get('group', 'free').upper())
            col3.metric("📊 總預測次數", len(user_data.get('history', [])))
            limit = user_data.get('predictions_limit', CONFIG.get('free_limit', 2))
            col4.metric("📊 剩餘場次", "♾️ 無限" if limit == -1 else max(0, limit - user_data.get('free_usage', 0)))
            history = user_data.get('history', [])
            if history:
                st.dataframe(pd.DataFrame(history[-20:][::-1]), use_container_width=True)
            else:
                st.info("呢個用戶暫時冇任何預測記錄")

    st.divider()

    # ========== 編輯用戶 ==========
    with st.expander("✏️ 編輯用戶", expanded=False):
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
                    group_options = ['free', 'paid', 'VIP', 'super_admin']
                    current_group = user.get('group', 'free')
                    if current_group not in group_options:
                        group_options.append(current_group)
                    new_group = st.selectbox("群組", group_options,
                                            index=group_options.index(current_group),
                                            key="edit_group")
                    new_is_paid = st.checkbox("付費狀態", value=user.get('is_paid', False), key="edit_is_paid")
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
                    new_password = st.text_input("新密碼（留空 = 不變）", type="password", key="edit_password")
                with col_edit2:
                    level_options = ["🥉 銅牌會員", "🥈 銀牌會員", "🥇 金牌會員", "💎 鑽石會員", "👑 傳說會員", "👑 超級管理員"]
                    current_level = user.get('level', '🥉 銅牌會員')
                    if current_level not in level_options:
                        level_options.append(current_level)
                    new_level = st.selectbox("🏅 等級", level_options,
                                            index=level_options.index(current_level) if current_level in level_options else 0,
                                            key="edit_level")
                    new_exp = st.number_input("📊 經驗值", min_value=0, value=user.get('exp', 0), step=10, key="edit_exp")
                    current_limit = user.get('predictions_limit', CONFIG.get('free_limit', 2))
                    new_limit = st.number_input("預測次數上限（-1 = 無限）", min_value=-1, value=int(current_limit), step=1, key="edit_limit")
                    # 🔥 額外抽獎次數
                    current_extra_draws = user.get('extra_lottery_draws', 0)
                    new_extra_draws = st.number_input("🎰 額外抽獎次數", min_value=0, value=int(current_extra_draws), step=1, key="edit_extra_draws")
                    all_badges = ["🏆 首勝", "🔥 三連勝", "⚡ 五連勝", "💯 百場預測", "🎯 命中大師", "👥 社交達人", "💰 付費會員", "🏇 馬匹專家", "🎰 抽獎達人", "🛍️ 購物達人"]
                    current_badges = user.get('badges', [])
                    new_badges = st.multiselect("🎖️ 勳章", all_badges,
                                                default=[b for b in current_badges if b in all_badges],
                                                key="edit_badges")

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

                if st.button("🔄 重置虛擬幣為 $1000", key="reset_coin"):
                    users[username]['virtual_balance'] = 1000
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    st.success("✅ 已重置為 $1000")
                    st.rerun()

                note = st.text_area("備註", value=user.get('note', ''), key="edit_note")

                if st.button("💾 儲存變更", key="save_user_changes", type="primary"):
                    users[username]['group'] = new_group
                    users[username]['is_paid'] = new_is_paid
                    users[username]['note'] = note
                    users[username]['level'] = new_level
                    users[username]['exp'] = new_exp
                    users[username]['badges'] = new_badges
                    users[username]['predictions_limit'] = new_limit
                    users[username]['extra_lottery_draws'] = new_extra_draws
                    if new_password:
                        users[username]['password'] = new_password
                    try:
                        users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        users[username]['expiry_date'] = str(new_expiry)
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    st.success("✅ 已更新用戶資料！")
                    st.rerun()
        else:
            st.info("暫無用戶可編輯")

    st.divider()

    # ========== 🎰 管理抽獎次數（獨立區塊） ==========
    st.subheader("🎰 管理抽獎次數")
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except:
        users = {}
    if users:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            draw_target_user = st.selectbox("選擇用戶", list(users.keys()), key="draw_target_user")
        with col_d2:
            current_extra = users.get(draw_target_user, {}).get('extra_lottery_draws', 0)
            st.metric("目前額外抽獎次數", current_extra)

        col_op1, col_op2, col_op3 = st.columns(3)
        with col_op1:
            add_draws = st.number_input("增加次數", min_value=1, value=1, step=1, key="add_draws")
            if st.button("➕ 增加", use_container_width=True, key="btn_add_draws"):
                if draw_target_user in users:
                    users[draw_target_user]['extra_lottery_draws'] = current_extra + add_draws
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    log_admin_action(st.session_state.get('admin_username', 'admin'), f"為 {draw_target_user} 增加 {add_draws} 次抽獎")
                    st.success(f"✅ 已為 {draw_target_user} 增加 {add_draws} 次抽獎（總計：{current_extra + add_draws}）")
                    st.rerun()
        with col_op2:
            reduce_draws = st.number_input("減少次數", min_value=1, value=1, step=1, key="reduce_draws")
            if st.button("➖ 減少", use_container_width=True, key="btn_reduce_draws"):
                if draw_target_user in users:
                    new_val = max(0, current_extra - reduce_draws)
                    users[draw_target_user]['extra_lottery_draws'] = new_val
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    log_admin_action(st.session_state.get('admin_username', 'admin'), f"為 {draw_target_user} 減少 {reduce_draws} 次抽獎")
                    st.success(f"✅ 已為 {draw_target_user} 減少 {reduce_draws} 次抽獎（總計：{new_val}）")
                    st.rerun()
        with col_op3:
            set_draws = st.number_input("設定為指定次數", min_value=0, value=int(current_extra), step=1, key="set_draws")
            if st.button("✅ 設定", use_container_width=True, key="btn_set_draws"):
                if draw_target_user in users:
                    users[draw_target_user]['extra_lottery_draws'] = set_draws
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    log_admin_action(st.session_state.get('admin_username', 'admin'), f"將 {draw_target_user} 抽獎次數設為 {set_draws}")
                    st.success(f"✅ 已將 {draw_target_user} 抽獎次數設為 {set_draws}")
                    st.rerun()
    else:
        st.info("暫無用戶")

    st.divider()

    # ========== 🎁 管理員贈送虛擬幣 ==========
    st.subheader("🎁 管理員贈送虛擬幣")
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except:
        users = {}
    if users:
        with st.form(key="admin_gift_coin_form"):
            col_gift1, col_gift2, col_gift3 = st.columns([2, 1, 1])
            with col_gift1:
                gift_target_user = st.selectbox("選擇用戶", list(users.keys()), key="gift_coin_user")
            with col_gift2:
                gift_coin_amount = st.number_input("金額", min_value=1, value=1000, step=100, key="gift_coin_amount")
            with col_gift3:
                submit_gift_coin = st.form_submit_button("🎁 贈送", type="primary")
            if submit_gift_coin:
                if gift_target_user in users:
                    current_bal = users[gift_target_user].get('virtual_balance', 0)
                    users[gift_target_user]['virtual_balance'] = current_bal + gift_coin_amount
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(users, f, ensure_ascii=False, indent=2)
                    log_admin_action(st.session_state.get('admin_username', 'admin'), f"贈送 ${gift_coin_amount} 虛擬幣給 {gift_target_user}")
                    st.success(f"✅ 已贈送 ${gift_coin_amount:,.0f} 給 {gift_target_user}（新餘額：${current_bal + gift_coin_amount:,.0f}）")
                    st.rerun()
                else:
                    st.error("❌ 用戶不存在")
    else:
        st.info("暫無用戶")

    st.divider()
    st.subheader("📥 數據匯出")
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            data = f.read()
        st.download_button("📥 下載 users.json", data=data,
            file_name="users.json", mime="application/json", key="download_users_json")
    except Exception as e:
        st.error(f"讀取失敗：{e}")

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
        col1.metric("用戶", selected_user)
        col2.metric("目前剩餘次數", current_limit - current_usage if current_limit != -1 else "無限")
        col3.metric("已使用次數", current_usage)
        st.divider()
        action = st.radio("選擇操作", ["增加次數", "減少次數", "設定為指定次數"], horizontal=True, key="predictions_action")
        if action == "增加次數":
            add_amount = st.number_input("增加次數", min_value=1, step=1, value=1, key="add_predictions")
            if st.button("✅ 增加", type="primary", key="confirm_add_predictions"):
                if current_limit == -1:
                    st.warning("⚠️ 已是無限次數")
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
                    st.error("❌ 不能低於 0")
                else:
                    users[selected_user]['predictions_limit'] = current_limit - reduce_amount
                    save_users(users)
                    st.success(f"✅ 已減少 {reduce_amount} 次")
                    st.rerun()
        elif action == "設定為指定次數":
            set_amount = st.number_input("設定為指定次數（-1 = 無限）", min_value=-1, step=1,
                                         value=current_limit if current_limit != -1 else 10, key="set_predictions")
            if st.button("✅ 設定", type="primary", key="confirm_set_predictions"):
                users[selected_user]['predictions_limit'] = set_amount
                save_users(users)
                st.success(f"✅ 已設定為 {'無限' if set_amount == -1 else set_amount}")
                st.rerun()

def admin_analytics():
    st.subheader("📊 數據分析")
    users = load_users()
    col1, col2, col3 = st.columns(3)
    col1.metric("總用戶", len(users))
    col2.metric("付費用戶", sum(1 for u in users.values() if u.get('is_paid', False)))
    col3.metric("VIP", sum(1 for u in users.values() if u.get('group') == 'VIP'))

def admin_horse_ranking():
    st.subheader("🏇 馬匹勝率排行榜")
    acc = load_accuracy()
    records = acc.get('records', [])
    valid_records = [r for r in records if r.get('is_hit') is not None]
    if not valid_records:
        st.info("暫時未有足夠數據")
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
        st.info("暫時未有足夠數據")
        return
    df_horse = pd.DataFrame(horse_list).sort_values('命中率', ascending=False).reset_index(drop=True)
    st.dataframe(df_horse.head(15), use_container_width=True)

def admin_jockey_ranking(): st.subheader("👨‍🏫 騎師勝率排行榜"); st.info("暫時未有足夠數據")
def admin_trainer_ranking(): st.subheader("👨‍🏫 練馬師勝率排行榜"); st.info("暫時未有足夠數據")
def admin_course_analysis(): st.subheader("📊 場地/路程勝率分析"); st.info("暫時未有足夠數據")
def admin_monthly_report(): st.subheader("📅 每月命中率報告"); st.info("暫時未有足夠數據")

def admin_finance():
    st.subheader("💰 財務管理")
    finance = load_finance()
    col1, col2, col3 = st.columns(3)
    col1.metric("總收入", f"${finance.get('total_income', 0):.2f}")
    col2.metric("本月收入", f"${finance.get('monthly_income', 0):.2f}")
    col3.metric("今年收入", f"${finance.get('yearly_income', 0):.2f}")

def admin_promo_codes():
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    total = len(promos)
    used = sum(1 for p in promos.values() if p.get('used', False))
    col_stat1.metric("📊 總優惠碼", total)
    col_stat2.metric("✅ 已使用", used)
    col_stat3.metric("🎁 可使用", total - used)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.write("### 📋 現有優惠碼")
        if promos:
            display_data = []
            for code, data in promos.items():
                expiry = data.get('expiry', '')
                try:
                    expiry_str = datetime.fromisoformat(expiry).strftime('%Y-%m-%d')
                    is_expired = datetime.fromisoformat(expiry) < datetime.now()
                except:
                    expiry_str = expiry
                    is_expired = False
                discount_type = data.get('discount_type', 'percentage')
                discount_value = data.get('discount_value', 0)
                if discount_type == 'percentage': discount_text = f"{discount_value}%"
                elif discount_type == 'fixed': discount_text = f"減${discount_value}"
                elif discount_type == 'free': discount_text = "全免"
                else: discount_text = str(discount_value)
                status = "✅ 已使用" if data.get('used', False) else ("🔴 已過期" if is_expired else "🟢 可使用")
                display_data.append({"優惠碼": code, "折扣": discount_text, "狀態": status, "使用用戶": data.get('used_by', '-') or '-', "來源": data.get('source', '-'), "到期日": expiry_str})
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
        else:
            st.info("暫無優惠碼")
    with col2:
        st.write("### ➕ 產生新優惠碼")
        with st.form(key="gen_promo_form"):
            duration = st.number_input("有效期 (天)", min_value=1, value=30, key="promo_duration")
            discount_type = st.selectbox("折扣類型", ["percentage", "fixed", "free"], key="promo_discount_type",
                                         format_func=lambda x: {"percentage": "百分比", "fixed": "固定金額", "free": "完全免費"}.get(x, x))
            if discount_type == 'percentage':
                discount_value = st.number_input("折扣百分比", min_value=1, max_value=100, value=20, key="promo_discount_value")
            elif discount_type == 'fixed':
                discount_value = st.number_input("減免金額", min_value=1, value=20, key="promo_discount_value")
            else:
                discount_value = 0
            if st.form_submit_button("🎁 產生優惠碼", type="primary"):
                code = generate_promo_code().upper()
                expiry = (datetime.now() + timedelta(days=duration)).isoformat()
                promos[code] = {"used": False, "expiry": expiry, "created_at": datetime.now().isoformat(), "discount_type": discount_type, "discount_value": discount_value, "used_by": None, "source": "手動產生"}
                save_promos(promos)
                st.success(f"✅ 優惠碼：`{code}`")
                st.rerun()

def admin_accuracy_monitor():
    st.subheader("📈 預測準確率監控")
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        st.info("暫時未有預測記錄")
        return
    total = len(records)
    hit = sum(1 for r in records if r.get('is_hit') is True)
    hit_rate = hit/total if total>0 else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("總預測記錄", total)
    col2.metric("命中次數", hit)
    col3.metric("命中率", f"{hit_rate:.2%}")

def admin_subscription(): st.subheader("⏰ 訂閱管理"); st.info("功能開發中")

def admin_payment_review():
    st.subheader("📤 付款審核")
    pending = get_all_pending_requests()
    if not pending:
        st.info("✅ 目前沒有待審核嘅付款申請")
        return
    for item in pending:
        username = item['username']
        req = item['request']
        with st.container():
            cols = st.columns([2, 2, 1.5, 1.5, 2])
            with cols[0]: st.write(f"👤 **{username}**")
            with cols[1]:
                st.write(f"📌 {req.get('plan_name', '未知')}")
                st.write(f"💰 ${req.get('final_price', 0):.2f}")
                if req.get('promo_code'): st.caption(f"🎟️ {req.get('promo_code')}")
            with cols[2]: st.caption(req.get('submitted_at', '')[:16])
            with cols[3]: st.warning("⏳ 待審核")
            with cols[4]:
                if st.button("✅ 批准", key=f"approve_{req.get('id')}"):
                    success, msg = approve_payment_request(username, req['id'], st.session_state.username)
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
                if st.button("❌ 拒絕", key=f"reject_{req.get('id')}"):
                    success, msg = reject_payment_request(username, req['id'], st.session_state.username)
                    if success: st.warning(msg); st.rerun()
            st.divider()

def admin_monitoring(): st.subheader("📡 系統監控"); st.info("系統正常")

def admin_content():
    st.subheader("📝 內容管理")
    uploaded = st.file_uploader("選擇 CSV 排位表", type=['csv'], key="upload_racecard")
    if uploaded:
        with open('racecard_uploaded.csv', 'wb') as f:
            f.write(uploaded.getbuffer())
        st.success("✅ 排位表已更新")

def admin_automation(): st.subheader("🤖 自動化工具"); st.info("功能開發中")

def admin_security():
    st.subheader("🔐 安全與權限")
    logs = load_logs()
    if logs.get('logs'):
        st.dataframe(pd.DataFrame(logs['logs'][-20:]), use_container_width=True)

def admin_user_monitor():
    st.subheader("👁️ 用戶監控")
    col1, col2, col3 = st.columns(3)
    with col1:
        users = load_users()
        user_list = ["全部用戶"] + list(users.keys())
        selected_user = st.selectbox("👤 篩選用戶", user_list, key="monitor_user")
    with col2:
        days = st.selectbox("📅 最近日數", [1, 7, 14, 30, 90, 365], index=3, key="monitor_days")
    with col3:
        action_options = {"全部動作": None, "🔑 登入": "login", "🔮 預測": "predict", "💳 付款申請": "payment_submit", "🎰 抽獎": "lottery", "🛍️ 購買": "purchase", "🚪 登出": "logout"}
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
    st.dataframe(df[['timestamp', 'username', 'action', 'details']], use_container_width=True, hide_index=True)

def admin_lottery_config():
    st.subheader("🎰 抽獎設定")
    config = load_lottery_config()
    st.markdown("### ⚙️ 全局設定")
    with st.form(key="lottery_global_form"):
        col1, col2, col3 = st.columns(3)
        with col1: enabled = st.checkbox("開啟抽獎", value=config.get('enabled', True))
        with col2: draws_per_day = st.number_input("每日抽獎次數", min_value=1, max_value=10, value=config.get('draws_per_day', 1), step=1)
        with col3: allow_admin_gift = st.checkbox("允許管理員贈送", value=config.get('allow_admin_gift', True))
        if st.form_submit_button("💾 儲存全局設定", type="primary"):
            config['enabled'] = enabled
            config['draws_per_day'] = draws_per_day
            config['allow_admin_gift'] = allow_admin_gift
            if save_lottery_config(config): st.success("✅ 已儲存"); st.rerun()
    st.divider()
    st.markdown("### 🎯 獎品機率管理")
    prizes = config.get('prizes', [])
    if not prizes: st.info("暫無獎品"); return
    total_weight = sum(p.get('weight', 1) for p in prizes)
    prob_data = []
    for p in prizes:
        weight = p.get('weight', 1)
        prob = (weight / total_weight * 100) if total_weight > 0 else 0
        stock = p.get('stock', -1)
        prob_data.append({"ID": p.get('id'), "圖示": p.get('icon', '🎁'), "獎品": p.get('name', ''), "權重": weight, "機率": f"{prob:.2f}%", "庫存": "∞" if stock == -1 else str(stock)})
    st.dataframe(pd.DataFrame(prob_data), use_container_width=True, hide_index=True)
    fig = px.pie(pd.DataFrame(prob_data), names='獎品', values='權重', title='獎品中獎機率分佈')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### ✏️ 快速調整機率")
    with st.form(key="quick_weight_form"):
        new_weights = {}
        cols = st.columns(min(len(prizes), 3))
        for idx, p in enumerate(prizes):
            col_idx = idx % 3
            with cols[col_idx]:
                st.markdown(f"**{p.get('icon', '🎁')} {p.get('name', '')}**")
                new_w = st.number_input(f"權重", min_value=0, max_value=1000, value=int(p.get('weight', 1)), step=1, key=f"weight_input_{p.get('id')}")
                new_weights[p.get('id')] = new_w
        st.markdown("---")
        preview_total = sum(new_weights.values())
        if preview_total > 0:
            preview_data = []
            for p in prizes:
                w = new_weights.get(p.get('id'), 0)
                prob = (w / preview_total * 100) if preview_total > 0 else 0
                preview_data.append({"獎品": f"{p.get('icon', '🎁')} {p.get('name', '')}", "新權重": w, "新機率": f"{prob:.2f}%"})
            st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
        if st.form_submit_button("💾 儲存所有權重", type="primary"):
            for p in prizes:
                new_w = new_weights.get(p.get('id'))
                if new_w is not None: p['weight'] = max(1, new_w)
            config['prizes'] = prizes
            if save_lottery_config(config): st.success("✅ 已儲存！"); st.rerun()
    st.markdown("#### ⚡ 快速預設")
    col_preset1, col_preset2, col_preset3 = st.columns(3)
    with col_preset1:
        if st.button("🎯 平均分佈", use_container_width=True, key="preset_even"):
            for p in prizes: p['weight'] = 10
            config['prizes'] = prizes
            save_lottery_config(config)
            st.rerun()
    with col_preset2:
        if st.button("💰 重金輕獎", use_container_width=True, key="preset_small"):
            for p in prizes:
                if p.get('type') == 'virtual_coin':
                    val = p.get('value', 0)
                    p['weight'] = 40 if val <= 200 else (15 if val <= 600 else 5)
                else: p['weight'] = 10
            config['prizes'] = prizes
            save_lottery_config(config)
            st.rerun()
    with col_preset3:
        if st.button("🎁 VIP 導向", use_container_width=True, key="preset_vip"):
            for p in prizes:
                if p.get('type') == 'vip_days': p['weight'] = 25
                elif p.get('type') == 'free_predictions': p['weight'] = 20
                elif p.get('type') == 'virtual_coin': p['weight'] = 8
                else: p['weight'] = 10
            config['prizes'] = prizes
            save_lottery_config(config)
            st.rerun()
    st.divider()
    st.markdown("### 🎁 獎品管理")
    with st.expander("➕ 新增獎品", expanded=False):
        with st.form(key="add_prize_form"):
            col1, col2 = st.columns(2)
            with col1:
                prize_name = st.text_input("獎品名稱", key="new_prize_name")
                prize_type = st.selectbox("獎品類型", 
                    ["virtual_coin", "vip_days", "free_predictions", "promo_code", "custom", "nothing"],
                    format_func=lambda x: {
                        "virtual_coin": "💰 虛擬幣", "vip_days": "👑 VIP 天數",
                        "free_predictions": "🎯 免費預測次數", 
                        "promo_code": "🎟️ 優惠碼（自動生成）",
                        "custom": "🎁 自訂文字",
                        "nothing": "😢 謝謝參與"
                    }.get(x, x), key="new_prize_type")
                
                if prize_type == 'promo_code':
                    st.markdown("**🎟️ 優惠碼設定：**")
                    promo_discount_type = st.selectbox("折扣類型", 
                        ["percentage", "fixed", "free"],
                        format_func=lambda x: {"percentage": "百分比", "fixed": "固定金額", "free": "全免"}.get(x, x),
                        key="new_prize_promo_type")
                    if promo_discount_type == 'percentage':
                        promo_discount_value = st.number_input("折扣百分比", min_value=1, max_value=100, value=20, key="new_prize_promo_value")
                    elif promo_discount_type == 'fixed':
                        promo_discount_value = st.number_input("減免金額", min_value=1, value=20, key="new_prize_promo_value")
                    else:
                        promo_discount_value = 0
                    promo_valid_days = st.number_input("有效期（天）", min_value=1, value=7, key="new_prize_promo_days")
                    prize_value = "auto"
                else:
                    prize_value = st.text_input("獎品數值", key="new_prize_value")
                    promo_discount_type = None
                    promo_discount_value = 0
                    promo_valid_days = 0
            with col2:
                prize_weight = st.number_input("權重", min_value=1, value=10, step=1, key="new_prize_weight")
                prize_stock = st.number_input("庫存（-1 = 無限）", min_value=-1, value=-1, step=1, key="new_prize_stock")
                prize_icon = st.text_input("圖示", value="🎁", key="new_prize_icon")
            if st.form_submit_button("✅ 新增", type="primary"):
                if prize_name:
                    if prize_type in ['virtual_coin', 'vip_days', 'free_predictions']:
                        try: value = int(prize_value)
                        except: st.error("數值必須係數字"); st.stop()
                    elif prize_type == 'promo_code':
                        value = "auto"
                    else: value = prize_value
                    new_id = max([p.get('id', 0) for p in prizes], default=0) + 1
                    new_prize = {
                        "id": new_id, "name": prize_name, "type": prize_type,
                        "value": value, "weight": prize_weight,
                        "stock": prize_stock, "icon": prize_icon
                    }
                    if prize_type == 'promo_code':
                        new_prize['discount_type'] = promo_discount_type
                        new_prize['discount_value'] = promo_discount_value
                        new_prize['valid_days'] = promo_valid_days
                    prizes.append(new_prize)
                    config['prizes'] = prizes
                    if save_lottery_config(config): st.success(f"✅ 已新增"); st.rerun()
    with st.expander("✏️ 編輯 / 刪除獎品", expanded=False):
        prize_options = {f"[{p.get('id')}] {p.get('name')}": p for p in prizes}
        selected_label = st.selectbox("選擇獎品", list(prize_options.keys()), key="edit_prize_select")
        selected_prize = prize_options[selected_label]
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            new_weight = st.number_input("新權重", min_value=1, value=int(selected_prize.get('weight', 1)), key="edit_prize_weight")
            new_stock = st.number_input("新庫存", min_value=-1, value=int(selected_prize.get('stock', -1)), key="edit_prize_stock")
        with col_e2:
            new_name = st.text_input("新名稱", value=selected_prize.get('name', ''), key="edit_prize_name")
            new_icon = st.text_input("新圖示", value=selected_prize.get('icon', '🎁'), key="edit_prize_icon")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 儲存", use_container_width=True, key="save_prize_edit"):
                for p in prizes:
                    if p.get('id') == selected_prize.get('id'):
                        p['weight'] = new_weight
                        p['stock'] = new_stock
                        p['name'] = new_name
                        p['icon'] = new_icon
                        break
                config['prizes'] = prizes
                if save_lottery_config(config): st.success("✅ 已更新"); st.rerun()
        with col_btn2:
            if st.button("🗑️ 刪除", use_container_width=True, key="delete_prize"):
                prizes = [p for p in prizes if p.get('id') != selected_prize.get('id')]
                config['prizes'] = prizes
                if save_lottery_config(config): st.success("✅ 已刪除"); st.rerun()
    st.divider()
    if config.get('allow_admin_gift', True):
        st.markdown("### 🎁 管理員贈送獎品")
        if prizes:
            with st.form(key="admin_gift_prize_form"):
                col1, col2 = st.columns(2)
                with col1:
                    users = load_users()
                    target_user = st.selectbox("選擇用戶", list(users.keys()), key="gift_prize_user")
                with col2:
                    gift_prize_label = st.selectbox("選擇獎品", [f"{p.get('icon', '🎁')} {p.get('name', '')}" for p in prizes], key="gift_prize_select")
                if st.form_submit_button("🎁 確認贈送", type="primary"):
                    selected_idx = [f"{p.get('icon', '🎁')} {p.get('name', '')}" for p in prizes].index(gift_prize_label)
                    gift_prize = prizes[selected_idx]
                    success, msg = admin_gift_prize(st.session_state.username, target_user, gift_prize)
                    if success: st.success(msg); st.balloons()
                    else: st.error(msg)
    st.divider()
    st.markdown("### 📋 全部抽獎記錄")
    records = load_lottery_records()
    all_records = records.get('records', [])
    if all_records:
        df_all = pd.DataFrame(all_records[-100:][::-1])
        display_cols = ['draw_time', 'username', 'prize_name', 'source']
        available_cols = [c for c in display_cols if c in df_all.columns]
        st.dataframe(df_all[available_cols], use_container_width=True)

def admin_shop_config():
    st.subheader("🛍️ 商城設定")
    config = load_shop_config()

    # ========== 全局設定 ==========
    with st.form(key="shop_global_form"):
        enabled = st.checkbox("開啟商城", value=config.get('enabled', True))
        if st.form_submit_button("💾 儲存", type="primary"):
            config['enabled'] = enabled
            if save_shop_config(config):
                st.success("✅ 已儲存")
                st.rerun()

    st.divider()

    # ========== 商品列表（可直接編輯） ==========
    st.markdown("### 🎁 商品列表（可直接編輯）")
    st.caption("💡 直接喺表格入面改價錢、庫存、名稱，改完撳「💾 儲存所有變更」")

    items = config.get('items', [])

    if items:
        df_edit = pd.DataFrame(items)
        display_cols = ['id', 'icon', 'name', 'type', 'value', 'price', 'stock', 'desc']
        available_cols = [c for c in display_cols if c in df_edit.columns]
        df_display = df_edit[available_cols].copy()

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "icon": st.column_config.TextColumn("圖示", width="small"),
                "name": st.column_config.TextColumn("名稱", width="medium"),
                "type": st.column_config.SelectboxColumn(
                    "類型",
                    options=["predictions", "vip_days", "lottery_draws", "title", "mystery_box"],
                    width="medium"
                ),
                "value": st.column_config.TextColumn("數值", width="small"),
                "price": st.column_config.NumberColumn("價格（幣）", min_value=1, step=100, width="small"),
                "stock": st.column_config.NumberColumn("庫存（-1=∞）", min_value=-1, step=1, width="small"),
                "desc": st.column_config.TextColumn("描述", width="large"),
            },
            key="shop_items_editor"
        )

        col_save1, col_save2 = st.columns([1, 3])
        with col_save1:
            if st.button("💾 儲存所有變更", type="primary", use_container_width=True, key="save_all_shop_items"):
                new_items = []
                for _, row in edited_df.iterrows():
                    item = {
                        "id": int(row.get('id', 0)),
                        "icon": str(row.get('icon', '🎁')),
                        "name": str(row.get('name', '')),
                        "type": str(row.get('type', 'predictions')),
                        "value": row.get('value', 0),
                        "price": int(row.get('price', 1000)),
                        "stock": int(row.get('stock', -1)),
                        "desc": str(row.get('desc', ''))
                    }
                    if item['type'] in ['predictions', 'vip_days', 'lottery_draws']:
                        try:
                            item['value'] = int(item['value'])
                        except:
                            pass
                    new_items.append(item)

                config['items'] = new_items
                if save_shop_config(config):
                    st.success("✅ 已儲存所有商品變更！")
                    st.rerun()
                else:
                    st.error("❌ 儲存失敗")
        with col_save2:
            st.caption("⚠️ 記得改完之後撳「💾 儲存所有變更」先生效")
    else:
        st.info("暫無商品")

    st.divider()

    # ========== 新增物品 ==========
    with st.expander("➕ 新增物品", expanded=False):
        with st.form(key="add_shop_item_form"):
            col1, col2 = st.columns(2)
            with col1:
                item_name = st.text_input("物品名稱", key="new_shop_name")
                item_type = st.selectbox("物品類型",
                    ["predictions", "vip_days", "lottery_draws", "title", "mystery_box"],
                    format_func=lambda x: {
                        "predictions": "🎯 額外預測次數",
                        "vip_days": "👑 VIP 天數",
                        "lottery_draws": "🎰 額外抽獎次數",
                        "title": "💎 特殊稱號",
                        "mystery_box": "🎁 神秘禮盒"
                    }.get(x, x), key="new_shop_type")
                item_value = st.text_input("物品數值", key="new_shop_value")
            with col2:
                item_price = st.number_input("價格", min_value=1, value=1000, step=100, key="new_shop_price")
                item_stock = st.number_input("庫存（-1 = 無限）", min_value=-1, value=-1, step=1, key="new_shop_stock")
                item_icon = st.text_input("圖示", value="🎁", key="new_shop_icon")
                item_desc = st.text_input("描述", key="new_shop_desc")
            if st.form_submit_button("✅ 新增", type="primary"):
                if item_name:
                    if item_type in ['predictions', 'vip_days', 'lottery_draws']:
                        try:
                            value = int(item_value)
                        except:
                            st.error("數值必須係數字")
                            st.stop()
                    else:
                        value = item_value
                    new_id = max([i.get('id', 0) for i in items], default=0) + 1
                    items.append({
                        "id": new_id, "name": item_name, "type": item_type,
                        "value": value, "price": item_price,
                        "stock": item_stock, "icon": item_icon, "desc": item_desc
                    })
                    config['items'] = items
                    if save_shop_config(config):
                        st.success(f"✅ 已新增")
                        st.rerun()

    # ========== 刪除物品 ==========
    if items:
        with st.expander("🗑️ 刪除物品", expanded=False):
            item_options = {f"[{i.get('id')}] {i.get('name')}": i for i in items}
            selected_label = st.selectbox("選擇物品", list(item_options.keys()), key="delete_shop_item_select")
            selected_item = item_options[selected_label]
            if st.button("🗑️ 確認刪除", key="delete_shop_item_btn"):
                items = [i for i in items if i.get('id') != selected_item.get('id')]
                config['items'] = items
                if save_shop_config(config):
                    st.success("✅ 已刪除")
                    st.rerun()

    st.divider()

    # ========== 銷售記錄 ==========
    st.markdown("### 📋 銷售記錄")
    purchases = load_shop_purchases()
    all_purchases = purchases.get('purchases', [])
    if all_purchases:
        df_all = pd.DataFrame(all_purchases[-100:][::-1])
        display_cols = ['purchased_at', 'username', 'item_name', 'price']
        available_cols = [c for c in display_cols if c in df_all.columns]
        st.dataframe(df_all[available_cols], use_container_width=True)
    else:
        st.info("暫無銷售記錄")

def admin_system_settings():
    users = load_users()
    admin_username = st.session_state.get('admin_username', 'admin')
    user_group = users.get(admin_username, {}).get('group', 'free')
    if user_group != 'super_admin':
        st.error("⛔ 只有超級管理員可以修改")
        return
    st.subheader("⚙️ 系統設定")
    config = load_system_config()
    col1, col2 = st.columns(2)
    with col1:
        enable_registration = st.checkbox("開放註冊", value=config.get("enable_registration", True))
        enable_payment = st.checkbox("啟用付款", value=config.get("enable_payment", True))
        enable_admin = st.checkbox("啟用後台", value=config.get("enable_admin", True))
        price_day = st.number_input("日費價格", min_value=0, value=config.get("price_day", 18), step=1)
        price_month = st.number_input("月費價格", min_value=0, value=config.get("price_month", 128), step=1)
        price_quarter = st.number_input("季費價格", min_value=0, value=config.get("price_quarter", 328), step=1)
    with col2:
        free_limit = st.number_input("免費預測次數", min_value=0, value=config.get("free_limit", 2), step=1)
        admin_password = st.text_input("管理員密碼", value=config.get("admin_password", "z54060437K"), type="password")
        daily_virtual_coin = st.number_input("每日派發虛擬幣", min_value=0, value=config.get("daily_virtual_coin", 1000), step=100)
    if st.button("💾 儲存設定", type="primary"):
        new_config = {"enable_registration": enable_registration, "enable_payment": enable_payment, "enable_admin": enable_admin, "free_limit": free_limit, "admin_password": admin_password, "price_day": price_day, "price_month": price_month, "price_quarter": price_quarter, "daily_virtual_coin": daily_virtual_coin}
        if save_system_config(new_config): st.success("✅ 設定已儲存！"); st.rerun()

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
                    st.rerun()
                else: st.error("❌ 密碼錯誤！")
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
    st.info(f"👤 管理員：{admin_username}")
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
        "🎰 抽獎設定": admin_lottery_config,
        "🛍️ 商城設定": admin_shop_config,
    }
    tab_names = list(tab_functions.keys())
    if is_super_admin:
        tab_names.append("⚙️ 系統設定")
        tab_functions["⚙️ 系統設定"] = admin_system_settings
    tabs = st.tabs(tab_names)
    for i, name in enumerate(tab_names):
        with tabs[i]:
            tab_functions[name]()

def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'username' not in st.session_state: st.session_state.username = None
    if 'role' not in st.session_state: st.session_state.role = 'free'
    if 'show_admin' not in st.session_state: st.session_state.show_admin = False
    if 'admin_authenticated' not in st.session_state: st.session_state.admin_authenticated = False
    if 'show_lottery' not in st.session_state: st.session_state.show_lottery = False
    if 'show_shop' not in st.session_state: st.session_state.show_shop = False
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
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')}")
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
                with st.form("change_password_form"):
                    st.markdown("#### 🔑 修改密碼")
                    old_pw = st.text_input("當前密碼", type="password")
                    new_pw = st.text_input("新密碼", type="password")
                    if st.form_submit_button("更新"):
                        users = load_users()
                        if users.get(st.session_state.username, {}).get('password') == old_pw:
                            users[st.session_state.username]['password'] = new_pw
                            save_users(users)
                            st.success("✅ 密碼已更新")
                        else: st.error("❌ 密碼錯誤")
    with col4:
        if st.session_state.get('logged_in', False):
            if st.button("🚪 登出", use_container_width=True, key="logout_main"):
                log_user_activity(st.session_state.username, 'logout', '用戶登出')
                for key in ['logged_in', 'username', 'role']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
    st.markdown("---")
    display_race_calendar()
    st.markdown("---")
    if st.session_state.logged_in:
        show_user_dashboard(st.session_state.username)
    st.markdown("---")
    st.subheader("🎯 賽事預測控制")
    col_date, col_race, col_btn = st.columns([2, 2, 1])
    with col_date: date = st.date_input("📅 選擇日期", value=pd.to_datetime("2026-09-06"), key="predict_date_mid")
    with col_race: race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=0, key="predict_race_mid")
    with col_btn: predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True, key="predict_btn_mid")
    if predict_btn:
        date_str = date.strftime("%Y-%m-%d")
        with st.spinner("⏳ 正在預測..."):
            try:
                result, pool = run_prediction(date_str, race_no)
                if result is not None and not result.empty:
                    st.success("✅ 預測完成！")
                    if pool: st.info(pool)
                    st.dataframe(result, use_container_width=True)
            except Exception as e: st.error(f"❌ 錯誤：{e}")
    if st.session_state.get('logged_in', False):
        st.markdown("---")
        st.subheader("🎰 每日抽獎")
        col_lot1, col_lot2 = st.columns([1, 3])
        with col_lot1:
            if st.button("🎁 抽獎", use_container_width=True, key="btn_lottery"):
                st.session_state.show_lottery = not st.session_state.get('show_lottery', False)
        with col_lot2:
            can_draw, msg = user_can_draw_today(st.session_state.username)
            if can_draw: st.success(f"🎉 {msg}")
            else: st.info(f"⏰ {msg}")
        if st.session_state.get('show_lottery', False):
            show_lottery_interface(st.session_state.username)
    if st.session_state.get('logged_in', False):
        st.markdown("---")
        st.subheader("🛍️ 虛擬商城")
        col_shop1, col_shop2 = st.columns([1, 3])
        with col_shop1:
            if st.button("🛒 進入商城", use_container_width=True, key="btn_shop"):
                st.session_state.show_shop = not st.session_state.get('show_shop', False)
        with col_shop2:
            shop_balance = get_user_real_balance_shop(st.session_state.username)
            st.info(f"💎 你嘅餘額：**${shop_balance:,.0f}**")
        if st.session_state.get('show_shop', False):
            show_shop_interface(st.session_state.username)
    st.markdown("---")
    st.subheader("💳 付款功能")
    if st.session_state.get('logged_in'): show_paywall()
    else: st.info("請先登入以使用付款功能")
    st.divider()
    st.warning("⚠️ 預測僅供參考，不構成投注建議。")
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | v18.4")

if __name__ == '__main__':
    main()
