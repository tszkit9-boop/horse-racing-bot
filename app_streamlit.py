# =============================================================
# SHTSN 36特徵三核心賽馬AI預測系統 - Streamlit 網頁版
# 完整主程式 (整合付款審核模組)
# =============================================================

import streamlit as st
import pandas as pd
import json
import os
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# ---------- 引入自訂模組 ----------
# 付款審核模組 (獨立檔案 payment_admin.py)
try:
    import payment_admin
except ImportError:
    st.error("❌ 找不到 payment_admin.py，請確保該檔案存在於同一目錄")
    payment_admin = None

# ---------- 頁面設定 ----------
st.set_page_config(
    page_title="SHTSN 賽馬AI預測系統",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    "verification_expiry": 5,
    "module_user_management": True,
    "module_analytics": True,
    "module_finance": True,
    "module_monitoring": True,
    "module_content": True,
    "module_automation": True,
    "module_security": True,
    "module_promo": True,
}

# ---------- 檔案路徑 ----------
USERS_FILE = "users.json"
PREDICTION_HISTORY_DIR = "prediction_history"
os.makedirs(PREDICTION_HISTORY_DIR, exist_ok=True)

# ---------- 輔助函數 ----------
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
                "predictions_limit": -1,  # -1 表示無限
                "is_active": True
            }
        }
        save_json(USERS_FILE, default_users)
        return default_users
    return load_json(USERS_FILE, {})

def get_current_user():
    if "user" in st.session_state:
        users = load_json(USERS_FILE, {})
        return users.get(st.session_state["user"], None)
    return None

def is_admin():
    user = get_current_user()
    return user and user.get("level") in ["超級管理員"]

def is_vip():
    user = get_current_user()
    return user and user.get("level") in ["VIP", "付費用戶", "超級管理員"]

def can_predict():
    user = get_current_user()
    if not user:
        return False
    if user.get("predictions_limit") == -1:  # 無限
        return True
    used = user.get("predictions_used", 0)
    limit = user.get("predictions_limit", CONFIG["free_limit"])
    return used < limit

def get_remaining_predictions():
    user = get_current_user()
    if not user:
        return 0
    if user.get("predictions_limit") == -1:
        return float('inf')
    used = user.get("predictions_used", 0)
    limit = user.get("predictions_limit", CONFIG["free_limit"])
    return max(0, limit - used)

# ---------- 初始化 Session State ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "主頁面"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 確保用戶檔案存在
init_users()

# ---------- 側邊欄登入/用戶資訊 ----------
def sidebar_login():
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/horse.png", width=80)
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
                remaining = get_remaining_predictions()
                if remaining == float('inf'):
                    st.caption("預測次數：♾️ 無限")
                else:
                    st.caption(f"剩餘預測：{remaining} 次")
                if st.button("🚪 登出"):
                    st.session_state.logged_in = False
                    st.session_state.user = None
                    st.session_state.is_admin = False
                    st.rerun()
            # 導航
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
                        st.error("密碼錯誤")
                else:
                    st.error("用戶不存在")
            
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

# ---------- 頁面內容 ----------
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
    
    ### 📊 系統特色
    - 36個專業特徵（檔位、負磅、路程、騎師勝率等）
    - 三模型融合提升準確度
    - 支援獨贏、位置Q、三四重彩
    - 自動生成預測報告
    """)

def predict_page():
    st.title("🔮 賽事預測")
    if not st.session_state.logged_in:
        st.warning("請先登入")
        return
    if not can_predict():
        st.error("你已用盡免費預測次數，請升級付費帳戶")
        return
    
    st.info(f"📌 剩餘預測次數：{get_remaining_predictions()}")
    
    # 模擬預測（實際會調用預測核心）
    race_date = st.date_input("賽事日期", datetime.today())
    race_no = st.number_input("場次", min_value=1, max_value=10, value=9)
    
    if st.button("🔮 開始預測"):
        # 此處應調用 predict_race_card.py 的預測函數
        # 為示範，顯示模擬結果
        st.subheader("📋 預測結果")
        st.success("✅ 預測完成！")
        data = {
            "馬匹": ["美麗傳承", "金鎗六十", "時時精綵"],
            "檔位": [3, 5, 7],
            "賠率": [2.5, 3.2, 4.8],
            "評分": [128, 125, 121],
            "預測勝率": [42.3, 31.5, 18.2]
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index("馬匹")["預測勝率"])
        
        # 扣除預測次數
        users = load_json(USERS_FILE, {})
        user = users.get(st.session_state.user)
        if user and user.get("predictions_limit") != -1:
            user["predictions_used"] = user.get("predictions_used", 0) + 1
            save_json(USERS_FILE, users)
        st.caption("📝 提示：實際預測會使用36個特徵及三模型融合")

def schedule_page():
    st.title("📅 賽程")
    st.info("今日賽程（示範數據）")
    data = {
        "場次": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "路程": ["1000m", "1200m", "1400m", "1600m", "1800m", "2000m", "1200m", "1400m", "1600m", "2200m"],
        "班次": ["一班", "二班", "三班", "四班", "五班", "一班", "二班", "三班", "四班", "一班"],
        "開跑時間": ["12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"]
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

def horse_query():
    st.title("🐴 馬匹查詢")
    horse_name = st.text_input("輸入馬匹名稱或ID")
    if horse_name:
        st.info(f"查詢結果：{horse_name}（示範數據）")
        st.json({
            "馬名": horse_name,
            "年齡": 5,
            "評分": 120,
            "出賽次數": 25,
            "勝出次數": 8,
            "上名率": "48%",
            "最近成績": "1/2/3/4/5"
        })

def jockey_query():
    st.title("🏇 騎師查詢")
    jockey_name = st.text_input("輸入騎師名稱")
    if jockey_name:
        st.info(f"查詢結果：{jockey_name}（示範數據）")
        st.json({
            "騎師": jockey_name,
            "近50場勝率": "18.5%",
            "近10場勝率": "22.0%",
            "檔位勝率": "15.2%",
            "同程勝率": "20.1%"
        })

def compare_page():
    st.title("📊 賽果對比")
    st.info("對比預測與實際賽果（示範數據）")
    data = {
        "場次": [1, 2, 3, 4, 5],
        "預測頭馬": ["美麗傳承", "金鎗六十", "時時精綵", "將王", "浪漫勇士"],
        "實際頭馬": ["美麗傳承", "金鎗六十", "時時精綵", "將王", "浪漫勇士"],
        "命中": ["✅", "✅", "✅", "❌", "✅"]
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    st.metric("命中率", "80%")

def trend_page():
    st.title("📈 預測準確度趨勢")
    st.info("準確度趨勢報告（示範數據）")
    dates = pd.date_range(start="2026-01-01", periods=30, freq="D")
    accuracy = [0.35 + i*0.01 + (i%5)*0.02 for i in range(30)]
    df = pd.DataFrame({"日期": dates, "準確度": accuracy})
    fig = px.line(df, x="日期", y="準確度", title="準確度趨勢")
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
        remaining = get_remaining_predictions()
        if remaining == float('inf'):
            st.metric("🔮 剩餘預測", "♾️ 無限")
        else:
            st.metric("🔮 剩餘預測", remaining)
    with col3:
        used = user.get("predictions_used", 0)
        st.metric("📊 已用預測", used)
    
    st.divider()
    st.subheader("📋 個人資料")
    st.json({
        "用戶名": user.get("username"),
        "電郵": user.get("email", "N/A"),
        "註冊日期": user.get("registered_at", "N/A"),
        "到期日": user.get("expiry", "N/A")
    })

def history_page():
    st.title("📜 預測歷史")
    st.info("你嘅預測記錄（示範數據）")
    data = {
        "日期": ["2026-08-20", "2026-08-19", "2026-08-18"],
        "場次": [9, 8, 7],
        "預測馬匹": ["美麗傳承", "金鎗六十", "時時精綵"],
        "結果": ["✅ 命中", "❌ 未中", "✅ 命中"]
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

def admin_page():
    """後台管理主頁面"""
    st.title("⚙️ 後台管理")
    if not is_admin():
        st.error("⛔ 沒有權限")
        return
    
    tabs = st.tabs([
        "📊 總覽",
        "👥 用戶管理",
        "💳 付款審核",
        "📈 數據分析",
        "💰 財務管理",
        "🎟️ 優惠碼",
        "📝 內容管理",
        "🔒 安全",
        "📋 操作日誌",
        "🔄 自動化",
        "⚡ 系統監控"
    ])
    
    # Tab 0: 總覽
    with tabs[0]:
        st.subheader("📊 系統總覽")
        users = load_json(USERS_FILE, {})
        total_users = len(users)
        paid_users = sum(1 for u in users.values() if u.get("level") in ["付費用戶", "VIP"])
        st.metric("👤 總用戶", total_users)
        st.metric("💎 付費用戶", paid_users)
        st.metric("📈 付費轉化率", f"{paid_users/total_users*100:.1f}%" if total_users > 0 else "0%")
    
    # Tab 1: 用戶管理
    with tabs[1]:
        if CONFIG["module_user_management"]:
            st.subheader("👥 用戶管理")
            users = load_json(USERS_FILE, {})
            search = st.text_input("搜尋用戶")
            filtered_users = users if not search else {k:v for k,v in users.items() if search.lower() in k.lower()}
            for username, info in filtered_users.items():
                with st.expander(f"{username} - {info.get('level')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.json(info)
                    with col2:
                        new_level = st.selectbox(
                            "修改等級",
                            ["免費用戶", "付費用戶", "VIP", "超級管理員"],
                            index=["免費用戶", "付費用戶", "VIP", "超級管理員"].index(info.get("level", "免費用戶")),
                            key=f"level_{username}"
                        )
                        if st.button("更新", key=f"update_{username}"):
                            users[username]["level"] = new_level
                            save_json(USERS_FILE, users)
                            st.success("更新成功")
                            st.rerun()
        else:
            st.info("此模組已關閉")
    
    # Tab 2: 付款審核 (整合 payment_admin)
    with tabs[2]:
        if payment_admin:
            try:
                payment_admin.payment_review_page()
            except Exception as e:
                st.error(f"付款審核模組載入失敗：{e}")
                st.info("請檢查 payment_admin.py 檔案是否存在及語法正確")
        else:
            st.error("付款審核模組未載入")
    
    # Tab 3: 數據分析
    with tabs[3]:
        if CONFIG["module_analytics"]:
            st.subheader("📈 數據分析")
            # 模擬 DAU 數據
            dates = pd.date_range(end=datetime.today(), periods=30, freq="D")
            dau = [10 + i*0.5 + (i%7)*2 for i in range(30)]
            df = pd.DataFrame({"日期": dates, "DAU": dau})
            fig = px.line(df, x="日期", y="DAU", title="每日活躍用戶 (DAU)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("此模組已關閉")
    
    # Tab 4: 財務管理
    with tabs[4]:
        if CONFIG["module_finance"]:
            st.subheader("💰 財務管理")
            st.metric("本月收入", "$12,800")
            st.metric("本年收入", "$156,200")
            # 模擬收入趨勢
            months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"]
            revenue = [12000, 15000, 18000, 14000, 16000, 19000, 21000, 12800]
            df = pd.DataFrame({"月份": months, "收入": revenue})
            fig = px.bar(df, x="月份", y="收入", title="月度收入")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("此模組已關閉")
    
    # Tab 5: 優惠碼
    with tabs[5]:
        if CONFIG["module_promo"]:
            st.subheader("🎟️ 優惠碼管理")
            code = st.text_input("優惠碼")
            discount = st.number_input("折扣 (%)", min_value=0, max_value=100, value=20)
            if st.button("建立優惠碼"):
                st.success(f"優惠碼 {code} 已建立，折扣 {discount}%")
        else:
            st.info("此模組已關閉")
    
    # Tab 6: 內容管理
    with tabs[6]:
        if CONFIG["module_content"]:
            st.subheader("📝 內容管理")
            announcement = st.text_area("公告內容", "歡迎使用SHTSN賽馬AI預測系統！")
            if st.button("發布公告"):
                st.success("公告已更新")
        else:
            st.info("此模組已關閉")
    
    # Tab 7: 安全
    with tabs[7]:
        if CONFIG["module_security"]:
            st.subheader("🔒 安全與權限")
            st.checkbox("啟用雙重驗證", value=False)
            st.text_input("允許IP列表 (逗號分隔)", placeholder="192.168.1.1, 10.0.0.1")
            st.button("儲存設定")
        else:
            st.info("此模組已關閉")
    
    # Tab 8: 操作日誌
    with tabs[8]:
        st.subheader("📋 操作日誌")
        log_file = "payment_audit.json"
        if os.path.exists(log_file):
            logs = load_json(log_file, {"logs": []})
            for log in logs.get("logs", [])[-50:]:
                st.text(f"[{log.get('time')}] {log.get('actor')} - {log.get('action')} - {log.get('detail', '')}")
        else:
            st.info("暫無日誌")
    
    # Tab 9: 自動化
    with tabs[9]:
        if CONFIG["module_automation"]:
            st.subheader("🔄 自動化工具")
            st.checkbox("啟用到期提醒", value=True)
            st.checkbox("自動開通付費", value=False)
            st.button("立即執行到期檢查")
        else:
            st.info("此模組已關閉")
    
    # Tab 10: 系統監控
    with tabs[10]:
        if CONFIG["module_monitoring"]:
            st.subheader("⚡ 系統監控")
            files = ["ALL_DATA_MERGED.csv", "hk_racing_model.pkl", "hk_catboost_model.cbm", "hk_ranking_model.pkl", "users.json"]
            for f in files:
                exists = os.path.exists(f)
                st.text(f"{'✅' if exists else '❌'} {f}")
            st.info(f"最後更新：{datetime.now().isoformat()}")
        else:
            st.info("此模組已關閉")

# ---------- 主路由 ----------
def main():
    sidebar_login()
    
    # 頁面路由
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