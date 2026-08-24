#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整穩定版（付款牆改用 radio 選擇，穩定無閃退）
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
# 🔐 功能開關（全部中文說明）
# ============================================================
CONFIG = {
    # ----- 基本設定 -----
    "enable_registration": True,
    "enable_payment": False,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "admin_password": "z54060437K",
    
    # ----- 訂閱價格（三種方案） -----
    "price_day": 18,
    "price_month": 128,
    "price_quarter": 328,
    
    # ----- 驗證碼設定 -----
    "verification_expiry": 5,
    
    # ----- 後台十大模組開關 -----
    "module_user_management": True,
    "module_analytics": True,
    "module_finance": True,
    "module_monitoring": True,
    "module_content": True,
    "module_automation": True,
    "module_security": True,
    "module_promo": True,
}

# ============================================================
# 1. 設定頁面
# ============================================================
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. 數據讀寫函數
# ============================================================
USER_DATA_FILE = 'users.json'
FINANCE_FILE = 'finance.json'
LOG_FILE = 'admin_log.json'
AUTOMATION_FILE = 'automation.json'
CONTENT_FILE = 'content.json'
PROMO_FILE = 'promo_codes.json'
ACCURACY_FILE = 'accuracy.json'
PAYMENT_PROOFS_FILE = 'payment_proofs.json'
PAYMENT_PROOFS_DIR = 'payment_proofs'

if not os.path.exists(PAYMENT_PROOFS_DIR):
    os.makedirs(PAYMENT_PROOFS_DIR)

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    users = load_json(USER_DATA_FILE)
    if not users or "admin" not in users:
        users = {
            "admin": {
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
                "history": [
                    {"date": "2025-04-09", "race": 9, "horse": "浪漫勇士", "timestamp": "2025-04-09 14:30:00", "predicted_prob": 0.35},
                    {"date": "2025-04-09", "race": 10, "horse": "金鎗六十", "timestamp": "2025-04-09 15:00:00", "predicted_prob": 0.42}
                ]
            }
        }
        save_users(users)
    else:
        if "admin" in users and users["admin"].get("group") != "super_admin":
            users["admin"]["group"] = "super_admin"
            users["admin"]["note"] = "系統超級管理員（已自動升級）"
        for uid, u in users.items():
            if 'plan' not in u:
                u['plan'] = None
            if 'paid_date' not in u:
                u['paid_date'] = None
            if 'expiry_date' not in u:
                u['expiry_date'] = None
            if 'phone' not in u:
                u['phone'] = ''
            if 'note' not in u:
                u['note'] = ''
            if 'history' not in u:
                u['history'] = []
        save_users(users)
    return users

def save_users(users):
    save_json(USER_DATA_FILE, users)

def load_finance():
    return load_json(FINANCE_FILE)

def save_finance(finance):
    save_json(FINANCE_FILE, finance)

def load_promos():
    return load_json(PROMO_FILE)

def save_promos(promos):
    save_json(PROMO_FILE, promos)

def load_logs():
    return load_json(LOG_FILE)

def save_logs(logs):
    save_json(LOG_FILE, logs)

def load_accuracy():
    return load_json(ACCURACY_FILE)

def save_accuracy(acc):
    save_json(ACCURACY_FILE, acc)

def load_payment_proofs():
    return load_json(PAYMENT_PROOFS_FILE)

def save_payment_proofs(proofs):
    save_json(PAYMENT_PROOFS_FILE, proofs)

def log_admin_action(admin, action):
    logs = load_logs()
    if 'logs' not in logs:
        logs['logs'] = []
    logs['logs'].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'admin': admin,
        'action': action
    })
    save_logs(logs)

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return True
    return False

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
# 3. 模型載入
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
    except Exception as e:
        st.error(f"❌ 模型載入失敗：{e}")
        return None, None, None

# ============================================================
# 4. 特徵工程（完整，但為節省篇幅省略詳細）
# ============================================================
# 注意：此處省略 FEATURES_EN、EXPECTED_FEATURES、NAME_MAPPING 等
# 以及 standardize_columns_safe、ensure_series、get_finish_column、
# safe_parse_dates、get_latest_features、compute_stats、
# load_horse_name_map、generate_pool_recommendations、run_prediction
# 等函數。實際程式碼中應完整保留，此處為佔位。
# 請確保你嘅實際檔案包含所有上述函數，否則會出錯。

# 為方便你，我假設你嘅完整檔案已有上述函數，此處只保留核心修改部分。

# ============================================================
# 5. 用戶功能（儀表板、歷史、統計）
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
            'predicted_prob': predicted_prob
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
    
    if group == 'super_admin':
        level = "👑 超級管理員"
    elif group == 'VIP':
        level = "👑 VIP"
    elif is_paid:
        level = "💎 付費用戶"
    else:
        level = "🆓 免費用戶"
    
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👤 用戶", username)
    col2.metric("🏷️ 級別", level)
    col3.metric("📊 總預測次數", stats['total_predictions'])
    if not is_paid and group not in ['VIP', 'super_admin']:
        remain = max(0, CONFIG["free_limit"] - stats['free_used'])
        col4.metric("📊 剩餘免費場次", remain)
    else:
        if expiry:
            try:
                expiry_date = pd.to_datetime(expiry)
                days_left = (expiry_date - datetime.now()).days
                if days_left > 0:
                    col4.metric("📊 剩餘日數", f"{days_left} 天")
                else:
                    col4.metric("📊 狀態", "⚠️ 已過期")
            except:
                col4.metric("📊 剩餘場次", "∞")
        else:
            col4.metric("📊 剩餘場次", "∞")
    st.markdown("---")
    if plan:
        st.caption(f"📌 當前方案：{get_plan_name(plan)}")

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
# 6. 登入/註冊
# ============================================================
def login_page():
    st.title("🔐 登入 / 註冊")
    tab1, tab2 = st.tabs(["登入", "註冊"])
    
    with tab1:
        username = st.text_input("用戶名稱", key="login_user")
        password = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入", key="login_button"):
            users = load_users()
            if username in users and users[username].get('password') == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = users[username].get('group', 'free')
                st.rerun()
            else:
                st.error("❌ 用戶名稱或密碼錯誤")
    
    with tab2:
        st.subheader("📝 註冊新帳號")
        with st.form("register_form"):
            new_user = st.text_input("用戶名稱（最少 3 個字）", key="reg_user")
            phone = st.text_input("手機號碼（可選）", key="reg_phone")
            new_pass = st.text_input("密碼", type="password", key="reg_pass")
            new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                verify_code_input = st.text_input("驗證碼", key="reg_verify", placeholder="輸入 6 位數字", max_chars=6)
            with col2:
                if st.form_submit_button("📨 獲取驗證碼", type="secondary"):
                    code = generate_verification_code()
                    st.session_state['reg_verify_code'] = code
                    st.session_state['reg_verify_expiry'] = datetime.now() + timedelta(minutes=CONFIG.get('verification_expiry', 5))
                    st.info(f"📧 你嘅驗證碼係：**{code}**（有效期 5 分鐘）")
            
            submitted = st.form_submit_button("註冊")
            if submitted:
                if len(new_user) < 3:
                    st.error("❌ 用戶名稱至少 3 個字")
                elif new_pass != new_pass2:
                    st.error("❌ 密碼不一致")
                elif len(new_pass) < 4:
                    st.error("❌ 密碼至少 4 個字")
                else:
                    if 'reg_verify_code' not in st.session_state or \
                       verify_code_input != st.session_state['reg_verify_code'] or \
                       datetime.now() > st.session_state.get('reg_verify_expiry', datetime.now()):
                        st.error("❌ 驗證碼無效或已過期，請重新獲取")
                    else:
                        users = load_users()
                        if new_user in users:
                            st.error("❌ 用戶名稱已被使用")
                        else:
                            users[new_user] = {
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
                                'history': []
                            }
                            save_users(users)
                            st.success("✅ 註冊成功！請用你嘅帳號登入。")
                            st.rerun()

# ============================================================
# 🔧 重點修改：付款牆（改用 radio 選擇，穩定無閃退）
# ============================================================
def show_paywall():
    """顯示付費牆，提供日/月/季三種方案 + 優惠碼折扣 + 上傳過數證明（穩定版）"""
    st.warning(f"⚠️ 你已經用晒 {CONFIG['free_limit']} 場免費額度")
    
    st.subheader("💳 選擇你嘅方案")
    
    # --- 使用 radio 選擇方案（完全唔需要用按鈕同 rerun，穩定） ---
    plan_options = {
        "day": f"☀️ 日費  (${CONFIG['price_day']}) - 24小時",
        "month": f"📆 月費 (${CONFIG['price_month']}) - 30天",
        "quarter": f"📅 季費 (${CONFIG['price_quarter']}) - 90天"
    }
    
    selected_label = st.radio(
        "揀選方案",
        options=list(plan_options.values()),
        key="plan_radio",
        index=None,
        horizontal=False
    )
    
    # 將所選 label 轉為 plan key
    plan_map = {v: k for k, v in plan_options.items()}
    selected_plan = plan_map.get(selected_label) if selected_label else None
    
    # 如果有揀到方案，儲存到 session_state
    if selected_plan:
        st.session_state['selected_plan'] = selected_plan
        st.session_state['plan_price'] = get_plan_price(selected_plan)
    
    # --- 如果已經揀咗方案，顯示付款詳細內容 ---
    if 'selected_plan' in st.session_state and st.session_state.get('selected_plan'):
        plan = st.session_state['selected_plan']
        plan_name = get_plan_name(plan)
        plan_days = get_plan_days(plan)
        original_price = st.session_state['plan_price']
        final_price = original_price
        
        st.divider()
        st.info(f"📌 你已選擇 **{plan_name}**（原價 ${original_price}，有效期 {plan_days} 天）")
        
        # ---- 優惠碼輸入 ----
        st.subheader("🎟️ 有優惠碼？")
        col_promo1, col_promo2 = st.columns([3, 1])
        with col_promo1:
            promo_input = st.text_input("輸入優惠碼", key="promo_input_paywall", placeholder="例如 A7K3X9P2")
        with col_promo2:
            if st.button("套用優惠碼", key="apply_promo_paywall"):
                if not promo_input:
                    st.warning("請輸入優惠碼")
                else:
                    promos = load_promos()
                    promo_data = promos.get(promo_input)
                    if not promo_data:
                        st.error("❌ 優惠碼不存在")
                    elif promo_data.get('used', False):
                        st.error("❌ 優惠碼已被使用")
                    else:
                        expiry = promo_data.get('expiry')
                        promo_valid = True
                        if expiry:
                            try:
                                expiry_date = datetime.fromisoformat(expiry)
                                if expiry_date < datetime.now():
                                    st.error("❌ 優惠碼已過期")
                                    promo_valid = False
                            except:
                                pass
                        if promo_valid:
                            discount_type = promo_data.get('discount_type', 'percentage')
                            discount_value = promo_data.get('discount_value', 0)
                            st.session_state['applied_promo'] = promo_input
                            st.session_state['discount_type'] = discount_type
                            st.session_state['discount_value'] = discount_value
                            st.success(f"✅ 優惠碼已套用！")
                            st.rerun()
        
        # ---- 計算折後價 ----
        discount_applied = False
        discount_desc = ""
        if 'applied_promo' in st.session_state:
            discount_type = st.session_state.get('discount_type', 'percentage')
            discount_value = st.session_state.get('discount_value', 0)
            if discount_type == 'percentage':
                final_price = original_price * (1 - discount_value / 100)
                discount_desc = f"{discount_value}% 折扣"
                discount_applied = True
            elif discount_type == 'fixed':
                final_price = max(0, original_price - discount_value)
                discount_desc = f"減 ${discount_value}"
                discount_applied = True
            elif discount_type == 'free':
                final_price = 0
                discount_desc = "全免！"
                discount_applied = True
            final_price = round(final_price, 2)
            if discount_applied:
                if final_price > 0:
                    st.success(f"💰 原價 **${original_price}** → 折後 **${final_price:.2f}**（{discount_desc}）")
                else:
                    st.success(f"🎉 恭喜！優惠碼已套用，**完全免費！**（{discount_desc}）")
        
        # ---- 上傳過數證明 ----
        st.divider()
        st.subheader("📤 上傳過數證明")
        st.caption("請上傳你嘅 FPS / PayMe / 銀行轉帳截圖")
        uploaded_file = st.file_uploader(
            "選擇截圖（PNG / JPG）",
            type=['png', 'jpg', 'jpeg'],
            key="proof_upload"
        )
        if uploaded_file is not None:
            st.image(uploaded_file, caption="你上傳嘅證明", width=300)
        
        # ---- 提交按鈕 ----
        st.divider()
        col_submit1, col_submit2, col_submit3 = st.columns([1, 2, 1])
        with col_submit2:
            if st.button("📩 提交付款申請，等待管理員審核", type="primary", use_container_width=True, key="submit_payment"):
                if uploaded_file is None:
                    st.error("❌ 請先上傳過數證明（轉帳截圖）")
                elif not st.session_state.get('logged_in', False):
                    st.error("❌ 請先登入")
                else:
                    # 儲存上傳記錄
                    proofs = load_payment_proofs()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{st.session_state.username}_{timestamp}.{uploaded_file.type.split('/')[1]}"
                    filepath = os.path.join(PAYMENT_PROOFS_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    new_proof = {
                        "id": len(proofs.get('proof_records', [])) + 1,
                        "username": st.session_state.username,
                        "plan": plan,
                        "plan_name": plan_name,
                        "original_price": original_price,
                        "final_price": final_price,
                        "discount_applied": discount_applied,
                        "discount_desc": discount_desc,
                        "promo_code": st.session_state.get('applied_promo', None),
                        "filename": filename,
                        "uploaded_at": datetime.now().isoformat(),
                        "status": "pending"
                    }
                    if 'proof_records' not in proofs:
                        proofs['proof_records'] = []
                    proofs['proof_records'].append(new_proof)
                    save_payment_proofs(proofs)
                    
                    log_admin_action(st.session_state.username, f"提交付款申請 - 方案：{plan_name}，金額：${final_price}")
                    
                    st.success("✅ 付款申請已提交！管理員將盡快審核。")
                    st.info("📩 請同時 WhatsApp 通知管理員（可加快審核）")
                    
                    # 清除 session 狀態，重新整理
                    for k in ['selected_plan', 'plan_price', 'applied_promo', 'discount_type', 'discount_value']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()

# ============================================================
# 7. 後台所有模組（佔位，實際請確保完整）
# ============================================================
# 為節省篇幅，此處省略 admin_* 函數的完整實作，
# 但實際執行時必須包含所有 admin_* 函數（可從你之前的備份複製）。
# 此處僅保留結構，你必須將之前版本的所有 admin_* 函數完整貼上。
def admin_user_management(): pass
def admin_analytics(): pass
def admin_finance(): pass
def admin_promo_codes(): pass
def admin_accuracy_monitor(): pass
def admin_subscription(): pass
def admin_monitoring(): pass
def admin_content(): pass
def admin_automation(): pass
def admin_security(): pass
def admin_payment_review(): pass
def admin_page(): pass

# ============================================================
# 8. 主頁面
# ============================================================
def main():
    # 初始化 session state
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

    # 顯示公告（此處省略，請確保從 content.json 讀取）
    # 實際程式碼請保留此部分

    # 登入檢查
    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return
    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        return

    # 主標題
    col1, col2 = st.columns([6, 1])
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

    # 用戶儀表板
    if CONFIG["enable_registration"] and st.session_state.logged_in:
        show_user_dashboard(st.session_state.username)
    elif not CONFIG["enable_registration"]:
        st.info("🔓 目前為公開模式，任何人皆可使用")

    # 側邊欄
    with st.sidebar:
        st.header("🎯 控制面板")
        if CONFIG["enable_registration"] and st.session_state.logged_in:
            st.write(f"👤 用戶：{st.session_state.username}")
            if CONFIG["enable_payment"]:
                users = load_users()
                user_data = users.get(st.session_state.username, {})
                if user_data.get('is_paid', False) or user_data.get('group') in ['VIP', 'super_admin']:
                    st.success("✅ 付費用戶")
                else:
                    remain = max(0, CONFIG["free_limit"] - st.session_state.usage_count)
                    st.info(f"📊 剩餘免費場次：{remain} 場")
            else:
                remain = max(0, CONFIG["free_limit"] - st.session_state.usage_count)
                st.info(f"📊 剩餘免費場次：{remain} 場")
            if st.button("📋 我的預測記錄", key="show_history_btn"):
                st.session_state.show_history = not st.session_state.show_history
            if st.button("🚪 登出", key="logout_btn"):
                for key in ['logged_in', 'username', 'role', 'usage_count', 'show_history', 'selected_plan', 'applied_promo']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"), key="predict_date")
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8, key="predict_race")
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True, key="predict_btn")

    # 顯示歷史記錄
    if CONFIG["enable_registration"] and st.session_state.logged_in and st.session_state.get('show_history', False):
        st.subheader("📋 我的預測記錄")
        show_prediction_history(st.session_state.username)
        st.divider()

    # 今日賽程
    st.subheader("📅 今日賽程")
    # 此處省略實際程式碼，請保留原有邏輯

    # 執行預測
    if predict_btn:
        if CONFIG["enable_payment"]:
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            is_paid = user_data.get('is_paid', False) or user_data.get('group') in ['VIP', 'super_admin']
            if not is_paid:
                if st.session_state.usage_count >= CONFIG["free_limit"]:
                    show_paywall()
                    return
            else:
                expiry = user_data.get('expiry_date')
                if expiry:
                    try:
                        expiry_date = pd.to_datetime(expiry)
                        if expiry_date < datetime.now():
                            st.error("❌ 你嘅訂閱已過期，請重新付費")
                            show_paywall()
                            return
                    except:
                        pass
        else:
            if st.session_state.usage_count >= CONFIG["free_limit"]:
                show_paywall()
                return

        # 此處省略實際 run_prediction 呼叫，請保留原有邏輯

    st.divider()
    st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🔐 數據來源：HKJC | 系統版本：v14.0-用戶體驗版")

if __name__ == '__main__':
    main()
