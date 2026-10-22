import streamlit as st
import pandas as pd
import numpy as np
import re
from scipy.stats import poisson

st.set_page_config(page_title="一鍵貼上預測", page_icon="⚽", layout="centered")
st.title("⚽ 一鍵貼上賠率預測")
st.markdown("請直接將馬會嘅賽事及賠率 **Copy & Paste** 落下面，系統會自動分析！")

# ==========================================
# 輸入區：一個大文字框
# ==========================================
with st.container(border=True):
    st.subheader("📋 請貼上賽事資料")
    st.markdown("""
    **支援格式（每行一場）：**
    *   `法國 vs 比利時 1.32 4.60 6.20` （建議用 vs 或空格隔開）
    *   `些路迪切爾達 2.52 3.30 2.32` （連埋一齊都認到）
    """)
    
    # 預設填入你頭先嗰行
    default_text = "些路迪切爾達 2.52 3.30 2.32\n法國 比利時 1.32 4.60 6.20"
    pasted_text = st.text_area("貼上資料：", value=default_text, height=150)

analyze_btn = st.button("🚀 自動解析並預測", type="primary", use_container_width=True)

# ==========================================
# 解析與計算邏輯
# ==========================================
if analyze_btn:
    if not pasted_text.strip():
        st.warning("⚠️ 請先貼上賽事資料！")
        st.stop()
    
    lines = pasted_text.strip().split('\n')
    parsed_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 1. 搵出所有小數（賠率）
        odds_list = re.findall(r'\d+\.\d+', line)
        if len(odds_list) < 3:
            continue
        
        # 取前三個數字做賠率
        odds_h = float(odds_list[0])
        odds_d = float(odds_list[1])
        odds_a = float(odds_list[2])

        # 2. 將數字替換走，剩低嘅字就係隊名
        team_str = line
        for odd in odds_list[:3]:
            team_str = team_str.replace(odd, '')
        
        team_str = team_str.strip()
        
        # 3. 嘗試拆分主客隊 (如果有 vs, v, 對, 或空格)
        if 'vs' in team_str.lower():
            parts = re.split(r'(?i)vs', team_str)
        elif '對' in team_str:
            parts = team_str.split('對')
        elif ' ' in team_str:
            parts = team_str.split()
        else:
            # 如果完全冇分隔符，就當成一個整體顯示
            parts = [team_str, ""]
            
        home_team = parts[0].strip() if len(parts) > 0 else "主隊"
        away_team = parts[1].strip() if len(parts) > 1 else "客隊"

        parsed_count += 1

        # ==========================================
        # 泊松計算
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
        display_name = f"{home_team} vs {away_team}" if away_team else home_team
        st.header(f"🏆 {display_name}")
        
        res1, res2, res3 = st.columns(3)
        res1.metric(f"主勝", f"{prob_h:.2%}", f"賠率: {odds_h}")
        res2.metric("和局", f"{prob_d:.2%}", f"賠率: {odds_d}")
        res3.metric(f"客勝", f"{prob_a:.2%}", f"賠率: {odds_a}")

        col_left, col_right = st.columns(2)
        with col_left:
            st.write("🎯 **波膽 Top 5**")
            scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
            scores.sort(key=lambda x: x[1], reverse=True)
            df_scores = pd.DataFrame(scores[:5], columns=["波膽", "概率"])
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

    if parsed_count == 0:
        st.error("❌ 完全認唔到數字，請確保每行至少有 3 個賠率數字（例如：2.52 3.30 2.32）。")
    else:
        st.success(f"✅ 成功解析並預測 {parsed_count} 場賽事！")
