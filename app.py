#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整版（含註冊/收費/後台）
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
# 2. 用戶數據管理
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

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return True
    return False

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
# 4. 登入/註冊頁面
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
# 5. 付費牆
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
    if CONFIG["enable_admin"]:
        with st.expander("🔐 管理員開通"):
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
# 6. 管理員後台
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
        st.json(CONFIG)

# ============================================================
# 7. 主頁面
# ============================================================
def main():
    # 初始化 session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False

    # ----- 如果啟用註冊，未登入就顯示登入頁 -----
    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    # ----- 如果係管理員模式 -----
    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        if st.button("⬅️ 返回主頁"):
            st.session_state.show_admin = False
            st.rerun()
        return

    # ----- 主頁面 -----
    # 標題
    st.title("🏇 賽馬預測系統")
    st.markdown("AI 驅動・即時預測・彩池推薦")
    st.caption(f"{datetime.now().strftime('%Y年%m月%d日')} · 36個特徵 · 三模型融合 · 六種彩池")

    # ----- 側邊欄 -----
    with st.sidebar:
        st.header("🎯 控制面板")
        # 顯示用戶狀態
        if CONFIG["enable_registration"] and st.session_state.logged_in:
            st.write(f"👤 用戶：{st.session_state.username}")
            if CONFIG["enable_payment"]:
                users = load_users()
                user_data = users.get(st.session_state.username, {})
                if user_data.get('is_paid', False):
                    st.success("✅ 付費用戶")
                else:
                    remain = max(0, CONFIG["free_limit"] - st.session_state.usage_count)
                    st.info(f"📊 剩餘免費場次：{remain} 場")
        
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"))
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8)
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)
        
        # ----- 後台管理入口（側邊欄底部）-----
        if CONFIG["enable_admin"]:
            st.divider()
            if st.button("🔐 後台管理", use_container_width=True):
                st.session_state.show_admin = True
                st.rerun()

    # ----- 今日賽程 -----
    st.subheader("📅 今日賽程")
    try:
        df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        # 簡化顯示
        st.info("今日沒有賽事（示範）")
    except:
        st.info("今日沒有賽事")

    # ----- 執行預測 -----
    if predict_btn:
        # 檢查付費限額（如果啟用付款）
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
            # 此處應該呼叫你原本嘅 run_prediction 函數
            # 為示範，模擬結果
            st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
            st.info("（此處顯示預測 TOP 5 同彩池推薦）")
            
            # 增加使用次數
            if CONFIG["enable_payment"]:
                users = load_users()
                if st.session_state.username in users:
                    users[st.session_state.username]['free_usage'] = users[st.session_state.username].get('free_usage', 0) + 1
                    users[st.session_state.username]['total_usage'] = users[st.session_state.username].get('total_usage', 0) + 1
                    save_users(users)
                st.session_state.usage_count += 1

    # ----- 底部 -----
    st.divider()
    st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🔐 數據來源：HKJC | 系統版本：v7.0-賽馬主題")

if __name__ == '__main__':
    main()
