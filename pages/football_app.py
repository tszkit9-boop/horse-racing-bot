import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import plotly.express as px

# ==========================================
# 網頁基本設定與 CSS 美化
# ==========================================
st.set_page_config(page_title="專業足球預測", page_icon="⚽", layout="wide")

# 自訂少少 CSS 令個網睇落高級啲
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; background-color: #1f77b4; color: white; }
    div[data-testid="stMetricValue"] { color: #1f77b4; font-size: 2.2rem; }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ 專業足球預測與 EV 分析")
st.markdown("結合**馬會賠率**、**泊松分佈**與**凱利公式**，計算真實投注價值。")

# ==========================================
# 側邊欄輸入
# ==========================================
with st.sidebar:
    st.header("📌 賽事設定")
    home_team = st.text_input("主隊名稱", "法國")
    away_team = st.text_input("客隊名稱", "比利時")
    
    st.divider()
    st.header("📊 輸入馬會賠率")
    odds_h = st.number_input("主勝賠率", min_value=1.01, value=1.32, step=0.01)
    odds_d = st.number_input("和局賠率", min_value=1.01, value=4.60, step=0.01)
    odds_a = st.number_input("客勝賠率", min_value=1.01, value=6.20, step=0.01)
    
    st.divider()
    analyze_btn = st.button("🚀 開始深度分析", type="primary")

# ==========================================
# 預測計算邏輯與介面顯示
# ==========================================
if analyze_btn:
    # 1. 計算隱含概率 (市場共識)
    imp_h, imp_d, imp_a = 1/odds_h, 1/odds_d, 1/odds_a
    total = imp_h + imp_d + imp_a
    prob_h, prob_d, prob_a = imp_h/total, imp_d/total, imp_a/total

    # 2. 用隱含概率反推場均入球
    home_avg = prob_h * 2.5 + 0.1
    away_avg = prob_a * 2.5 + 0.1

    # 3. 建立全場泊松矩陣 (0-6球)
    max_goals = 6
    matrix = np.zeros((max_goals+1, max_goals+1))
    for i in range(max_goals+1):
        for j in range(max_goals+1):
            matrix[i, j] = poisson.pmf(i, home_avg) * poisson.pmf(j, away_avg)

    # --- 主客和與賠率顯示 ---
    st.header(f"🏆 {home_team} vs {away_team}")
    col1, col2, col3 = st.columns(3)
    col1.metric(f"主勝 ({home_team})", f"{prob_h:.2%}", f"賠率 {odds_h}")
    col2.metric("和局", f"{prob_d:.2%}", f"賠率 {odds_d}")
    col3.metric(f"客勝 ({away_team})", f"{prob_a:.2%}", f"賠率 {odds_a}")

    st.divider()

    # --- 投注價值分析 (EV & 凱利) ---
    st.subheader("💰 投注價值分析 (EV & 凱利注碼)")
    st.markdown("**EV > 0** 代表長遠有利可圖；**凱利注碼** 代表建議使用幾多 % 本金落注。")
    
    ev_h = (prob_h * odds_h) - 1
    ev_d = (prob_d * odds_d) - 1
    ev_a = (prob_a * odds_a) - 1
    
    kelly_h = (prob_h * odds_h - 1) / (odds_h - 1) if odds_h > 1 else 0
    kelly_d = (prob_d * odds_d - 1) / (odds_d - 1) if odds_d > 1 else 0
    kelly_a = (prob_a * odds_a - 1) / (odds_a - 1) if odds_a > 1 else 0

    ev_data = {
        "選項": [f"主勝 ({home_team})", "和局", f"客勝 ({away_team})"],
        "預測概率": [f"{prob_h:.2%}", f"{prob_d:.2%}", f"{prob_a:.2%}"],
        "EV (期望值)": [f"{ev_h:.2f}", f"{ev_d:.2f}", f"{ev_a:.2f}"],
        "凱利建議注碼": [f"{max(0, kelly_h)*100:.1f}%", f"{max(0, kelly_d)*100:.1f}%", f"{max(0, kelly_a)*100:.1f}%"]
    }
    st.table(pd.DataFrame(ev_data))

    st.divider()

    # --- 波膽圖表與列表 ---
    col_chart, col_list = st.columns([2, 1])
    
    with col_chart:
        st.subheader("📊 波膽概率分佈圖 (Top 10)")
        scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        df_chart = pd.DataFrame(scores[:10], columns=["波膽", "概率"])
        df_chart["概率"] = df_chart["概率"] * 100 # 轉百分比
        
        fig = px.bar(df_chart, x="波膽", y="概率", text_auto='.1f', 
                     color="概率", color_continuous_scale="Blues")
        fig.update_layout(xaxis_title="波膽", yaxis_title="概率 (%)", showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_list:
        st.subheader("🎯 波膽 Top 5")
        df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
        df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
        st.dataframe(df_scores, hide_index=True, use_container_width=True)

    # --- 入球大細 & 讓球 ---
    st.divider()
    col_ou, col_ah = st.columns(2)
    
    with col_ou:
        st.subheader("⚽ 入球大細 (2.5球)")
        over = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 3)
        st.progress(float(over), text=f"大 (3球或以上)：{over:.2%}")
        st.progress(float(1-over), text=f"細 (0-2球)：{1-over:.2%}")

    with col_ah:
        st.subheader("⚖️ 讓球 (主隊 -0.5)")
        ah_home = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i > j)
        st.progress(float(ah_home), text=f"主隊贏盤 ({home_team})：{ah_home:.2%}")
        st.progress(float(1-ah_home), text=f"客隊贏盤 ({away_team})：{1-ah_home:.2%}")

    # --- 折疊選單：半場與半全場 ---
    st.divider()
    with st.expander("🔍 展開查看：半場及半全場預測 (按全場45%估算)"):
        ht_home, ht_away = home_avg * 0.45, away_avg * 0.45
        ht_matrix = np.zeros((max_goals+1, max_goals+1))
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                ht_matrix[i, j] = poisson.pmf(i, ht_home) * poisson.pmf(j, ht_away)
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**半場波膽 Top 5**")
            ht_scores = [(f"{i}:{j}", ht_matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
            ht_scores.sort(key=lambda x: x[1], reverse=True)
            df_ht = pd.DataFrame(ht_scores[:5], columns=["波膽", "概率"])
            df_ht["概率"] = df_ht["概率"].apply(lambda x: f"{x:.2%}")
            st.table(df_ht)
            
        with c2:
            st.write("**半全場 Top 5**")
            htft = {}
            for i in range(max_goals+1):
                for j in range(max_goals+1):
                    ht_res = 'H' if i > j else ('D' if i == j else 'A')
                    for k in range(max_goals+1):
                        for l in range(max_goals+1):
                            ft_res = 'H' if k > l else ('D' if k == l else 'A')
                            key = f"{ht_res}-{ft_res}"
                            htft[key] = htft.get(key, 0) + (ht_matrix[i, j] * matrix[k, l])
            htft_sorted = sorted(htft.items(), key=lambda x: x[1], reverse=True)
            df_htft = pd.DataFrame(htft_sorted[:5], columns=["組合", "概率"])
            df_htft["概率"] = df_htft["概率"].apply(lambda x: f"{x:.2%}")
            st.table(df_htft)
