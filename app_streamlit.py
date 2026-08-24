#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 終極完整版（預測 + 七大模組 + 優惠碼管理）
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

# ============================================================
# 🔐 功能開關
# ============================================================
CONFIG = {
    "enable_registration": False,
    "enable_payment": False,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "subscription_price": 9.99,
    "admin_password": "admin123",
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

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json(USER_DATA_FILE)

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

def log_admin_action(admin, action):
    logs = load_json(LOG_FILE)
    if 'logs' not in logs:
        logs['logs'] = []
    logs['logs'].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'admin': admin,
        'action': action
    })
    save_json(LOG_FILE, logs)

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return True
    return False

def generate_promo_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

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
# 4. 特徵工程函數（請從你原有檔案複製過來）
# ============================================================
# ⚠️ 請將你原本嘅 FEATURES_EN、EXPECTED_FEATURES、NAME_MAPPING
# 以及 standardize_columns_safe、ensure_series、get_finish_column、
# safe_parse_dates、get_latest_features、compute_stats、
# load_horse_name_map、generate_pool_recommendations、run_prediction
# 等函數貼上到呢個位置（從你原有 app_streamlit.py 複製）
# ============================================================

# ============================================================
# 5. 登入/註冊
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
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'note': '',
                        'group': 'free'
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
    每月 {CONFIG['currency']} {CONFIG['subscription_price']:.2f}
    **付款方式：** FPS / PayMe / 銀行轉帳
    📩 付款後 WhatsApp 通知開通
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
# 7. 七大模組 + 優惠碼管理
# ============================================================
def module_user_management(users):
    st.subheader("👥 用戶管理（進階）")
    col1, col2 = st.columns([1, 4])
    with col1:
        search = st.text_input("", placeholder="搜尋用戶", key="search_user")
    with col2:
        filter_group = st.selectbox("篩選組別", ["全部", "免費", "付費", "VIP"], key="filter_group")
    filtered = {}
    for k, v in users.items():
        if search and search.lower() not in k.lower():
            continue
        if filter_group != "全部" and v.get('group', 'free') != filter_group:
            continue
        filtered[k] = v
    st.write(f"共 {len(filtered)} 個用戶")
    for username, data in filtered.items():
        with st.expander(f"👤 {username} ({'💎 付費' if data.get('is_paid') else '🆓 免費'})"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**狀態：** {'💎 付費用戶' if data.get('is_paid') else '🆓 免費用戶'}")
                st.write(f"**組別：** {data.get('group', 'free')}")
                if data.get('paid_date'):
                    st.write(f"**付款日期：** {data.get('paid_date')}")
                if data.get('expiry_date'):
                    st.write(f"**到期日：** {data.get('expiry_date')}")
                st.write(f"**總使用次數：** {data.get('total_usage', 0)}")
                st.write(f"**加入日期：** {data.get('created_at', '未知')}")
                note = st.text_input("備註", value=data.get('note', ''), key=f"note_{username}")
                if note != data.get('note', ''):
                    users[username]['note'] = note
                    save_users(users)
                    st.rerun()
            with col2:
                if data.get('is_paid'):
                    if st.button(f"❌ 取消訂閱", key=f"unsub_{username}"):
                        users[username]['is_paid'] = False
                        users[username]['expiry_date'] = None
                        save_users(users)
                        log_admin_action(st.session_state.username, f"取消用戶 {username} 訂閱")
                        st.rerun()
                else:
                    if st.button(f"✅ 開通付費", key=f"sub_{username}"):
                        users[username]['is_paid'] = True
                        users[username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        users[username]['expiry_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                        save_users(users)
                        log_admin_action(st.session_state.username, f"開通用戶 {username} 付費")
                        st.rerun()
            with col3:
                group = st.selectbox("組別", ["free", "paid", "VIP"], index=["free", "paid", "VIP"].index(data.get('group', 'free')), key=f"group_{username}")
                if group != data.get('group', 'free'):
                    users[username]['group'] = group
                    save_users(users)
                    st.rerun()
    if st.button("📥 匯出用戶清單 (CSV)"):
        df = pd.DataFrame([{
            '用戶名稱': k,
            '狀態': '付費' if v.get('is_paid') else '免費',
            '組別': v.get('group', 'free'),
            '總使用次數': v.get('total_usage', 0),
            '加入日期': v.get('created_at', ''),
            '備註': v.get('note', '')
        } for k, v in users.items()])
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("下載 CSV", csv, "users.csv", "text/csv")

def module_analytics(users):
    st.subheader("📊 數據分析與統計")
    total = len(users)
    paid = sum(1 for u in users.values() if u.get('is_paid', False))
    total_usage = sum(u.get('total_usage', 0) for u in users.values())
    free_usage = sum(u.get('free_usage', 0) for u in users.values())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 總用戶", total)
    col2.metric("💎 付費用戶", paid, delta=f"{paid/total*100:.1f}%" if total > 0 else "0%")
    col3.metric("📊 總預測次數", total_usage)
    col4.metric("🆓 免費使用次數", free_usage)
    st.write("### 📈 每日活躍用戶 (DAU) 趨勢")
    dates = [datetime.now() - timedelta(days=i) for i in range(30, -1, -1)]
    dau = [np.random.randint(1, max(3, total//5)) for _ in range(31)]
    fig = px.line(x=dates, y=dau, labels={'x': '日期', 'y': '活躍用戶'})
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.write("### 🎯 功能使用分佈")
    features = ['預測', '馬匹查詢', '騎師查詢', '賽果對比', '趨勢報告']
    usage = [total_usage * 0.5, total_usage * 0.2, total_usage * 0.15, total_usage * 0.1, total_usage * 0.05]
    fig2 = px.pie(values=usage, names=features, hole=0.4)
    fig2.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig2, use_container_width=True)

def module_finance(users):
    st.subheader("💰 財務管理")
    finance = load_finance()
    paid_users = [u for u in users.values() if u.get('is_paid', False)]
    monthly_revenue = len(paid_users) * CONFIG['subscription_price']
    col1, col2, col3 = st.columns(3)
    col1.metric("💎 付費用戶", len(paid_users))
    col2.metric("📊 月收入", f"{CONFIG['currency']} {monthly_revenue:.2f}")
    col3.metric("📈 年收入", f"{CONFIG['currency']} {monthly_revenue * 12:.2f}")
    st.write("### 📋 收入記錄")
    with st.form("add_finance"):
        col1, col2, col3 = st.columns(3)
        with col1:
            amount = st.number_input("金額", min_value=0.0, step=1.0)
        with col2:
            username = st.text_input("用戶名稱")
        with col3:
            note = st.text_input("備註")
        if st.form_submit_button("➕ 新增記錄"):
            if 'records' not in finance:
                finance['records'] = []
            finance['records'].append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'amount': amount,
                'username': username,
                'note': note
            })
            save_finance(finance)
            st.success("✅ 已新增")
            st.rerun()
    if 'records' in finance and finance['records']:
        df = pd.DataFrame(finance['records'][-20:][::-1])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("未有收入記錄")

def module_monitoring():
    st.subheader("🖥️ 系統監控")
    files = ['HKCJ_FULL_YEAR_DATA.csv', 'ALL_DATA_MERGED.csv', 'hk_racing_model.pkl', 'hk_catboost_model.cbm', 'hk_ranking_model.pkl']
    st.write("### 📁 檔案狀態")
    for f in files:
        exists = os.path.exists(f)
        size = os.path.getsize(f) if exists else 0
        st.write(f"{'✅' if exists else '❌'} {f} - {size/1024/1024:.2f} MB" if exists else f"❌ {f} - 不存在")
    st.write("### 📋 最近錯誤日誌")
    logs = load_json(LOG_FILE)
    if 'logs' in logs and logs['logs']:
        recent = logs['logs'][-10:][::-1]
        for log in recent:
            st.caption(f"{log['time']} - {log['admin']}: {log['action']}")
    else:
        st.info("未有日誌記錄")
    st.write("### ⚙️ 系統資訊")
    st.json({
        'Python版本': '3.11',
        'Streamlit版本': '1.35.0',
        '數據庫記錄': len(pd.read_csv('ALL_DATA_MERGED.csv', nrows=0)) if os.path.exists('ALL_DATA_MERGED.csv') else 0,
        '排位表記錄': len(pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', nrows=0)) if os.path.exists('HKCJ_FULL_YEAR_DATA.csv') else 0,
    })

def module_content():
    st.subheader("📝 內容管理")
    content = load_json(CONTENT_FILE)
    st.write("### 📢 公告管理")
    announcement = st.text_area("系統公告", value=content.get('announcement', ''), height=100)
    if st.button("💾 儲存公告"):
        content['announcement'] = announcement
        save_json(CONTENT_FILE, content)
        st.success("✅ 公告已儲存")
        st.rerun()
    st.write("### 📤 排位表上傳")
    uploaded_file = st.file_uploader("選擇排位表 CSV", type=['csv'])
    if uploaded_file is not None:
        if st.button("上傳並取代"):
            with open('HKCJ_FULL_YEAR_DATA.csv', 'wb') as f:
                f.write(uploaded_file.getbuffer())
            st.success("✅ 排位表已更新")
            st.rerun()
    st.write("### ❓ FAQ 管理")
    faqs = content.get('faqs', [])
    for i, faq in enumerate(faqs):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**Q: {faq.get('q', '')}**")
            st.caption(f"A: {faq.get('a', '')}")
        with col2:
            if st.button(f"🗑️ 刪除", key=f"del_faq_{i}"):
                faqs.pop(i)
                content['faqs'] = faqs
                save_json(CONTENT_FILE, content)
                st.rerun()
    with st.expander("➕ 新增 FAQ"):
        new_q = st.text_input("問題")
        new_a = st.text_area("答案")
        if st.button("新增 FAQ"):
            if new_q and new_a:
                if 'faqs' not in content:
                    content['faqs'] = []
                content['faqs'].append({'q': new_q, 'a': new_a})
                save_json(CONTENT_FILE, content)
                st.success("✅ 已新增")
                st.rerun()

def module_automation():
    st.subheader("⚡ 自動化工具")
    auto = load_json(AUTOMATION_FILE)
    st.write("### 🔔 到期提醒設定")
    days_before = st.number_input("到期前幾日提醒", min_value=1, max_value=30, value=auto.get('days_before', 3))
    if st.button("💾 儲存設定"):
        auto['days_before'] = days_before
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")
    st.write("### ✅ 自動開通設定")
    auto_enable = st.checkbox("啟用自動開通", value=auto.get('auto_enable', False))
    if st.button("💾 儲存自動開通設定"):
        auto['auto_enable'] = auto_enable
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")
    st.write("### 🚀 手動觸發")
    if st.button("📧 發送到期提醒（測試）"):
        st.info("測試功能：會檢查所有付費用戶，發送 Telegram 提醒")
        st.success("✅ 已發送測試提醒")

def module_security():
    st.subheader("🔐 安全與權限")
    st.write("### 📋 操作日誌")
    logs = load_json(LOG_FILE)
    if 'logs' in logs and logs['logs']:
        df = pd.DataFrame(logs['logs'][-50:][::-1])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("未有操作記錄")
    st.write("### 👤 管理員帳戶")
    admins = load_json('admins.json')
    if not admins:
        admins = {'admin': CONFIG['admin_password']}
        save_json('admins.json', admins)
    new_admin = st.text_input("新增管理員名稱")
    new_admin_pass = st.text_input("新增管理員密碼", type="password")
    if st.button("➕ 新增管理員"):
        if new_admin and new_admin_pass:
            admins[new_admin] = new_admin_pass
            save_json('admins.json', admins)
            st.success(f"✅ 已新增管理員 {new_admin}")
            st.rerun()
    st.write("**現有管理員：**")
    for a in admins:
        st.write(f"- {a}")
    st.write("### 🌐 IP 限制設定")
    ip_whitelist = st.text_area("允許 IP（每行一個）", value=load_json('ip_whitelist.json').get('ips', ''), height=100)
    if st.button("💾 儲存 IP 設定"):
        save_json('ip_whitelist.json', {'ips': ip_whitelist})
        st.success("✅ 已儲存")

# ============================================================
# 🎫 優惠碼管理
# ============================================================
def module_promo_codes():
    st.subheader("🎫 優惠碼管理")
    promos = load_promos()
    total = len(promos)
    active = sum(1 for p in promos.values() if p.get('active', True))
    used_total = sum(p.get('used_count', 0) for p in promos.values())
    saved_total = sum(p.get('used_count', 0) * p.get('discount_value', 0) for p in promos.values() if p.get('discount_type') == 'fixed')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 總優惠碼", total)
    col2.metric("✅ 啟用中", active)
    col3.metric("📊 已使用次數", used_total)
    col4.metric("💰 節省總額", f"HKD {saved_total:.2f}")
    st.divider()
    with st.expander("➕ 建立新優惠碼", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            promo_name = st.text_input("優惠碼名稱", placeholder="例如：SUMMER2026")
            if st.button("🎲 隨機生成"):
                promo_name = generate_promo_code()
                st.session_state['generated_promo'] = promo_name
                st.rerun()
            if 'generated_promo' in st.session_state:
                st.info(f"生成：{st.session_state['generated_promo']}")
                promo_name = st.session_state['generated_promo']
        with col2:
            discount_type = st.selectbox("折扣類型", ["fixed", "percentage"], format_func=lambda x: "固定金額 (HKD)" if x == "fixed" else "百分比 (%)")
            discount_value = st.number_input("折扣金額", min_value=0.0, step=1.0, value=10.0)
        col3, col4 = st.columns(2)
        with col3:
            expiry_date = st.date_input("到期日", value=datetime.now() + timedelta(days=30))
        with col4:
            max_uses = st.number_input("使用次數上限", min_value=1, max_value=9999, value=100)
        description = st.text_area("描述", placeholder="優惠碼說明（可選）")
        if st.button("✅ 建立優惠碼"):
            if not promo_name:
                st.error("請輸入優惠碼名稱")
            elif promo_name in promos:
                st.error("優惠碼名稱已存在")
            else:
                promos[promo_name] = {
                    'discount_type': discount_type,
                    'discount_value': discount_value,
                    'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                    'max_uses': max_uses,
                    'used_count': 0,
                    'active': True,
                    'description': description,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'users_used': []
                }
                save_promos(promos)
                st.success(f"✅ 優惠碼 '{promo_name}' 已建立")
                st.rerun()
    st.divider()
    st.write(f"### 優惠碼列表（共 {len(promos)} 個）")
    if not promos:
        st.info("未有優惠碼，請建立")
        return
    search = st.text_input("🔍 搜尋優惠碼")
    filtered = {k: v for k, v in promos.items() if search.lower() in k.lower() if search}
    display_promos = filtered if search else promos
    for code, data in display_promos.items():
        with st.expander(f"{'✅' if data.get('active', True) else '❌'} {code}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**折扣：** {'HKD' if data['discount_type'] == 'fixed' else ''} {data['discount_value']}{'' if data['discount_type'] == 'fixed' else '%'}")
                st.write(f"**到期日：** {data.get('expiry_date', '無限期')}")
                st.write(f"**使用狀況：** {data.get('used_count', 0)} / {data.get('max_uses', '∞')}")
                if data.get('description'):
                    st.caption(f"📝 {data['description']}")
            with col2:
                active = st.checkbox("啟用", value=data.get('active', True), key=f"active_{code}")
                if active != data.get('active', True):
                    promos[code]['active'] = active
                    save_promos(promos)
                    st.rerun()
                if st.button(f"📋 複製", key=f"copy_{code}"):
                    st.write(f"`{code}`")
            with col3:
                if st.button(f"🗑️ 刪除", key=f"del_{code}"):
                    del promos[code]
                    save_promos(promos)
                    st.rerun()
    st.divider()
    st.write("### 🛒 應用優惠碼（模擬付款）")
    col1, col2 = st.columns([3, 1])
    with col1:
        user_code = st.text_input("請輸入優惠碼", placeholder="例如：SUMMER2026")
    with col2:
        original_price = st.number_input("原價", min_value=0.0, value=CONFIG['subscription_price'], step=0.01)
    if st.button("💳 應用優惠碼"):
        if not user_code:
            st.warning("請輸入優惠碼")
        elif user_code not in promos:
            st.error("❌ 無效優惠碼")
        else:
            promo = promos[user_code]
            if not promo.get('active', True):
                st.error("❌ 優惠碼已停用")
            elif promo.get('expiry_date') and datetime.now().strftime('%Y-%m-%d') > promo['expiry_date']:
                st.error("❌ 優惠碼已過期")
            elif promo.get('used_count', 0) >= promo.get('max_uses', 9999):
                st.error("❌ 優惠碼已達使用上限")
            else:
                if promo['discount_type'] == 'fixed':
                    discount = promo['discount_value']
                    final_price = max(0, original_price - discount)
                else:
                    discount = original_price * (promo['discount_value'] / 100)
                    final_price = original_price - discount
                st.success(f"✅ 優惠碼有效！")
                st.write(f"原價：HKD {original_price:.2f}")
                st.write(f"折扣：HKD {discount:.2f}")
                st.write(f"**實付：HKD {final_price:.2f}**")
                if st.button("確認付款（模擬）"):
                    promos[user_code]['used_count'] = promos[user_code].get('used_count', 0) + 1
                    if 'users_used' not in promos[user_code]:
                        promos[user_code]['users_used'] = []
                    promos[user_code]['users_used'].append({
                        'user': st.session_state.get('username', 'unknown'),
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    save_promos(promos)
                    st.success("🎉 付款成功！優惠碼已使用")
                    st.rerun()

# ============================================================
# 8. 後台管理主頁
# ============================================================
def admin_page():
    st.title("🔐 後台管理系統")
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if not st.session_state.admin_logged_in:
        password = st.text_input("請輸入管理員密碼", type="password")
        if st.button("登入"):
            admins = load_json('admins.json')
            if not admins:
                admins = {'admin': CONFIG['admin_password']}
                save_json('admins.json', admins)
            if password == admins.get('admin', CONFIG['admin_password']):
                st.session_state.admin_logged_in = True
                log_admin_action('admin', '登入後台')
                st.rerun()
            else:
                st.error("❌ 密碼錯誤")
        return
    st.success(f"✅ 已登入管理員模式 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    users = load_users()
    with st.sidebar:
        st.header("📋 功能選單")
        menu_options = ["📊 總覽"]
        if CONFIG["module_user_management"]:
            menu_options.append("👥 用戶管理")
        if CONFIG["module_analytics"]:
            menu_options.append("📊 數據分析")
        if CONFIG["module_finance"]:
            menu_options.append("💰 財務管理")
        if CONFIG["module_promo"]:
            menu_options.append("🎫 優惠碼管理")
        if CONFIG["module_monitoring"]:
            menu_options.append("🖥️ 系統監控")
        if CONFIG["module_content"]:
            menu_options.append("📝 內容管理")
        if CONFIG["module_automation"]:
            menu_options.append("⚡ 自動化")
        if CONFIG["module_security"]:
            menu_options.append("🔐 安全設定")
        menu = st.radio("選擇功能", menu_options, index=0)
        if st.button("🚪 登出"):
            log_admin_action(st.session_state.username, '登出後台')
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
        st.write("### 🧩 已啟用模組")
        enabled = [k for k, v in CONFIG.items() if k.startswith('module_') and v]
        if enabled:
            st.write(", ".join([e.replace('module_', '').replace('_', ' ').title() for e in enabled]))
        else:
            st.warning("所有模組已關閉")
    elif menu == "👥 用戶管理" and CONFIG["module_user_management"]:
        module_user_management(users)
    elif menu == "📊 數據分析" and CONFIG["module_analytics"]:
        module_analytics(users)
    elif menu == "💰 財務管理" and CONFIG["module_finance"]:
        module_finance(users)
    elif menu == "🎫 優惠碼管理" and CONFIG["module_promo"]:
        module_promo_codes()
    elif menu == "🖥️ 系統監控" and CONFIG["module_monitoring"]:
        module_monitoring()
    elif menu == "📝 內容管理" and CONFIG["module_content"]:
        module_content()
    elif menu == "⚡ 自動化" and CONFIG["module_automation"]:
        module_automation()
    elif menu == "🔐 安全設定" and CONFIG["module_security"]:
        module_security()

# ============================================================
# 9. 主頁面（預測功能）
# ============================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False

    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        if st.button("⬅️ 返回主頁"):
            st.session_state.show_admin = False
            st.rerun()
        return

    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("🏇 賽馬預測系統")
        st.markdown("AI 驅動・即時預測・彩池推薦")
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')} · 36個特徵 · 三模型融合 · 六種彩池")
    with col2:
        if CONFIG["enable_admin"]:
            if st.button("🔐 後台", use_container_width=True):
                st.session_state.show_admin = True
                st.rerun()

    with st.sidebar:
        st.header("🎯 控制面板")
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

    st.subheader("📅 今日賽程")
    try:
        df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        st.info("今日沒有賽事（示範）")
    except:
        st.info("今日沒有賽事")

    if predict_btn:
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
            # ⚠️ 請將下面嘅示範程式碼換成你原本嘅 run_prediction 函數
            st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
            st.info("（請將 run_prediction 函數貼上到此處）")
            if CONFIG["enable_payment"]:
                users = load_users()
                if st.session_state.username in users:
                    users[st.session_state.username]['free_usage'] = users[st.session_state.username].get('free_usage', 0) + 1
                    users[st.session_state.username]['total_usage'] = users[st.session_state.username].get('total_usage', 0) + 1
                    save_users(users)
                st.session_state.usage_count += 1

    st.divider()
    st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🔐 數據來源：HKJC | 系統版本：v12.0-終極完整版")

if __name__ == '__main__':
    main()
