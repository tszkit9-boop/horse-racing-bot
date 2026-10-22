import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import poisson
from datetime import datetime, date

st.set_page_config(page_title="馬會賽事預測", page_icon="⚽", layout="wide")
st.title("⚽ 馬會熱門賽事預測")

# 讀取 API Key
try:
    API_KEY = st.secrets["FOOTBALL_DATA_KEY"]
except:
    st.warning("⚠️ 請先在 Streamlit Secrets 設定 FOOTBALL_DATA_KEY！")
    st.stop()

# ==========================================
# 1. 選擇日期並自動抓取賽程
# ==========================================
with st.container(border=True):
    st.subheader("📅 請選擇比賽日期")
    selected_date = st.date_input("日期", date.today())
    date_str = selected_date.strftime('%Y-%m-%d')

@st.cache_data(ttl=3600)
def get_fixtures(query_date):
    headers = {'X-Auth-Token': API_KEY}
    # 免費版只支援部分聯賽，這裡示範抓取英超 (PL) 和歐聯 (CL)
    # 你可以根據需要修改 competition 參數，例如 'PL' 代表英超
    url = f"https://api.football-data.org/v4/matches?dateFrom={query_date}&dateTo={query_date}"
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        
        if 'message' in data:
            return {"error": f"API 錯誤: {data['message']}"}
            
        matches = []
        if 'matches' in data:
            for m in data['matches']:
                h = m['homeTeam']['name']
                a = m['awayTeam']['name']
                fid = m['id']
                competition = m['competition']['name']
                matches.append({"name": f"[{competition}] {h} vs {a}", "id": fid, "home": h, "away": a})
        return {"matches": matches}
    except Exception as e:
        return {"error": f"連線失敗: {e}"}

with st.spinner("正在讀取賽程..."):
    result = get_fixtures(date_str)

if "error" in result:
    st.error(f"❌ {result['error']}")
    st.stop()

today_matches = result["matches"]

if not today_matches:
    st.warning(f"⚠️ {date_str} 暫時沒有賽程數據（免費版只支援部分聯賽）。")
    st.stop()

match_options = {m['name']: m for m in today_matches}
selected_match_name = st.selectbox("👇 請選擇賽事", list(match_options.keys()))

# ==========================================
# 2. 手動輸入賠率（因為免費版冇賠率）
# ==========================================
st.divider()
st.subheader("💰 請手動輸入馬會賠率")
st.info("Football-Data.org 免費版不提供賠率，請從馬會網站複製即時賠率填寫。")

col1, col2, col3 = st.columns(3)
odds_h = col1.number_input("主勝賠率", min_value=1.01, value=1.50, step=0.01)
odds_d = col2.number_input("和局賠率", min_value=1.01, value=3.80, step=0.01)
odds_a = col3.number_input("客勝賠率", min_value=1.01, value=5.00, step=0.01)

if st.button("🚀 立即預測", type="primary", use_container_width=True):
    match_info = match_options[selected_match_name]
    real_home = match_info['home']
    real_away = match_info['away']

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
