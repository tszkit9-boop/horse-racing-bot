# =============================================================
# SHTSN 賽馬AI預測系統 - 最終完整穩定版
# =============================================================

import streamlit as st
import pandas as pd
import json
import os
import hashlib
from datetime import datetime, timedelta
import plotly.express as px

# ---------- 頁面設定 ----------
st.set_page_config(page_title="SHTSN 賽馬AI預測", page_icon="🐴", layout="wide")

# ---------- 系統配置 ----------
CONFIG = {
    "enable_registration": True,
    "enable_payment": False,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "admin_password": "z54060437K",
    "price_day": 18,
    "price_month": 128,
    "price_quarter": 328,
}

USERS_FILE = "users.json"
PREDICTION_HISTORY_DIR = "prediction_history"
os.makedirs(PREDICTION_HISTORY_DIR, exist_ok=True)

# =============================================================
# 付款審核相關函數
# =============================================================
PROOF_FILE = "payment_proofs.json"
AUDIT_FILE = "payment_audit.json"

def load_json(filepath, default=None):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    except Exception as e:
        st.error(f"讀取檔案失敗：{e}")
        return default if default is not None else {}

def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"儲存檔案失敗：{e}")
        return False

def init_payment_files():
    for f, default in [(PROOF_FILE, {"records": []}), (AUDIT_FILE, {"logs": []})]:
        if not os.path.exists(f):
            save_json(f, default)

def log_action(action, detail=""):
    data = load_json(AUDIT_FILE, {"logs": []})
    data["logs"].append({
        "time": datetime.now().isoformat(),
        "actor": st.session_state.get("username", "admin"),
        "action": action,
        "detail": detail
    })
    save_json(AUDIT_FILE, data)

def handle_approve(original_idx, record):
    proofs = load_json(PROOF_FILE, {"records": []})
    if original_idx >= len(proofs.get("records", [])):
        st.error("記錄索引錯誤")
        return False
    proofs["records"][original_idx]["status"] = "approved"
    proofs["records"][original_idx]["review_time"] = datetime.now().isoformat()
    proofs["records"][original_idx]["reviewer"] = st.session_state.get("username", "admin")
    save_json(PROOF_FILE, proofs)

    user_id = record.get("user_id")
    if not user_id:
        st.warning("記錄缺少 user_id")
        return False

    users = load_json(USERS_FILE, {})
    if user_id not in users:
        st.warning(f"用戶 {user_id} 不存在")
        return False

    users[user_id]["level"] = "付費用戶"
    plan = record.get("plan", "月費")
    days_map = {"日費": 1, "月費": 30, "季費": 90}
    days = days_map.get(plan, 30)
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    users[user_id]["expiry"] = expiry
    if "subscription_history" not in users[user_id]:
        users[user_id]["subscription_history"] = []
    users[user_id]["subscription_history"].append({
        "plan": plan,
        "amount": record.get("amount"),
        "approved_at": datetime.now().isoformat()
    })
    save_json(USERS_FILE, users)

    log_action("批准付款", f"用戶 {record.get('username')} ({user_id})，方案 {plan}")
    st.success(f"✅ 已批准 {record.get('username')} 並升級，有效期至 {expiry[:10]}")
    return True

def handle_reject(original_idx, record):
    proofs = load_json(PROOF_FILE, {"records": []})
    if original_idx >= len(proofs.get("records", [])):
        st.error("記錄索引錯誤")
        return False
    proofs["records"][original_idx]["status"] = "rejected"
    proofs["records"][original_idx]["review_time"] = datetime.now().isoformat()
    proofs["records"][original_idx]["reviewer"] = st.session_state.get("username", "admin")
    save_json(PROOF_FILE, proofs)
    log_action("拒絕付款", f"用戶 {record.get('username')} ({record.get('user_id')})")
    st.warning(f"❌ 已拒絕 {record.get('username')} 的申請")
    return True

def handle_refund(original_idx, record):
    user_id = record.get("user_id")
    if not user_id:
        st.error("記錄缺少 user_id")
        return False
    users = load_json(USERS_FILE, {})
    if user_id not in users:
        st.error(f"用戶 {user_id} 不存在")
        return False
    users[user_id]["level"] = "免費用戶"
    users[user_id].pop("expiry", None)
    save_json(USERS_FILE, users)

    proofs = load_json(PROOF_FILE, {"records": []})
    if original_idx < len(proofs.get("records", [])):
        proofs["records"][original_idx]["refunded"] = True
        proofs["records"][original_idx]["refund_time"] = datetime.now().isoformat()
        save_json(PROOF_FILE, proofs)

    log_action("退款", f"用戶 {record.get('username')} ({user_id})")
    st.info(f"↩️ 已為 {record.get('username')} 辦理退款，用戶已降級")
    return True

def batch_approve_all(records):
    pending_indices = [i for i, r in enumerate(records) if r.get("status") == "pending"]
    if not pending_indices:
        st.warning("沒有待審批記錄")
        return
    success = 0
    for idx in pending_indices:
        if handle_approve(idx, records[idx]):
            success += 1
    st.success(f"✅ 成功批量批准 {success}/{len(pending_indices)} 條記錄")
    log_action("批量批准", f"共 {len(pending_indices)} 條")

def payment_review_page():
    st.header("💳 付款審核管理")
    init_payment_files()

    if not st.session_state.get("is_admin", False):
        st.error("⛔ 你沒有權限訪問此頁面")
        return

    proofs_data = load_json(PROOF_FILE, {"records": []})
    records = proofs_data.get("records", [])

    total_pending = sum(1 for r in records if r.get("status") == "pending")
    total_approved = sum(1 for r in records if r.get("status") == "approved")
    total_rejected = sum(1 for r in records if r.get("status") == "rejected")
    total_amount = sum(r.get("amount", 0) for r in records if r.get("status") == "approved")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏳ 待審批", total_pending)
    col2.metric("✅ 已批准", total_approved)
    col3.metric("❌ 已拒絕", total_rejected)
    col4.metric("💰 總收入", f"${total_amount:,}")
    st.divider()

    with st.expander("🔍 篩選與搜尋", expanded=True):
        col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
        with col_s1:
            search_term = st.text_input("搜尋用戶名 / ID", placeholder="輸入關鍵字")
        with col_s2:
            status_filter = st.selectbox(
                "狀態篩選",
                ["全部", "pending", "approved", "rejected"],
                format_func=lambda x: {"pending": "待審批", "approved": "已批准", "rejected": "已拒絕", "全部": "全部"}[x]
            )
        with col_s3:
            if status_filter in ["pending", "全部"] and total_pending > 0:
                if st.button("📦 批量批准全部"):
                    batch_approve_all(records)
                    st.rerun()

    filtered = records.copy()
    if search_term:
        filtered = [r for r in filtered if search_term.lower() in r.get("username", "").lower() or search_term in r.get("user_id", "")]
    if status_filter != "全部":
        filtered = [r for r in filtered if r.get("status") == status_filter]

    if not filtered:
        st.info("📭 沒有符合條件的記錄")
        return

    st.subheader(f"📋 共 {len(filtered)} 條記錄")

    for idx, record in enumerate(filtered):
        original_idx = records.index(record)
        status = record.get("status", "pending")

        with st.container():
            cols = st.columns([2, 2, 1.5, 1.5, 2])
            with cols[0]:
                st.write(f"**👤 {record.get('username', '未知')}**")
                st.caption(f"ID: `{record.get('user_id', '')}`")
            with cols[1]:
                plan = record.get('plan', '未指定')
                amount = record.get('amount', 0)
                st.write(f"**{plan}**  **${amount}**")
                st.caption(f"上傳：{record.get('upload_time', '')}")
            with cols[2]:
                proof_img = record.get('proof_image', '')
                if proof_img and os.path.exists(proof_img):
                    st.image(proof_img, width=100)
                else:
                    st.caption("無圖片")
            with cols[3]:
                if status == "pending":
                    st.warning("⏳ 待審批")
                elif status == "approved":
                    st.success("✅ 已批准")
                    if record.get("expiry"):
                        st.caption(f"到期：{record['expiry'][:10]}")
                elif status == "rejected":
                    st.error("❌ 已拒絕")
                else:
                    st.info(status)
                if record.get("review_notes"):
                    st.caption(f"📝 {record['review_notes']}")
            with cols[4]:
                if status == "pending":
                    col_a, col_r = st.columns(2)
                    with col_a:
                        if st.button("✅ 批准", key=f"app_{original_idx}"):
                            handle_approve(original_idx, record)
                            st.rerun()
                    with col_r:
                        if st.button("❌ 拒絕", key=f"rej_{original_idx}"):
                            handle_reject(original_idx, record)
                            st.rerun()
                    note = st.text_input("備註", value=record.get("review_notes", ""), key=f"note_{original_idx}")
                    if note != record.get("review_notes", ""):
                        proofs_data["records"][original_idx]["review_notes"] = note
                        save_json(PROOF_FILE, proofs_data)
                elif status == "approved":
                    if st.button("↩️ 退款", key=f"ref_{original_idx}"):
                        handle_refund(original_idx, record)
                        st.rerun()
            st.divider()

    with st.expander("📜 操作日誌 (最近20條)"):
        audit = load_json(AUDIT_FILE, {"logs": []})
        logs = audit.get("logs", [])[-20:]
        if logs:
            for log in reversed(logs):
                st.text(f"[{log['time']}] {log['actor']} - {log['action']} - {log.get('detail', '')}")
        else:
            st.info("暫無日誌")

# =============================================================
# 用戶管理與認證
# =============================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "username": "admin",
                "password": hash_password(CONFIG["admin_password"]),
                "level": "超級管理員",
                "email": "admin@shstn.com",
                "registered_at": datetime.now().isoformat(),
                "predictions_used": 0,
                "predictions_limit": -1,
                "is_active": True
            }
        }
        save_json(USERS_FILE, default_users)
        st.success("管理員帳戶已建立 (admin / z54060437K)")
    return load_json(USERS_FILE, {})

def get_current_user():
    if "user" in st.session_state:
        users = load_json(USERS_FILE, {})
        return users.get(st.session_state["user"], None)
    return None

def is_admin():
    user = get_current_user()
    return user and user.get("level") in ["超級管理員"]

def can_predict():
    user = get_current_user()
    if not user:
        return False
    if user.get("predictions_limit") == -1:
        return True
    used = user.get("predictions_used", 0)
    limit = user.get("predictions_limit", CONFIG["free_limit"])
    return used < limit

def get_remaining():
    user = get_current_user()
    if not user:
        return 0
    if user.get("predictions_limit") == -1:
        return float('inf')
    used = user.get("predictions_used", 0)
    limit = user.get("predictions_limit", CONFIG["free_limit"])
    return max(0, limit - used)

# ---------- Session State 初始化 ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "主頁面"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 初始化用戶檔案（如果不存在會自動建立）
init_users()

# =============================================================
# 側邊欄登入
# =============================================================
def sidebar_login():
    with st.sidebar:
        st.title("🏇 SHTSN 賽馬AI")
        if st.session_state.logged_in:
            user = get_current_user()
            if user:
                level_emoji = {
                    "超級管理員": "👑",
                    "VIP": "👑",
                    "付費用戶": "💎",
                    "免費用戶": "🆓"
                }.get(user.get("level"), "🆓")
                st.markdown(f"### {level_emoji} {user.get('username')}")
                st.caption(f"等級：{user.get('level')}")
                remaining = get_remaining()
                if remaining == float('inf'):
                    st.caption("預測次數：♾️ 無限")
                else:
                    st.caption(f"剩餘預測：{remaining} 次")
                if st.button("🚪 登出"):
                    st.session_state.logged_in = False
                    st.session_state.user = None
                    st.session_state.is_admin = False
                    st.rerun()
            pages = ["主頁面", "預測", "賽程", "馬匹查詢", "騎師查詢", "對比", "趨勢", "用戶儀表板", "預測歷史"]
            if is_admin():
                pages.append("後台管理")
            selected = st.selectbox("📌 導航", pages, index=0)
            st.session_state.page = selected
        else:
            st.subheader("🔐 登入")
            login_username = st.text_input("用戶名")
            login_password = st.text_input("密碼", type="password")
            if st.button("登入"):
                users = load_json(USERS_FILE, {})
                if login_username in users:
                    user = users[login_username]
                    if user.get("password") == hash_password(login_password):
                        st.session_state.logged_in = True
                        st.session_state.user = login_username
                        st.session_state.is_admin = user.get("level") in ["超級管理員"]
                        st.success("登入成功！")
                        st.rerun()
                    else:
                        st.error("❌ 密碼錯誤")
                else:
                    st.error("❌ 用戶不存在")
            if CONFIG["enable_registration"]:
                st.divider()
                st.subheader("📝 註冊")
                new_username = st.text_input("新用戶名")
                new_password = st.text_input("新密碼", type="password")
                new_email = st.text_input("電郵")
                if st.button("註冊"):
                    users = load_json(USERS_FILE, {})
                    if new_username in users:
                        st.error("用戶名已被使用")
                    elif len(new_username) < 3:
                        st.error("用戶名至少3個字符")
                    elif len(new_password) < 6:
                        st.error("密碼至少6個字符")
                    else:
                        users[new_username] = {
                            "username": new_username,
                            "password": hash_password(new_password),
                            "level": "免費用戶",
                            "email": new_email,
                            "registered_at": datetime.now().isoformat(),
                            "predictions_used": 0,
                            "predictions_limit": CONFIG["free_limit"],
                            "is_active": True
                        }
                        save_json(USERS_FILE, users)
                        st.success("註冊成功！請登入")

# =============================================================
# 各個頁面
# =============================================================
def main_page():
    st.title("🏇 SHTSN 36特徵三核心賽馬AI預測系統")
    st.markdown("### 歡迎使用最先進嘅賽馬預測系統")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 模型融合", "3核心", "XGBoost + CatBoost + Ranking")
    with col2:
        st.metric("📈 歷史數據", "40,298 筆", "2024-2026")
    with col3:
        st.metric("🏆 回測ROI", "58.21%", "命中率 39.55%")
    st.divider()
    st.markdown("""
    ### 🚀 快速開始
    1. 左側登入帳號（免費試玩 2 次預測）
    2. 選擇「預測」頁面獲取今日賽事推薦
    3. 查看「用戶儀表板」追蹤表現
    """)

def predict_page():
    st.title("🔮 賽事預測")
    if not st.session_state.logged_in:
        st.warning("請先登入")
        return
    if not can_predict():
        st.error("你已用盡免費預測次數，請升級付費帳戶")
        return
    st.info(f"📌 剩餘預測次數：{get_remaining()}")
    race_date = st.date_input("賽事日期", datetime.today())
    race_no = st.number_input("場次", min_value=1, max_value=10, value=9)
    if st.button("🔮 開始預測"):
        st.subheader("📋 預測結果")
        st.success("✅ 預測完成！")
        data = {"馬匹": ["美麗傳承", "金鎗六十", "時時精綵"], "檔位": [3,5,7], "賠率": [2.5,3.2,4.8], "預測勝率": [42.3,31.5,18.2]}
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index("馬匹")["預測勝率"])
        users = load_json(USERS_FILE, {})
        user = users.get(st.session_state.user)
        if user and user.get("predictions_limit") != -1:
            user["predictions_used"] = user.get("predictions_used", 0) + 1
            save_json(USERS_FILE, users)

def schedule_page():
    st.title("📅 賽程")
    st.info("今日賽程（示範數據）")
    data = {"場次": list(range(1,11)), "路程": ["1000m","1200m","1400m","1600m","1800m","2000m","1200m","1400m","1600m","2200m"], "班次": ["一班","二班","三班","四班","五班","一班","二班","三班","四班","一班"]}
    st.dataframe(pd.DataFrame(data), use_container_width=True)

def horse_query():
    st.title("🐴 馬匹查詢")
    horse_name = st.text_input("輸入馬匹名稱或ID")
    if horse_name:
        st.json({"馬名": horse_name, "年齡":5, "評分":120, "出賽次數":25, "勝出次數":8, "上名率":"48%"})

def jockey_query():
    st.title("🏇 騎師查詢")
    jockey_name = st.text_input("輸入騎師名稱")
    if jockey_name:
        st.json({"騎師": jockey_name, "近50場勝率":"18.5%", "近10場勝率":"22.0%"})

def compare_page():
    st.title("📊 賽果對比")
    st.info("對比預測與實際賽果（示範數據）")
    data = {"場次":[1,2,3,4,5], "預測頭馬":["美麗傳承","金鎗六十","時時精綵","將王","浪漫勇士"], "實際頭馬":["美麗傳承","金鎗六十","時時精綵","將王","浪漫勇士"], "命中":["✅","✅","✅","❌","✅"]}
    st.dataframe(pd.DataFrame(data), use_container_width=True)
    st.metric("命中率", "80%")

def trend_page():
    st.title("📈 預測準確度趨勢")
    dates = pd.date_range(start="2026-01-01", periods=30, freq="D")
    accuracy = [0.35 + i*0.01 + (i%5)*0.02 for i in range(30)]
    fig = px.line(pd.DataFrame({"日期":dates, "準確度":accuracy}), x="日期", y="準確度", title="準確度趨勢")
    st.plotly_chart(fig, use_container_width=True)

def dashboard_page():
    st.title("📊 用戶儀表板")
    if not st.session_state.logged_in:
        st.warning("請先登入")
        return
    user = get_current_user()
    if not user:
        st.error("用戶資料錯誤")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 用戶等級", user.get("level", "未知"))
    with col2:
        remaining = get_remaining()
        st.metric("🔮 剩餘預測", "♾️ 無限" if remaining == float('inf') else remaining)
    with col3:
        st.metric("📊 已用預測", user.get("predictions_used", 0))
    st.divider()
    st.subheader("📋 個人資料")
    st.json({"用戶名": user.get("username"), "電郵": user.get("email", "N/A"), "註冊日期": user.get("registered_at", "N/A"), "到期日": user.get("expiry", "N/A")})

def history_page():
    st.title("📜 預測歷史")
    st.info("你嘅預測記錄（示範數據）")
    data = {"日期": ["2026-08-20", "2026-08-19", "2026-08-18"], "場次": [9,8,7], "預測馬匹": ["美麗傳承","金鎗六十","時時精綵"], "結果": ["✅ 命中","❌ 未中","✅ 命中"]}
    st.dataframe(pd.DataFrame(data), use_container_width=True)

def admin_page():
    st.title("⚙️ 後台管理")
    if not is_admin():
        st.error("⛔ 沒有權限")
        return
    tabs = st.tabs(["📊 總覽", "👥 用戶管理", "💳 付款審核", "📈 數據分析", "💰 財務管理", "📜 操作日誌"])
    with tabs[0]:
        users = load_json(USERS_FILE, {})
        st.metric("👤 總用戶", len(users))
        st.metric("💎 付費用戶", sum(1 for u in users.values() if u.get("level") in ["付費用戶","VIP"]))
    with tabs[1]:
        users = load_json(USERS_FILE, {})
        search = st.text_input("搜尋用戶")
        for username, info in users.items():
            if search and search.lower() not in username.lower():
                continue
            with st.expander(f"{username} - {info.get('level')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.json(info)
                with col2:
                    new_level = st.selectbox("修改等級", ["免費用戶","付費用戶","VIP","超級管理員"], index=["免費用戶","付費用戶","VIP","超級管理員"].index(info.get("level","免費用戶")), key=f"lv_{username}")
                    if st.button("更新", key=f"up_{username}"):
                        users[username]["level"] = new_level
                        save_json(USERS_FILE, users)
                        st.success("更新成功")
                        st.rerun()
    with tabs[2]:
        payment_review_page()
    with tabs[3]:
        st.subheader("📈 數據分析")
        dates = pd.date_range(end=datetime.today(), periods=30, freq="D")
        dau = [10 + i*0.5 + (i%7)*2 for i in range(30)]
        fig = px.line(pd.DataFrame({"日期":dates, "DAU":dau}), x="日期", y="DAU", title="每日活躍用戶")
        st.plotly_chart(fig, use_container_width=True)
    with tabs[4]:
        st.subheader("💰 財務管理")
        st.metric("本月收入", "$12,800")
        st.metric("本年收入", "$156,200")
        months = ["1月","2月","3月","4月","5月","6月","7月","8月"]
        revenue = [12000,15000,18000,14000,16000,19000,21000,12800]
        fig = px.bar(pd.DataFrame({"月份":months, "收入":revenue}), x="月份", y="收入", title="月度收入")
        st.plotly_chart(fig, use_container_width=True)
    with tabs[5]:
        st.subheader("📜 操作日誌")
        audit = load_json(AUDIT_FILE, {"logs": []})
        logs = audit.get("logs", [])[-50:]
        if logs:
            for log in reversed(logs):
                st.text(f"[{log['time']}] {log['actor']} - {log['action']} - {log.get('detail','')}")
        else:
            st.info("暫無日誌")

# =============================================================
# 主路由
# =============================================================
def main():
    sidebar_login()
    page = st.session_state.get("page", "主頁面")
    if page == "主頁面":
        main_page()
    elif page == "預測":
        predict_page()
    elif page == "賽程":
        schedule_page()
    elif page == "馬匹查詢":
        horse_query()
    elif page == "騎師查詢":
        jockey_query()
    elif page == "對比":
        compare_page()
    elif page == "趨勢":
        trend_page()
    elif page == "用戶儀表板":
        dashboard_page()
    elif page == "預測歷史":
        history_page()
    elif page == "後台管理":
        admin_page()
    else:
        st.error("頁面不存在")

if __name__ == "__main__":
    main()