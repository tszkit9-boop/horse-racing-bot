import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import poisson
from datetime import datetime, date

st.set_page_config(page_title="全自動足球預測", page_icon="⚽", layout="centered")
st.title("⚽ 免打字全自動預測")

# 讀取 API Key
try:
    API_KEY = st.secrets["API_FOOTBALL_KEY"]
except:
    API_KEY = ""
    st.warning("⚠️ 請先在 Streamlit Secrets 設定 API_FOOTBALL_KEY！")
    st.stop()

# ==========================================
# 1. 選擇日期並自動抓取賽事
# ==========================================
with st.container(border=True):
    st.subheader("📅 請選擇比賽日期")
    # 預設為今天
    selected_date = st.date_input("日期", date.today())
    date_str = selected_date.strftime('%Y-%m-%d')

@st.cache_data(ttl=3600)
def get_fixtures_by_date(query_date):
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    url = f"https://v3.football.api-sports.io/fixtures?date={query_date}"
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        matches = []
        if 'response' in data:
            for m in data['response']:
                h = m['teams']['home']['name']
                a = m['teams']['away']['name']
                fid = m['fixture']['id']
                matches.append({"name": f"{h} vs {a}", "id": fid, "home": h, "away": a})
        return matches
    except:
        return []

with st.spinner("正在讀取該日賽程..."):
    today_matches = get_fixtures_by_date(date_str)

if not today_matches:
    st.error(f"❌ {date_str} 暫時沒有賽事數據（或 API 額度已用完）。")
    st.stop()

# 自動生成下拉選單，你唔使打任何字
match_options = {m['name']: m for m in today_matches}
selected_match_name = st.selectbox("👇 請直接選擇賽事", list(match_options.keys()))

if st.button("🚀 立即預測", type="primary", use_container_width=True):
    match_info = match_options[selected_match_name]
    fixture_id = match_info['id']
    real_home = match_info['home']
    real_away = match_info['away']

    with st.spinner("正在抓取即時賠率..."):
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        odds_h, odds_d, odds_a = 2.00, 3.20, 3.50 # 後備賠率
        
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

        # ==========================================
        # 泊松計算與顯示
        # ==========================================
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
        res1.metric(f"主勝", f"{prob_h:.2%}", f"賠率: {odds_h}")
        res2.metric("和局", f"{prob_d:.2%}", f"賠率: {odds_d}")
        res3.metric(f"客勝", f"{prob_a:.2%}", f"賠率: {odds_a}")

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
