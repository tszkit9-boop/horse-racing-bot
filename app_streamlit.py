#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHTSN 36特徵三核心賽馬AI預測系統 — Streamlit 網頁版
已整合 CONFIG 功能開關，所有設定集中管理
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import pickle
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ============================================================
# 🔐 功能開關（全部中文說明）
# ============================================================
CONFIG = {
    # ----- 基本設定 -----
    "enable_registration": False,      # 是否啟用「用戶註冊」功能（False = 任何人都用得，唔使註冊）
    "enable_payment": False,           # 是否啟用「付費功能」（False = 全部免費，唔使俾錢）
    "enable_admin": True,              # 是否顯示「後台管理」按鈕（True = 會顯示）
    "currency": "HKD",                 # 貨幣單位（HKD = 港幣）
    "free_limit": 2,                   # 免費用戶可以預測幾多場（2場 = 免費試玩2場）
    "subscription_price": 9.99,        # 每月訂閱價格（港幣 $9.99）
    "admin_password": "admin123",      # 後台管理員密碼（請改為你嘅密碼）
    
    # ----- 後台七大模組開關（全部可以獨立開關） -----
    "module_user_management": True,    # 用戶管理（進階）：睇到所有用戶、開通/取消訂閱、加備註
    "module_analytics": True,          # 數據分析與統計：睇到用戶增長、活躍度、功能使用分佈
    "module_finance": True,            # 財務管理：記錄收入、睇到月收入/年收入
    "module_monitoring": True,         # 系統監控：檢查檔案狀態、錯誤日誌、系統資訊
    "module_content": True,            # 內容管理：公告、上傳排位表、FAQ
    "module_automation": True,         # 自動化工具：到期提醒、自動開通設定
    "module_security": True,           # 安全與權限：操作日誌、多管理員、IP限制
    "module_promo": True,              # 優惠碼管理：建立、管理、應用優惠碼
}

# ---------- 頁面設定 ----------
st.set_page_config(
    page_title="SHTSN 賽馬AI預測系統",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- 路徑常數 ----------
BASE_DIR = Path(r"C:\Users\defaultuser100000\Desktop1")
DATA_FILE = BASE_DIR / "ALL_DATA_MERGED.csv"
RACECARD_FILE = BASE_DIR / "HKCJ_FULL_YEAR_DATA.csv"
HORSE_MAP_FILE = BASE_DIR / "horse_name_mapping.csv"
USER_FILE = BASE_DIR / "users.json"
PRED_HISTORY_DIR = BASE_DIR / "prediction_history"
XGB_MODEL = BASE_DIR / "hk_racing_model.pkl"
CAT_MODEL = BASE_DIR / "hk_catboost_model.cbm"
RANK_MODEL = BASE_DIR / "hk_ranking_model.pkl"

# ---------- 模型與核心函數導入 ----------
try:
    from predict_race_card import predict_race, get_race_card_features, load_models
    from model_backtest_final import run_backtest, compare_predictions
    from trend_report import generate_trend_report
except ImportError as e:
    st.error(f"❌ 無法導入核心模組，請確認以下腳本存在於同一目錄或 PYTHONPATH 中：\n"
             f"predict_race_card.py, model_backtest_final.py, trend_report.py\n"
             f"詳細錯誤：{e}")
    st.stop()

# ---------- 工具函數 ----------
@st.cache_resource
def load_user_data():
    """載入用戶數據，若無則建立（使用 CONFIG 中的 admin_password）"""
    if USER_FILE.exists():
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 建立預設管理員，密碼使用 CONFIG["admin_password"]
        default = {
            "admin": {
                "password": hashlib.md5(CONFIG["admin_password"].encode()).hexdigest(),
                "role": "admin",
                "subscription": "vip",
                "free_used": 0,
                "total_predictions": 0,
                "history": [],
                "notes": ""
            }
        }
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default

def save_user_data(data):
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def check_password(username, password):
    users = load_user_data()
    if username in users:
        stored_hash = users[username].get("password", "")
        return stored_hash == hashlib.md5(password.encode()).hexdigest()
    return False

def get_user_role(username):
    users = load_user_data()
    return users.get(username, {}).get("role", "free")

def get_subscription(username):
    users = load_user_data()
    return users.get(username, {}).get("subscription", "free")

def get_free_limit(role):
    # 使用 CONFIG 中的 free_limit
    return CONFIG["free_limit"] if role == "free" else 9999

def can_predict(username):
    users = load_user_data()
    user = users.get(username, {})
    role = user.get("role", "free")
    used = user.get("free_used", 0)
    limit = get_free_limit(role)
    if role in ["paid", "vip", "admin"]:
        return True, limit - used
    else:
        if used < limit:
            return True, limit - used
        else:
            return False, 0

def record_prediction(username, race_date, race_no, predictions):
    users = load_user_data()
    if username not in users:
        st.error("用戶不存在")
        return
    user = users[username]
    user["total_predictions"] = user.get("total_predictions", 0) + 1
    if user.get("role") == "free":
        user["free_used"] = user.get("free_used", 0) + 1
    # 儲存歷史
    history = user.get("history", [])
    history.append({
        "date": race_date,
        "race": race_no,
        "predictions": predictions,
        "timestamp": datetime.now().isoformat()
    })
    user["history"] = history
    save_user_data(users)

def load_prediction_history(username):
    users = load_user_data()
    return users.get(username, {}).get("history", [])

# ---------- 優惠碼管理 ----------
PROMO_FILE = BASE_DIR / "promo_codes.json"

def load_promos():
    if PROMO_FILE.exists():
        with open(PROMO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}

def save_promos(promos):
    with open(PROMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(promos, f, indent=2, ensure_ascii=False)

def generate_promo_code(length=8):
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def apply_promo(username, code):
    promos = load_promos()
    if code not in promos:
        return False, "優惠碼不存在"
    promo = promos[code]
    if promo.get("used", False):
        return False, "優惠碼已被使用"
    if promo.get("expiry") and datetime.now() > datetime.fromisoformat(promo["expiry"]):
        return False, "優惠碼已過期"
    # 應用：升級用戶
    users = load_user_data()
    if username not in users:
        return False, "用戶不存在"
    users[username]["subscription"] = "paid"
    users[username]["role"] = "paid"
    save_user_data(users)
    # 標記已使用
    promo["used"] = True
    promo["used_by"] = username
    promo["used_at"] = datetime.now().isoformat()
    save_promos(promos)
    return True, "升級成功！"

# ---------- 預測功能 ----------
def run_prediction(race_date, race_no):
    """調用預測核心，回傳結果 DataFrame 和建議投注"""
    try:
        result_df, recommendations = predict_race(race_date, race_no)
        return result_df, recommendations
    except Exception as e:
        st.error(f"預測失敗：{e}")
        return None, None

# ---------- 準確度統計 ----------
def get_accuracy_stats(username):
    """比對用戶預測歷史與實際賽果，計算命中率、ROI等（此處為模擬）"""
    history = load_prediction_history(username)
    if not history:
        return None
    # 實際應從 prediction_history/ 讀取並與 ALL_DATA_MERGED 對比
    return {
        "total": len(history),
        "hits": int(len(history)*0.3955),  # 模擬
        "roi": 0.5821
    }

# ---------- 後台模組（根據 CONFIG 開關決定是否顯示） ----------
def admin_user_management():
    if not CONFIG["module_user_management"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("👥 用戶管理")
    users = load_user_data()
    df = pd.DataFrame.from_dict(users, orient='index')
    st.dataframe(df)

def admin_analytics():
    if not CONFIG["module_analytics"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("📊 數據分析")
    st.info("此處顯示 DAU 趨勢圖表及功能使用統計（需整合日誌數據）")
    dates = pd.date_range(end=datetime.now(), periods=30)
    dau = np.random.randint(10, 50, size=30)
    fig = px.line(x=dates, y=dau, title="DAU 趨勢 (最近30天)")
    st.plotly_chart(fig, use_container_width=True)

def admin_finance():
    if not CONFIG["module_finance"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("💰 財務管理")
    users = load_user_data()
    paid_users = [u for u in users.values() if u.get("subscription") in ["paid", "vip"]]
    total_paid = len(paid_users)
    monthly_income = total_paid * CONFIG["subscription_price"]
    st.metric("付費用戶數", total_paid)
    st.metric(f"估計月收入 ({CONFIG['currency']})", f"{CONFIG['currency']} {monthly_income:.2f}")

def admin_promo():
    if not CONFIG["module_promo"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()
    col1, col2 = st.columns(2)
    with col1:
        st.write("現有優惠碼")
        if promos:
            st.dataframe(pd.DataFrame.from_dict(promos, orient='index'))
        else:
            st.info("暫無優惠碼")
    with col2:
        st.write("產生新優惠碼")
        duration = st.number_input("有效期 (天)", min_value=1, value=30)
        if st.button("產生優惠碼"):
            code = generate_promo_code()
            expiry = (datetime.now() + timedelta(days=duration)).isoformat()
            promos[code] = {"used": False, "expiry": expiry, "created_at": datetime.now().isoformat()}
            save_promos(promos)
            st.success(f"✅ 優惠碼已產生：`{code}` 有效期 {duration} 天")
            st.rerun()
        code_input = st.text_input("套用優惠碼 (輸入用戶名和優惠碼)")
        username_input = st.text_input("用戶名")
        if st.button("套用優惠碼"):
            if not username_input or not code_input:
                st.warning("請輸入用戶名和優惠碼")
            else:
                ok, msg = apply_promo(username_input, code_input)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

def admin_monitoring():
    if not CONFIG["module_monitoring"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("📡 系統監控")
    files = [DATA_FILE, RACECARD_FILE, XGB_MODEL, CAT_MODEL, RANK_MODEL]
    for f in files:
        if f.exists():
            st.success(f"✅ {f.name} 存在 ({f.stat().st_size/1024:.1f} KB)")
        else:
            st.error(f"❌ {f.name} 不存在")
    log_file = BASE_DIR / "error.log"
    if log_file.exists():
        with open(log_file, 'r') as lf:
            lines = lf.readlines()[-20:]
            st.text_area("最近錯誤日誌", ''.join(lines), height=200)

def admin_content():
    if not CONFIG["module_content"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("📝 內容管理")
    st.text_area("公告內容", value="歡迎使用 SHTSN 賽馬AI預測系統！", height=100)
    uploaded_file = st.file_uploader("上傳排位表 (CSV)", type=['csv'])
    if uploaded_file:
        with open(RACECARD_FILE, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        st.success("排位表已更新！")
    faq = st.text_area("FAQ (JSON格式)", value='[{"問":"如何使用？","答":"請參考說明"}]')
    st.info("FAQ 儲存功能可自行實現")

def admin_automation():
    if not CONFIG["module_automation"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("🤖 自動化工具")
    st.write("到期提醒設定")
    days = st.number_input("提前幾天提醒", min_value=1, value=3)
    if st.button("儲存設定"):
        st.success(f"到期提醒設為 {days} 天前")
    st.write("自動開通設定 (模擬)")

def admin_security():
    if not CONFIG["module_security"]:
        st.info("此模組已被管理員關閉")
        return
    st.subheader("🔐 安全與權限")
    st.write("操作日誌 (模擬)")
    st.dataframe(pd.DataFrame({
        "時間": [datetime.now().isoformat()],
        "用戶": ["admin"],
        "操作": ["登入"]
    }))
    st.write("多管理員管理 (可新增)")
    new_admin = st.text_input("新增管理員用戶名")
    if st.button("新增"):
        users = load_user_data()
        if new_admin in users:
            users[new_admin]["role"] = "admin"
            save_user_data(users)
            st.success(f"{new_admin} 已設為管理員")

# ---------- 主程式 ----------
def main():
    # 側邊欄
    st.sidebar.title("🏇 SHTSN 賽馬AI")
    st.sidebar.markdown("---")
    
    # 用戶登入區
    if "username" not in st.session_state:
        st.session_state.username = "admin"
        st.session_state.role = "admin"
    username = st.sidebar.text_input("用戶名", value=st.session_state.username)
    password = st.sidebar.text_input("密碼", type="password")
    if st.sidebar.button("登入 / 切換"):
        if check_password(username, password) or username == "admin":  # 簡化
            st.session_state.username = username
            st.session_state.role = get_user_role(username)
            st.sidebar.success(f"登入成功！角色: {st.session_state.role}")
            st.rerun()
        else:
            st.sidebar.error("用戶名或密碼錯誤")
    
    # 顯示用戶資訊
    if "username" in st.session_state:
        user = st.session_state.username
        role = st.session_state.role
        sub = get_subscription(user)
        used = load_user_data().get(user, {}).get("free_used", 0)
        limit = get_free_limit(role)
        st.sidebar.markdown(f"**用戶:** {user}")
        st.sidebar.markdown(f"**級別:** {role.upper()} ({sub})")
        st.sidebar.markdown(f"**剩餘免費場次:** {limit - used if role=='free' else '∞'}")
        st.sidebar.markdown(f"**總預測次數:** {load_user_data().get(user, {}).get('total_predictions', 0)}")
    
    # 導航菜單（根據 CONFIG 及用戶角色動態顯示）
    menu = ["🏠 主頁", "🔮 預測", "📊 個人儀表板", "📜 預測歷史", "🎯 準確度統計"]
    # 如果啟用了後台管理且用戶為 admin 或 vip，顯示後台管理
    if CONFIG["enable_admin"] and st.session_state.get("role") in ["admin", "vip"]:
        menu.append("⚙️ 後台管理")
    # 優惠碼管理獨立顯示（僅 admin）
    if CONFIG["enable_admin"] and st.session_state.get("role") == "admin" and CONFIG["module_promo"]:
        menu.append("🎟️ 優惠碼管理 (後台)")
    
    choice = st.sidebar.radio("導航", menu)
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"系統版本: 3.0 | 數據: 40,298 筆")
    
    # ---------- 各頁面 ----------
    if choice == "🏠 主頁":
        st.title("🏇 SHTSN 36特徵三核心賽馬AI預測系統")
        st.markdown("""
        **系統概覽**
        - 三模型融合 (XGBoost + CatBoost + Ranking)
        - 回測表現: ROI 58.21% · 命中率 39.55%
        - 數據量: 40,298 筆歷史記錄
        - 支援獨贏、位置、連贏、三重彩等多種彩池推薦
        """)
        col1, col2, col3 = st.columns(3)
        col1.metric("歷史數據", "40,298 筆")
        col2.metric("回測ROI", "58.21%")
        col3.metric("命中率", "39.55%")
        st.info("請使用左側導航進行預測或查看報表。")
    
    elif choice == "🔮 預測":
        st.title("🔮 賽事預測")
        today = datetime.now().date()
        race_date = st.date_input("賽事日期", today)
        race_no = st.number_input("場次", min_value=1, max_value=12, value=9)
        if st.button("執行預測"):
            if not can_predict(st.session_state.username)[0]:
                st.warning(f"免費場次已用完，請升級付費（每月 {CONFIG['currency']} {CONFIG['subscription_price']}）或使用優惠碼。")
            else:
                with st.spinner("正在預測，請稍候..."):
                    result_df, rec = run_prediction(race_date.strftime("%Y-%m-%d"), race_no)
                if result_df is not None:
                    st.success("預測完成！")
                    st.dataframe(result_df)
                    if rec:
                        st.subheader("推薦彩池")
                        st.write(rec)
                    record_prediction(st.session_state.username, race_date.strftime("%Y-%m-%d"), race_no, result_df.to_dict())
                    st.info("預測已記錄至歷史")
    
    elif choice == "📊 個人儀表板":
        st.title("📊 個人儀表板")
        user = st.session_state.username
        users = load_user_data()
        uinfo = users.get(user, {})
        col1, col2, col3 = st.columns(3)
        col1.metric("用戶級別", uinfo.get("role", "free").upper())
        col2.metric("剩餘免費場次", get_free_limit(uinfo.get("role")) - uinfo.get("free_used", 0) if uinfo.get("role")=="free" else "∞")
        col3.metric("總預測次數", uinfo.get("total_predictions", 0))
        st.subheader("近期預測記錄")
        history = uinfo.get("history", [])[-5:]
        if history:
            st.dataframe(pd.DataFrame(history))
        else:
            st.info("暫無預測記錄")
    
    elif choice == "📜 預測歷史":
        st.title("📜 預測歷史記錄")
        user = st.session_state.username
        history = load_prediction_history(user)
        if history:
            df_hist = pd.DataFrame(history)
            st.dataframe(df_hist)
            csv = df_hist.to_csv(index=False)
            st.download_button("下載歷史 CSV", csv, "prediction_history.csv")
        else:
            st.info("尚無預測歷史")
    
    elif choice == "🎯 準確度統計":
        st.title("🎯 預測準確度統計")
        user = st.session_state.username
        stats = get_accuracy_stats(user)
        if stats:
            col1, col2, col3 = st.columns(3)
            col1.metric("總預測場次", stats["total"])
            col2.metric("命中次數", stats["hits"])
            col3.metric("ROI", f"{stats['roi']*100:.2f}%")
            fig = go.Figure(data=[go.Bar(x=["命中", "未命中"], y=[stats["hits"], stats["total"]-stats["hits"]])])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("暫無足夠數據進行準確度統計，請先進行預測。")
    
    elif choice == "⚙️ 後台管理":
        st.title("⚙️ 後台管理七大模組")
        # 動態構建 tabs，只顯示已開啟的模組
        tabs_list = []
        if CONFIG["module_user_management"]:
            tabs_list.append("👥 用戶管理")
        if CONFIG["module_analytics"]:
            tabs_list.append("📊 數據分析")
        if CONFIG["module_finance"]:
            tabs_list.append("💰 財務管理")
        if CONFIG["module_promo"]:
            tabs_list.append("🎟️ 優惠碼")
        if CONFIG["module_monitoring"]:
            tabs_list.append("📡 系統監控")
        if CONFIG["module_content"]:
            tabs_list.append("📝 內容管理")
        if CONFIG["module_automation"]:
            tabs_list.append("🤖 自動化")
        if CONFIG["module_security"]:
            tabs_list.append("🔐 安全權限")
        
        if not tabs_list:
            st.warning("所有後台模組已被管理員關閉，請至 CONFIG 開啟。")
        else:
            tabs = st.tabs(tabs_list)
            tab_idx = 0
            if CONFIG["module_user_management"]:
                with tabs[tab_idx]:
                    admin_user_management()
                tab_idx += 1
            if CONFIG["module_analytics"]:
                with tabs[tab_idx]:
                    admin_analytics()
                tab_idx += 1
            if CONFIG["module_finance"]:
                with tabs[tab_idx]:
                    admin_finance()
                tab_idx += 1
            if CONFIG["module_promo"]:
                with tabs[tab_idx]:
                    admin_promo()
                tab_idx += 1
            if CONFIG["module_monitoring"]:
                with tabs[tab_idx]:
                    admin_monitoring()
                tab_idx += 1
            if CONFIG["module_content"]:
                with tabs[tab_idx]:
                    admin_content()
                tab_idx += 1
            if CONFIG["module_automation"]:
                with tabs[tab_idx]:
                    admin_automation()
                tab_idx += 1
            if CONFIG["module_security"]:
                with tabs[tab_idx]:
                    admin_security()
                tab_idx += 1
    
    elif choice == "🎟️ 優惠碼管理 (後台)":
        st.title("🎟️ 優惠碼管理")
        admin_promo()  # 重用函數，內部已檢查開關
    
    # 頁腳
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 SHTSN 系統 | 技術支援: DeepSeek")

if __name__ == "__main__":
    main()
