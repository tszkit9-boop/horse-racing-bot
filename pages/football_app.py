import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="足球預測", page_icon="⚽")
st.title("⚽ 足球預測系統")

# 建立側邊欄輸入
st.sidebar.header("輸入賽事資料")
home_team = st.sidebar.text_input("主隊名稱", "法國")
away_team = st.sidebar.text_input("客隊名稱", "比利時")

st.subheader("手動輸入賠率（用於即時計算概率）")
col1, col2, col3 = st.columns(3)
odds_h = col1.number_input("主勝賠率", min_value=1.01, value=1.32, step=0.01)
odds_d = col2.number_input("和局賠率", min_value=1.01, value=4.60, step=0.01)
odds_a = col3.number_input("客勝賠率", min_value=1.01, value=6.20, step=0.01)

if st.button("開始預測", type="primary"):
    # 計算隱含概率
    imp_h, imp_d, imp_a = 1/odds_h, 1/odds_d, 1/odds_a
    total = imp_h + imp_d + imp_a
    prob_h, prob_d, prob_a = imp_h/total, imp_d/total, imp_a/total

    st.success(f"預測完成：{home_team} vs {away_team}")
    
    # 顯示主客和
    st.write("### 📌 主客和概率")
    st.write(f"**主勝 ({home_team})**: {prob_h:.2%}")
    st.write(f"**和局**: {prob_d:.2%}")
    st.write(f"**客勝 ({away_team})**: {prob_a:.2%}")

    # 泊松波膽計算
    home_avg = prob_h * 2.5 + 0.1
    away_avg = prob_a * 2.5 + 0.1
    
    st.write("### 🎯 波膽 Top 5")
    scores = []
    for i in range(6):
        for j in range(6):
            p = poisson.pmf(i, home_avg) * poisson.pmf(j, away_avg)
            scores.append((f"{i}:{j}", p))
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # 用表格顯示
    df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
    df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
    st.table(df_scores)
