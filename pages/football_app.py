import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import poisson
from datetime import datetime, date

st.set_page_config(page_title="全自動足球預測", page_icon="⚽", layout="centered")
st.title("⚽ 馬會熱門賽事預測")

# ==========================================
# 0. 球隊英文轉中文對照表
# ==========================================
TEAM_NAMES = {
    "France": "法國", "Belgium": "比利時", "Italy": "意大利", "Turkey": "土耳其",
    "Japan": "日本", "Brazil": "巴西", "Argentina": "阿根廷", "China": "中國",
    "South Korea": "南韓", "Uzbekistan": "烏茲別克", "Spain": "西班牙", "Germany": "德國",
    "Arsenal": "阿仙奴", "Manchester City": "曼城", "Manchester United": "曼聯",
    "Liverpool": "利物浦", "Chelsea": "車路士", "Tottenham": "熱刺",
    "Newcastle": "紐卡素", "Aston Villa": "阿士東維拉",
    "Real Madrid": "皇家馬德里", "Barcelona": "巴塞隆拿", "Atletico Madrid": "馬德里體育會",
    "Kashima Antlers": "鹿島鹿角", "Gamba Osaka": "大阪飛腳", "Urawa Reds": "浦和紅鑽",
    "W": "女足", "U21": "U21", "U20": "U20", "U19": "U19", "U17": "U17"
}

def translate_team(name):
    for eng, zh in TEAM_NAMES.items():
        if name.endswith(f" {eng}"):
            return f"{TEAM_NAMES.get(name.replace(f' {eng}', ''), name.replace(f' {eng}', ''))} {zh}"
    return TEAM_NAMES.get(name, name)

# 讀取 API Key
try:
    API_KEY = st.secrets["API_FOOTBALL_KEY"]
except:
    st.warning("⚠️ 請先在 Streamlit Secrets 設定 API_FOOTBALL_KEY！")
    st.stop()

# ==========================================
# 1. 選擇日期與過濾設定
# ==========================================
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("📅 請選擇比賽日期", date.today())
    with col2:
        show_all = st.checkbox("顯示所有賽事 (包括冷門/青年軍)", value=False)
    
    date_str = selected_date.strftime('%Y-%m-%d')

@st.cache_data(ttl=3600)
def get_fixtures(query_date, fetch_all):
    headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
    url = f"https://v3.football.api-sports.io/fixtures?date={query_date}"
    
    # 馬會常見聯賽關鍵字 (白名單)
    allowed_keywords = [
        "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", 
        "Champions League", "Europa League", "Conference League",
        "J1", "K League", "World Cup", "Euro", "Copa", "Nations League", 
        "Championship", "Eredivisie", "Primeira Liga", "FA Cup", "Carabao Cup"
    ]
    
    # 黑名單 (如果唔係 Fetch All 就會過濾)
    block_keywords = ["Women", "W ", "U19", "U20", "U21", "Reserve", "Youth", "Friendly", "Club Friendlies"]

    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        
        # 檢查 API 錯誤 (例如額度用完)
        if data.get('errors'):
            error_msg = str(data['errors'])
            return {"error": f"API 錯誤 (可能係免費額度用完): {error_msg}"}
            
        matches = []
        if 'response' in data:
            for m in data['response']:
                league_name = m['league']['name']
                
                if not fetch_all:
                    is_blocked = any(bk.lower() in league_name.lower() for bk in block_keywords)
                    if is_blocked: continue
                    
                    is_allowed = any(ak.lower() in league_name.lower() for ak in allowed_keywords)
                    # 放寬少少，非黑名單都照出
                
                h_eng = m['teams']['home']['name']
                a_eng = m['teams']['away']['name']
                h_zh = translate_team(h_eng)
                a_zh = translate_team(a_eng)
                fid = m['fixture']['id']
                
                display_name = f"[{league_name}] {h_zh} vs {a_zh}"
                matches.append({"name": display_name, "id": fid, "home": h_zh, "away": a_zh})
                
        return {"matches": matches}
    except Exception as e:
        return {"error": f"連線失敗: {e}"}

with st.spinner("正在讀取賽程..."):
    result = get_fixtures(date_str, show_all)

if "error" in result:
    st.error(f"❌ {result['error']}")
    st.stop()

today_matches = result["matches"]

if not today_matches:
    st.warning(f"⚠️ {date_str} 沒有符合條件的賽事。你可以剔上面個掣「顯示所有賽事」再試，或者換過另一日。")
    st.stop()

match_options = {m['name']: m for m in today_matches}
selected_match_name = st.selectbox("👇 請選擇賽事", list(match_options.keys()))

if st.button("🚀 立即預測", type="primary", use_container_width=True):
    match_info = match_options[selected_match_name]
    fixture_id = match_info['id']
    real_home = match_info['home']
    real_away = match_info['away']

    with st.spinner("正在抓取即時賠率..."):
        headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        odds_h, odds_d, odds_a = 2.00, 3.20, 3.50 
        
        try:
            odds_url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=8"
            res_odds = requests.get(odds_url, headers=headers)
            data_odds = res_odds.json()
            
            if 'response' in data_odds and len(data_odds['response']) > 0:
                bookmakers = data_odds['response'][0]['bookmakers']
                if len(bookmakers) > 0:
                    bets = bookmakers[0]['bets']
                    for bet in bets:
                        if bet['name'] == 'Match Winner' or bet['id'] == 1:
                            for val in bet['values']:
                                if val['value'] == 'Home': odds_h = float(val['odd'])
                                elif val['value'] == 'Draw': odds_d = float(val['odd'])
                                elif val['value'] == 'Away': odds_a = float(val['odd'])
                            break
            st.info(f"📊 已自動抓取賠率：主勝 {odds_h} / 和局 {odds_d} / 客勝 {odds_a}")
        except:
            st.warning("⚠️ 暫未搵到即時賠率，使用預設賠率計算。")

        # 泊松計算
        imp_h, imp_d, imp_a = 1/odds_h, 1/odds_d, 1/odds_a
        total = imp_h + imp_d + imp_a
        prob_h, prob_d, prob_a = imp_h/total, imp_d/total, imp_a/total

        home_avg = prob_h * 2.5 + 0.1
        away_avg = prob_a * 2.5 + 0.1

        max_goals = 6
        matrix = np.zeros((max_goals+1, max_goals+1))
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                matrix[i, j] = poisson.pmf(i, home_avg) * poisson.pmf(j, away_avg)

        st.divider()
        st.header(f"🏆 分析結果：{real_home} vs {real_away}")

        res1, res2, res3 = st.columns(3)
        res1.metric(f"主勝 ({real_home})", f"{prob_h:.2%}", f"賠率: {odds_h}")
        res2.metric("和局", f"{prob_d:.2%}", f"賠率: {odds_d}")
        res3.metric(f"客勝 ({real_away})", f"{prob_a:.2%}", f"賠率: {odds_a}")

        st.divider()
        st.subheader("🎯 波膽 Top 5")
        scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
        scores.sort(key=lambda x: x[1], reverse=True)
        df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
        df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
        st.table(df_scores)

        st.divider()
        col_ou, col_ah = st.columns(2)
        with col_ou:
            st.subheader("⚽ 入球大細 (2.5球)")
            over = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 3)
            st.progress(float(over), text=f"大：{over:.2%}")
            st.progress(float(1-over), text=f"細：{1-over:.2%}")
        with col_ah:
            st.subheader("⚖️ 讓球 (主隊 -0.5)")
            st.progress(float(prob_h), text=f"主隊贏盤：{prob_h:.2%}")
            st.progress(float(1-prob_h), text=f"客隊贏盤：{1-prob_h:.2%}")
