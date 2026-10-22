import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import poisson
from datetime import datetime

st.set_page_config(page_title="全自動足球預測", page_icon="⚽", layout="centered")
st.title("⚽ 全自動足球預測系統")

# 從 Secrets 安全讀取 API Key
try:
    API_KEY = st.secrets["API_FOOTBALL_KEY"]
except:
    API_KEY = ""

if not API_KEY:
    st.warning("⚠️ 請先在 Streamlit Secrets 設定 API_FOOTBALL_KEY 才能使用自動抓取功能。")
    st.stop()

with st.container(border=True):
    st.subheader("📌 輸入球隊名稱 (必須用英文)")
    st.write("系統會自動去國際數據庫搵今日嘅賽事及即時賠率！")
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.text_input("主隊", "France")
    with col2:
        away_team = st.text_input("客隊", "Belgium")

if st.button("🔍 全自動抓取賠率並預測", type="primary", use_container_width=True):
    with st.spinner("正在搜尋賽事及抓取即時賠率，請稍等..."):
        
        # ==========================================
        # 1. 經由 API 搜尋賽事 (Fixtures)
        # ==========================================
        today_str = datetime.now().strftime('%Y-%m-%d')
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        
        # 搜尋今日賽事
        fixture_url = f"https://v3.football.api-sports.io/fixtures?date={today_str}"
        try:
            res = requests.get(fixture_url, headers=headers)
            data = res.json()
            
            fixture_id = None
            real_home = ""
            real_away = ""
            
            # 喺今日賽事入面搵返呢兩隊
            if 'response' in data:
                for match in data['response']:
                    h_name = match['teams']['home']['name']
                    a_name = match['teams']['away']['name']
                    if home_team.lower() in h_name.lower() and away_team.lower() in a_name.lower():
                        fixture_id = match['fixture']['id']
                        real_home = h_name
                        real_away = a_name
                        break
            
            if not fixture_id:
                st.error(f"❌ 喺今日 ({today_str}) 嘅賽程中，搵唔到 {home_team} 對 {away_team} 嘅比賽。請確認隊名或比賽日期。")
                st.stop()
                
            st.success(f"✅ 搵到賽事：{real_home} vs {real_away} (ID: {fixture_id})")

        except Exception as e:
            st.error(f"❌ 搜尋賽事時出錯：{e}")
            st.stop()

        # ==========================================
        # 2. 經由 API 抓取即時賠率 (Odds)
        # ==========================================
        odds_h, odds_d, odds_a = 2.00, 3.20, 3.50 # 預設後備賠率
        try:
            odds_url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=8" # bookmaker=8 通常係 Bet365
            res_odds = requests.get(odds_url, headers=headers)
            data_odds = res_odds.json()
            
            if 'response' in data_odds and len(data_odds['response']) > 0:
                bookmakers = data_odds['response'][0]['bookmakers']
                if len(bookmakers) > 0:
                    bets = bookmakers[0]['bets']
                    for bet in bets:
                        if bet['name'] == 'Match Winner' or bet['id'] == 1:
                            # 提取真實賠率
                            for val in bet['values']:
                                if val['value'] == 'Home':
                                    odds_h = float(val['odd'])
                                elif val['value'] == 'Draw':
                                    odds_d = float(val['odd'])
                                elif val['value'] == 'Away':
                                    odds_a = float(val['odd'])
                            break
                st.info(f"📊 成功抓取即時賠率：主勝 {odds_h} / 和局 {odds_d} / 客勝 {odds_a}")
            else:
                st.warning("⚠️ 暫時未搵到該場賽事嘅賠率，將使用預設平均賠率作計算。")
        except Exception as e:
            st.warning(f"⚠️ 抓取賠率時出錯，將使用預設賠率。 ({e})")

        # ==========================================
        # 3. 計算隱含概率及泊松分佈
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

        # ==========================================
        # 4. 顯示結果
        # ==========================================
        st.divider()
        st.header(f"🏆 分析結果：{real_home} vs {real_away}")

        res1, res2, res3 = st.columns(3)
        res1.metric(f"主勝 ({real_home})", f"{prob_h:.2%}", f"賠率: {odds_h}")
        res2.metric("和局", f"{prob_d:.2%}", f"賠率: {odds_d}")
        res3.metric(f"客勝 ({real_away})", f"{prob_a:.2%}", f"賠率: {odds_a}")

        st.divider()

        # --- 投注價值分析 (EV & 凱利) ---
        st.subheader("💰 投注價值分析 (EV & 凱利注碼)")
        ev_h = (prob_h * odds_h) - 1
        ev_d = (prob_d * odds_d) - 1
        ev_a = (prob_a * odds_a) - 1
        
        kelly_h = (prob_h * odds_h - 1) / (odds_h - 1) if odds_h > 1 else 0
        kelly_d = (prob_d * odds_d - 1) / (odds_d - 1) if odds_d > 1 else 0
        kelly_a = (prob_a * odds_a - 1) / (odds_a - 1) if odds_a > 1 else 0

        ev_data = {
            "選項": [f"主勝 ({real_home})", "和局", f"客勝 ({real_away})"],
            "預測概率": [f"{prob_h:.2%}", f"{prob_d:.2%}", f"{prob_a:.2%}"],
            "EV (期望值)": [f"{ev_h:+.2f}", f"{ev_d:+.2f}", f"{ev_a:+.2f}"],
            "凱利建議注碼": [f"{max(0, kelly_h)*100:.1f}%", f"{max(0, kelly_d)*100:.1f}%", f"{max(0, kelly_a)*100:.1f}%"]
        }
        st.table(pd.DataFrame(ev_data))

        st.divider()

        # --- 波膽 Top 5 ---
        st.subheader("🎯 波膽 Top 5")
        scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
        scores.sort(key=lambda x: x[1], reverse=True)
        df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
        df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
        st.table(df_scores)

        st.divider()

        # --- 入球大細 & 讓球 ---
        col_ou, col_ah = st.columns(2)
        with col_ou:
            st.subheader("⚽ 入球大細 (2.5球)")
            over = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 3)
            st.progress(float(over), text=f"大 (3球或以上)：{over:.2%}")
            st.progress(float(1-over), text=f"細 (0-2球)：{1-over:.2%}")
        with col_ah:
            st.subheader("⚖️ 讓球 (主隊 -0.5)")
            st.progress(float(prob_h), text=f"主隊贏盤 ({real_home})：{prob_h:.2%}")
            st.progress(float(1-prob_h), text=f"客隊贏盤 ({real_away})：{1-prob_h:.2%}")
