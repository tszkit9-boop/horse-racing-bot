import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# 設定網頁標題同排版
st.set_page_config(page_title="足球預測", page_icon="⚽", layout="wide")
st.title("⚽ 足球賠率預測系統")
st.markdown("輸入兩隊名稱及**馬會賠率**，即時計算出各項預測概率及波膽。")

# ==========================================
# 側邊欄輸入
# ==========================================
st.sidebar.header("📌 輸入賽事資料")
home_team = st.sidebar.text_input("主隊名稱", "法國")
away_team = st.sidebar.text_input("客隊名稱", "比利時")

# ==========================================
# 主畫面輸入賠率
# ==========================================
st.subheader("📊 輸入賠率")
col1, col2, col3 = st.columns(3)
odds_h = col1.number_input("主勝賠率", min_value=1.01, value=1.32, step=0.01)
odds_d = col2.number_input("和局賠率", min_value=1.01, value=4.60, step=0.01)
odds_a = col3.number_input("客勝賠率", min_value=1.01, value=6.20, step=0.01)

# ==========================================
# 預測計算邏輯
# ==========================================
if st.button("🚀 開始全面預測", type="primary", use_container_width=True):
    
    # 1. 計算隱含概率
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

    st.success(f"✅ 預測完成：{home_team} vs {away_team}")
    
    # --- 區塊 A：主客和 ---
    st.write("---")
    st.subheader("🎯 主客和概率")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"主勝 ({home_team})", f"{prob_h:.2%}")
    c2.metric("和局", f"{prob_d:.2%}")
    c3.metric(f"客勝 ({away_team})", f"{prob_a:.2%}")

    # --- 區塊 B：入球大細 & 讓球 ---
    st.write("---")
    col_ou, col_ah = st.columns(2)
    
    with col_ou:
        st.subheader("⚽ 入球大細 (2.5球)")
        over = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 3)
        st.metric("大 (3球或以上)", f"{over:.2%}")
        st.metric("細 (0-2球)", f"{1-over:.2%}")

    with col_ah:
        st.subheader("⚖️ 讓球 (主隊 -0.5)")
        ah_home = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i > j)
        st.metric(f"主隊贏盤 ({home_team})", f"{ah_home:.2%}")
        st.metric(f"客隊贏盤 ({away_team})", f"{1-ah_home:.2%}")

    # --- 區塊 C：全場波膽 ---
    st.write("---")
    st.subheader("🎲 全場波膽 Top 5")
    scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
    scores.sort(key=lambda x: x[1], reverse=True)
    
    df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
    df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
    st.table(df_scores)

    # --- 區塊 D：半場預測 (估算：全場 45%) ---
    st.write("---")
    st.subheader("⏱️ 半場預測 (按全場45%估算)")
    
    ht_home, ht_away = home_avg * 0.45, away_avg * 0.45
    ht_matrix = np.zeros((max_goals+1, max_goals+1))
    for i in range(max_goals+1):
        for j in range(max_goals+1):
            ht_matrix[i, j] = poisson.pmf(i, ht_home) * poisson.pmf(j, ht_away)

    col_ht1, col_ht2 = st.columns(2)
    
    with col_ht1:
        st.write("**半場主客和**")
        ht_h = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i > j)
        ht_d = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i == j)
        ht_a = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i < j)
        st.write(f"主勝：{ht_h:.2%}")
        st.write(f"和局：{ht_d:.2%}")
        st.write(f"客勝：{ht_a:.2%}")
        
        st.write("**半場大細 (1.5球)**")
        ht_over = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 2)
        st.write(f"大：{ht_over:.2%}")
        st.write(f"細：{1-ht_over:.2%}")

    with col_ht2:
        st.write("**半場波膽 Top 5**")
        ht_scores = [(f"{i}:{j}", ht_matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
        ht_scores.sort(key=lambda x: x[1], reverse=True)
        df_ht = pd.DataFrame(ht_scores[:5], columns=["波膽", "概率"])
        df_ht["概率"] = df_ht["概率"].apply(lambda x: f"{x:.2%}")
        st.table(df_ht)

    # --- 區塊 E：半全場估算 ---
    st.write("---")
    st.subheader("🔄 半全場 Top 5 (估算)")
    
    htft = {}
    for i in range(max_goals+1):
        for j in range(max_goals+1):
            ht_result = 'H' if i > j else ('D' if i == j else 'A')
            for k in range(max_goals+1):
                for l in range(max_goals+1):
                    ft_result = 'H' if k > l else ('D' if k == l else 'A')
                    prob = ht_matrix[i, j] * matrix[k, l]
                    key = f"{ht_result}-{ft_result}"
                    htft[key] = htft.get(key, 0) + prob
    
    htft_sorted = sorted(htft.items(), key=lambda x: x[1], reverse=True)
    df_htft = pd.DataFrame(htft_sorted[:5], columns=["半全場組合 (半場-全場)", "概率"])
    df_htft["概率"] = df_htft["概率"].apply(lambda x: f"{x:.2%}")
    st.table(df_htft)
