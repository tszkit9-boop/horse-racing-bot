import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="足球預測", page_icon="⚽", layout="centered")
st.title("⚽ 專業足球預測")

# --- 主畫面輸入區 ---
st.subheader("📌 請輸入賽事及賠率")
col1, col2 = st.columns(2)
with col1:
    home_team = st.text_input("主隊名稱", "法國")
with col2:
    away_team = st.text_input("客隊名稱", "比利時")

st.write("**輸入馬會賠率**")
c1, c2, c3 = st.columns(3)
odds_h = c1.number_input("主勝賠率", min_value=1.01, value=1.32, step=0.01)
odds_d = c2.number_input("和局賠率", min_value=1.01, value=4.60, step=0.01)
odds_a = c3.number_input("客勝賠率", min_value=1.01, value=6.20, step=0.01)

analyze_btn = st.button("🚀 開始分析", type="primary", use_container_width=True)
st.divider()

# --- 預測結果區 ---
if analyze_btn:
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

    st.header(f"🏆 {home_team} vs {away_team}")
    
    # 主客和
    res1, res2, res3 = st.columns(3)
    res1.metric(f"主勝 ({home_team})", f"{prob_h:.2%}", f"賠率 {odds_h}")
    res2.metric("和局", f"{prob_d:.2%}", f"賠率 {odds_d}")
    res3.metric(f"客勝 ({away_team})", f"{prob_a:.2%}", f"賠率 {odds_a}")
    
    st.divider()

    # 波膽
    st.subheader("🎯 波膽 Top 5")
    scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
    scores.sort(key=lambda x: x[1], reverse=True)
    df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
    df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
    st.table(df_scores)
    
    st.divider()

    # 入球大細 & 讓球
    col_ou, col_ah = st.columns(2)
    with col_ou:
        st.subheader("⚽ 入球大細 (2.5球)")
        over = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 3)
        st.write(f"**大 (3球或以上)**：{over:.2%}")
        st.write(f"**細 (0-2球)**：{1-over:.2%}")
    with col_ah:
        st.subheader("⚖️ 讓球 (主隊 -0.5)")
        ah_home = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i > j)
        st.write(f"**主隊贏盤 ({home_team})**：{ah_home:.2%}")
        st.write(f"**客隊贏盤 ({away_team})**：{1-ah_home:.2%}")
