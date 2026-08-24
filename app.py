#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整版（含註冊/收費/後台，全部可開關）
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

# ============================================================
# 🔐 功能開關（一鍵控制所有新功能）
# ============================================================
CONFIG = {
    "enable_registration": False,      # True = 要註冊先用得，False = 任何人都用得
    "enable_payment": False,           # True = 要俾錢，False = 全部免費
    "enable_admin": True,              # True = 管理員功能可見，False = 隱藏
    "currency": "HKD",                 # 貨幣單位
    "free_limit": 2,                   # 免費場次上限
    "subscription_price": 9.99,        # 每月訂閱價格（港幣）
    "admin_password": "admin123",      # 管理員密碼（請更改）
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
# 2. 用戶數據管理（JSON 儲存）
# ============================================================
USER_DATA_FILE = 'users.json'

def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def init_user(username):
    users = load_users()
    if username not in users:
        users[username] = {
            'password': 'password123',  # 預設密碼，用戶可更改
            'is_paid': False,
            'paid_date': None,
            'expiry_date': None,
            'free_usage': 0,
            'total_usage': 0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_users(users)
    return users[username]

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return True
    return False

# ============================================================
# 3. 模型載入（原有）
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
# 4. 完整特徵工程（原有，因篇幅省略，但你已有完整版）
# ============================================================
# 此處保留你原有嘅 FEATURES_EN、EXPECTED_FEATURES、NAME_MAPPING
# 以及 standardize_columns_safe、ensure_series、get_finish_column、
# safe_parse_dates、get_latest_features、compute_stats、
# load_horse_name_map、generate_pool_recommendations、run_prediction 等函數
# 為節省篇幅，我假設你已將佢哋複製過嚟，或者直接用你現有嘅版本。
# 下面只保留最關鍵嘅部份作為示範。

# ============================================================
# 5. 註冊／登入頁面
# ============================================================
def login_page():
    st.title("🔐 登入 / 註冊")
    
    tab1, tab2 = st.tabs(["登入", "註冊"])
    
    with tab1:
        username = st.text_input("用戶名稱", key="login_user")
        password = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ 登入成功！")
                st.rerun()
            else:
                st.error("❌ 用戶名稱或密碼錯誤")
    
    with tab2:
        new_user = st.text_input("用戶名稱", key="reg_user")
        new_pass = st.text_input("密碼", type="password", key="reg_pass")
        new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
        if st.button("註冊"):
            if new_pass != new_pass2:
                st.error("❌ 密碼不一致")
            elif len(new_user) < 3:
                st.error("❌ 用戶名稱至少 3 個字")
            else:
                users = load_users()
                if new_user in users:
                    st.error("❌ 用戶名稱已被使用")
                else:
                    users[new_user] = {
                        'password': new_pass,
                        'is_paid': False,
                        'paid_date': None,
                        'expiry_date': None,
                        'free_usage': 0,
                        'total_usage': 0,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    save_users(users)
                    st.success("✅ 註冊成功！請返回登入")
                    st.rerun()

# ============================================================
# 6. 付費牆
# ============================================================
def show_paywall():
    st.warning(f"⚠️ 你已經用晒 {CONFIG['free_limit']} 場免費額度")
    
    st.markdown(f"""
    ### 💳 升級至付費版（{CONFIG['currency']}）
    
    **付費版功能：**
    - ✅ 無限場次預測
    - ✅ 全部彩池推薦
    - ✅ 賽果對比
    - ✅ 歷史記錄
    
    **價格：** 每月 {CONFIG['currency']} {CONFIG['subscription_price']:.2f}
    
    **付款方式：**
    1. FPS 轉數快：`你的FPS ID`
    2. PayMe：`你的PayMe連結`
    3. 銀行轉帳：`你的戶口號碼`
    
    📩 付款後請將入數紙 WhatsApp 到 `你的電話號碼`，我哋會喺 30 分鐘內為你開通。
    """)
    
    # 管理員手動開通（用密碼）
    if CONFIG["enable_admin"]:
        with st.expander("🔐 管理員開通（只限管理員）"):
            admin_code = st.text_input("管理員密碼", type="password", key="admin_paywall")
            if admin_code == CONFIG["admin_password"]:
                if st.button("✅ 手動開通此用戶"):
                    users = load_users()
                    if st.session_state.username in users:
                        users[st.session_state.username]['is_paid'] = True
                        users[st.session_state.username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        users[st.session_state.username]['expiry_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                        save_users(users)
                        st.success("✅ 已開通！")
                        st.rerun()

# ============================================================
# 7. 管理員後台
# ============================================================
def admin_page():
    st.title("🔐 後台管理系統")
    
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    
    if not st.session_state.admin_logged_in:
        password = st.text_input("請輸入管理員密碼", type="password")
        if st.button("登入"):
            if password == CONFIG["admin_password"]:
                st.session_state.admin_logged_in = True
                st.success("✅ 登入成功！")
                st.rerun()
            else:
                st.error("❌ 密碼錯誤")
        return
    
    st.success("✅ 已登入管理員模式")
    
    users = load_users()
    
    with st.sidebar:
        st.header("📋 管理功能")
        menu = st.radio("選擇功能", ["📊 總覽", "👥 用戶管理", "⚙️ 設定"])
        if st.button("🚪 登出"):
            st.session_state.admin_logged_in = False
            st.rerun()
    
    if menu == "📊 總覽":
        st.subheader("📊 系統總覽")
        col1, col2, col3, col4 = st.columns(4)
        total_users = len(users)
        paid_users = sum(1 for u in users.values() if u.get('is_paid', False))
        total_usage = sum(u.get('total_usage', 0) for u in users.values())
        col1.metric("👥 總用戶", total_users)
        col2.metric("💎 付費用戶", paid_users)
        col3.metric("📊 總預測次數", total_usage)
        col4.metric("💰 估計月收入", f"{CONFIG['currency']} {paid_users * CONFIG['subscription_price']:.2f}")
        st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    elif menu == "👥 用戶管理":
        st.subheader("👥 用戶管理")
        search = st.text_input("🔍 搜尋用戶")
        filtered = {k: v for k, v in users.items() if search.lower() in k.lower()}
        if not filtered:
            st.info("沒有找到用戶")
        else:
            for username, data in filtered.items():
                with st.expander(f"👤 {username} ({'💎 付費' if data.get('is_paid') else '🆓 免費'})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**狀態：** {'💎 付費用戶' if data.get('is_paid') else '🆓 免費用戶'}")
                        if data.get('paid_date'):
                            st.write(f"**付款日期：** {data.get('paid_date')}")
                        if data.get('expiry_date'):
                            st.write(f"**到期日：** {data.get('expiry_date')}")
                        st.write(f"**免費使用次數：** {data.get('free_usage', 0)}")
                        st.write(f"**總使用次數：** {data.get('total_usage', 0)}")
                        st.write(f"**加入日期：** {data.get('created_at', '未知')}")
                    with col2:
                        if data.get('is_paid'):
                            if st.button(f"❌ 取消訂閱", key=f"unsub_{username}"):
                                users[username]['is_paid'] = False
                                users[username]['expiry_date'] = None
                                save_users(users)
                                st.success(f"已取消 {username} 嘅訂閱")
                                st.rerun()
                        else:
                            if st.button(f"✅ 開通付費", key=f"sub_{username}"):
                                users[username]['is_paid'] = True
                                users[username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                users[username]['expiry_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                                save_users(users)
                                st.success(f"已開通 {username} 嘅付費功能")
                                st.rerun()
    
    elif menu == "⚙️ 設定":
        st.subheader("⚙️ 系統設定")
        st.info("修改 CONFIG 變數嚟調整設定（需要重新部署）")
        st.json(CONFIG)

# ============================================================
# 8. 主程式
# ============================================================
def main():
    # 初始化 session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'is_paid' not in st.session_state:
        st.session_state.is_paid = False

    # ----- 如果啟用註冊，未登入就顯示登入頁 -----
    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    # ----- 已登入或唔使註冊，顯示主內容 -----
    # 顯示用戶狀態（如果有登入）
    if CONFIG["enable_registration"] and st.session_state.logged_in:
        st.sidebar.write(f"👤 用戶：{st.session_state.username}")
        if CONFIG["enable_payment"]:
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            if user_data.get('is_paid', False):
                st.sidebar.success("✅ 付費用戶")
            else:
                remain = CONFIG["free_limit"] - st.session_state.usage_count
                st.sidebar.info(f"📊 剩餘免費場次：{max(0, remain)} 場")
    
    # ----- 顯示主界面（原有預測功能） -----
    st.title("🏇 賽馬預測系統")
    st.markdown("AI 驅動・即時預測・彩池推薦")
    
    # 側邊欄控制
    with st.sidebar:
        st.header("🎯 控制面板")
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"))
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8)
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)
        
        # 管理員後台入口（如果啟用）
        if CONFIG["enable_admin"]:
            st.divider()
            if st.button("🔐 後台管理"):
                st.session_state.show_admin = True

    # 顯示今日賽程（原有）
    st.subheader("📅 今日賽程")
    try:
        df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        # ...（此處保留你原有嘅賽程顯示邏輯）
        st.info("今日沒有賽事（示範）")
    except:
        st.info("今日沒有賽事")
    
    # 執行預測
    if predict_btn:
        # 檢查限額（如果啟用付款）
        if CONFIG["enable_payment"]:
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            is_paid = user_data.get('is_paid', False)
            if not is_paid:
                if st.session_state.usage_count >= CONFIG["free_limit"]:
                    show_paywall()
                    return
        
        date_str = date.strftime('%Y-%m-%d')
        with st.spinner(f"執行預測 {date_str} 第 {race_no} 場..."):
            # 此處呼叫你原有嘅 run_prediction 函數
            # 為示範，我假設 run_prediction 已定義
            # result, pool = run_prediction(date_str, race_no)
            # 如果成功，顯示結果
            st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
            st.info("（此處顯示預測 TOP 5 同彩池推薦）")
            
            # 增加使用次數（如果啟用付款）
            if CONFIG["enable_payment"]:
                if not is_paid:
                    st.session_state.usage_count += 1
                    # 更新用戶記錄
                    users = load_users()
                    if st.session_state.username in users:
                        users[st.session_state.username]['free_usage'] = users[st.session_state.username].get('free_usage', 0) + 1
                        users[st.session_state.username]['total_usage'] = users[st.session_state.username].get('total_usage', 0) + 1
                        save_users(users)
    
    # 顯示後台（如果啟用）
    if CONFIG["enable_admin"] and st.session_state.get('show_admin', False):
        admin_page()
        if st.button("⬅️ 返回主頁"):
            st.session_state.show_admin = False
            st.rerun()

if __name__ == '__main__':
    main()
