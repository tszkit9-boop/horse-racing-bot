import streamlit as st
import pandas as pd
import numpy as np
import re
from scipy.stats import poisson

st.set_page_config(page_title="一鍵貼上預測", page_icon="⚽", layout="wide")
st.title("⚽ 一鍵貼上賠率預測 (終極版)")
st.markdown("請直接將馬會嘅賽事及賠率 **Copy & Paste** 落下面，系統會自動分析！")

# ==========================================
# 輸入區
# ==========================================
with st.container(border=True):
    st.subheader("📋 請貼上賽事資料")
    st.markdown("""
    **支援任何格式（打直、打橫、連埋一齊都得）：**
    *   `法國 比利時 1.32 4.60 6.20`
    *   或者直接喺馬會 Copy 一大段掟落嚟。
    """)
    
    default_text = """法國 比利時 1.32 4.60 6.20
意大利 土耳其 1.25 5.00 7.50"""
    pasted_text = st.text_area("貼上資料：", value=default_text, height=150)

analyze_btn = st.button("🚀 自動解析並全面預測", type="primary", use_container_width=True)

# ==========================================
# 解析與計算邏輯
# ==========================================
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
    
    # 逐場顯示預測
    for match in matches:
        home_team, away_team, odds_h_str, odds_d_str, odds_a_str = match
        
        home_team = re.sub(r'(?i)\bvs\b|對', '', home_team).strip()
        away_team = re.sub(r'(?i)\bvs\b|對', '', away_team).strip()
        
        odds_h = float(odds_h_str)
        odds_d = float(odds_d_str)
        odds_a = float(odds_a_str)
        
        # 1. 計算隱含概率
        imp_h, imp_d, imp_a = 1/odds_h, 1/odds_d, 1/odds_a
        total = imp_h + imp_d + imp_a
        prob_h, prob_d, prob_a = imp_h/total, imp_d/total, imp_a/total

        # 2. 反推場均入球
        home_avg = prob_h * 2.5 + 0.1
        away_avg = prob_a * 2.5 + 0.1

        # 3. 建立全場泊松矩陣
        max_goals = 6
        matrix = np.zeros((max_goals+1, max_goals+1))
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                matrix[i, j] = poisson.pmf(i, home_avg) * poisson.pmf(j, away_avg)

        st.divider()
        st.header(f"🏆 {home_team} vs {away_team}")
        
        # --- 主客和及 EV 分析 ---
        res1, res2, res3 = st.columns(3)
        res1.metric(f"主勝 ({home_team})", f"{prob_h:.2%}", f"賠率: {odds_h}")
        res2.metric("和局", f"{prob_d:.2%}", f"賠率: {odds_d}")
        res3.metric(f"客勝 ({away_team})", f"{prob_a:.2%}", f"賠率: {odds_a}")

        # --- EV & 凱利 (如果賠率大於1才計算) ---
        ev_h = (prob_h * odds_h) - 1
        ev_d = (prob_d * odds_d) - 1
        ev_a = (prob_a * odds_a) - 1
        
        kelly_h = (prob_h * odds_h - 1) / (odds_h - 1) if odds_h > 1 else 0
        kelly_d = (prob_d * odds_d - 1) / (odds_d - 1) if odds_d > 1 else 0
        kelly_a = (prob_a * odds_a - 1) / (odds_a - 1) if odds_a > 1 else 0

        with st.expander("💰 展開查看：投注價值 (EV) 及 凱利建議注碼", expanded=False):
            ev_data = {
                "選項": [f"主勝 ({home_team})", "和局", f"客勝 ({away_team})"],
                "預測概率": [f"{prob_h:.2%}", f"{prob_d:.2%}", f"{prob_a:.2%}"],
                "EV (期望值)": [f"{ev_h:+.2f}", f"{ev_d:+.2f}", f"{ev_a:+.2f}"],
                "凱利建議注碼": [f"{max(0, kelly_h)*100:.1f}%", f"{max(0, kelly_d)*100:.1f}%", f"{max(0, kelly_a)*100:.1f}%"]
            }
            st.table(pd.DataFrame(ev_data))

        # --- 全場波膽 & 大細 ---
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("🎯 **全場波膽 Top 3**")
            scores = [(f"{i}:{j}", matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
            scores.sort(key=lambda x: x[1], reverse=True)
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

        # --- 半場及半全場分析 ---
        st.write("---")
        st.write("⏱️ **半場及半全場預測 (按全場45%估算)**")
        
        ht_home_avg = home_avg * 0.45
        ht_away_avg = away_avg * 0.45
        ht_matrix = np.zeros((max_goals+1, max_goals+1))
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                ht_matrix[i, j] = poisson.pmf(i, ht_home_avg) * poisson.pmf(j, ht_away_avg)
                
        col_ht1, col_ht2, col_ht3 = st.columns(3)
        
        with col_ht1:
            st.write("**半場主客和**")
            ht_h = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i > j)
            ht_d = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i == j)
            ht_a = sum(ht_matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i < j)
            st.write(f"主勝：{ht_h:.2%}")
            st.write(f"和局：{ht_d:.2%}")
            st.write(f"客勝：{ht_a:.2%}")
            
        with col_ht2:
            st.write("**半場波膽 Top 2**")
            ht_scores = [(f"{i}:{j}", ht_matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
            ht_scores.sort(key=lambda x: x[1], reverse=True)
            df_ht = pd.DataFrame(ht_scores[:2], columns=["波膽", "概率"])
            df_ht["概率"] = df_ht["概率"].apply(lambda x: f"{x:.2%}")
            st.dataframe(df_ht, hide_index=True, use_container_width=True)
            
        with col_ht3:
        with col_ht3:
            st.write("**半全場 Top 2**")
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
            df_htft = pd.DataFrame(htft_sorted[:2], columns=["組合", "概率"])
            df_htft["概率"] = df_htft["概率"].apply(lambda x: f"{x:.2%}")
            
            # ==========================================
            # 新增：將英文 H/D/A 替換為中文
            # ==========================================
            ht_ft_mapping = {
                "H-H": "主-主", "H-D": "主-和", "H-A": "主-客",
                "D-H": "和-主", "D-D": "和-和", "D-A": "和-客",
                "A-H": "客-主", "A-D": "客-和", "A-A": "客-客"
            }
            df_htft["組合"] = df_htft["組合"].replace(ht_ft_mapping)
            # ==========================================
            
            st.dataframe(df_htft, hide_index=True, use_container_width=True)
