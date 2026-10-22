import streamlit as st
import pandas as pd
import numpy as np
import re
from scipy.stats import poisson

st.set_page_config(page_title="一鍵貼上預測", page_icon="⚽", layout="centered")
st.title("⚽ 一鍵貼上賠率預測")
st.markdown("請直接將馬會嘅賽事及賠率 **Copy & Paste** 落下面，系統會自動分析！")

with st.container(border=True):
    st.subheader("📋 請貼上賽事資料")
    st.markdown("""
    **支援任何格式（打直、打橫、連埋一齊都得）：**
    *   `法國 比利時 1.32 4.60 6.20`
    *   或者直接喺馬會 Copy 一大段掟落嚟。
    """)
    
    default_text = """比錫達斯
永島拿
1.85
3.70
2.85"""
    pasted_text = st.text_area("貼上資料：", value=default_text, height=180)

analyze_btn = st.button("🚀 自動解析並預測", type="primary", use_container_width=True)

if analyze_btn:
    if not pasted_text.strip():
        st.warning("⚠️ 請先貼上賽事資料！")
        st.stop()
    
    flat_text = " ".join(pasted_text.split())
    pattern = r"(.*?)\s+(.*?)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)"
    matches = re.findall(pattern, flat_text)
    
    if not matches:
        st.error("❌ 認唔到資料格式，請確保有隊名同三個賠率（例如：法國 比利時 1.32 4.60 6.20）。")
        st.stop()
        
    st.success(f"✅ 成功解析並預測 {len(matches)} 場賽事！")
    
    for match in matches:
        home_team, away_team, odds_h_str, odds_d_str, odds_a_str = match
        
        home_team = re.sub(r'(?i)\bvs\b|對', '', home_team).strip()
        away_team = re.sub(r'(?i)\bvs\b|對', '', away_team).strip()
        
        odds_h = float(odds_h_str)
        odds_d = float(odds_d_str)
        odds_a = float(odds_a_str)
        
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
        st.header(f"🏆 {home_team} vs {away_team}")
        
        res1, res2, res3 = st.columns(3)
        res1.metric(f"主勝 ({home_team})", f"{prob_h:.2%}", f"賠率: {odds_h}")
        res2.metric("和局", f"{prob_d:.2%}", f"賠率: {odds_d}")
        res3.metric(f"客勝 ({away_team})", f"{prob_a:.2%}", f"賠率: {odds_a}")

        col_left, col_right = st.columns(2)
        with col_left:
            # 👇 改咗做 Top 3
            st.write("🎯 **波膽 Top 3**")
            scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
            scores.sort(key=lambda x: x[1], reverse=True)
            # 👇 改咗做 [:3]
            df_scores = pd.DataFrame(scores[:3], columns=["波膽", "概率"])
            df_scores["概率"] = df_scores["概率"].apply(lambda x: f"{x:.2%}")
            st.dataframe(df_scores, hide_index=True, use_container_width=True)
            
        with col_right:
            st.write("⚽ **入球大細 (2.5球)**")
            over = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i+j >= 3)
            st.progress(float(over), text=f"大：{over:.2%}")
            st.progress(float(1-over), text=f"細：{1-over:.2%}")
            
            st.write("⚖️ **讓球 (主隊 -0.5)**")
            st.progress(float(prob_h), text=f"主隊贏盤：{prob_h:.2%}")
            st.progress(float(1-prob_h), text=f"客隊贏盤：{1-prob_h:.2%}")
