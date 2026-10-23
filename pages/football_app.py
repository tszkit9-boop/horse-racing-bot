import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import joblib
from scipy.stats import poisson
from supabase import create_client, Client

# ==========================================
# 🧠 載入 AI 模型 (使用 cache_resource 防止每次撳掣都重新載入)
# ==========================================
@st.cache_resource
def load_ai_model():
    if os.path.exists("football_ensemble.pkl"):
        try:
            return joblib.load("football_ensemble.pkl")
        except Exception as e:
            st.error(f"AI 模型載入失敗：{e}")
    return None

ai_model = load_ai_model()
# ==========================================
# 頁面設定
# ==========================================
st.set_page_config(page_title="一鍵貼上預測", page_icon="⚽", layout="wide")

# ==========================================
# ☁️ 連接 Supabase (請填入你真實嘅 URL 同 Key)
# ==========================================
SUPABASE_URL = "https://fewanagxvezelufmuggq.supabase.co"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("⚠️ Supabase 連接失敗，請檢查 URL 同 Key 是否正確。")

# ==========================================
# 🎨 全局美化 CSS
# ==========================================
st.markdown("""
<style>
.stApp { background-color: #f8f9fa; }
.stTextArea textarea {
    font-size: 16px !important; border-radius: 10px !important;
    border: 2px solid #e0e0e0 !important; padding: 15px !important;
    background-color: #ffffff !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
}
.stTextArea textarea:focus {
    border-color: #1f77b4 !important; box-shadow: 0 4px 12px rgba(31,119,180,0.2) !important;
}
.stButton button {
    background: linear-gradient(135deg, #1f77b4 0%, #2b5c8f 100%) !important;
    color: white !important; border-radius: 8px !important;
    font-weight: bold !important; font-size: 16px !important;
    padding: 10px 24px !important; border: none !important;
    transition: all 0.3s ease !important;
}
.stButton button:hover {
    transform: translateY(-2px) !important; box-shadow: 0 5px 15px rgba(31,119,180,0.4) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important; border-radius: 12px !important;
    box-shadow: 0 6px 16px rgba(0,0,0,0.06) !important; padding: 20px !important;
    margin-bottom: 20px !important; border: 1px solid #f0f0f0 !important;
}
div[data-testid="stMetricValue"] {
    font-size: 28px !important; font-weight: bold !important; color: #2c3e50 !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 頂部導航
# ==========================================
col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([5, 1, 1, 1.2, 1])

with col_nav1:
    st.title("⚽ 一鍵貼上賠率預測 (終極版)")

with col_nav2:
    if st.button("❓ 常見問題", use_container_width=True, key="faq_btn_football"):
        st.switch_page("pages/FAQ.py")

with col_nav3:
    if st.button("🏇 前往賽馬", use_container_width=True, key="go_horse_btn"):
        st.switch_page("app_streamlit.py")

with col_nav4:
    if st.session_state.get('logged_in', False):
        username = st.session_state.get('username', '用戶')
        group = st.session_state.get('group', 'free')
        level = st.session_state.get('level', '🥉 銅牌會員')
        
        with st.popover("👤 個人中心", use_container_width=True):
            st.markdown(f"### 👤 {username}")
            st.markdown(f"**級別**：{group.upper()}　|　**等級**：{level}")
            st.divider()
            
            # --- 足球預測記錄 (從 Supabase 讀取) ---
            st.markdown("#### ⚽ 足球預測記錄 (最近10場)")
            try:
                response = supabase.table("football_predictions").select("*").eq("username", username).order("created_at", desc=True).limit(10).execute()
                records = response.data
                
                if records:
                    df_rec = pd.DataFrame(records)
                    df_show = df_rec[['match_date', 'home_team', 'away_team', 'predicted_result']].copy()
                    df_show.columns = ['日期', '主隊', '客隊', '預測賽果']
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                else:
                    st.info("📭 暫無足球預測記錄")
            except Exception as e:
                st.warning("未能讀取記錄，請確保 Supabase 已建立 Table。")

with col_nav5:
    if st.session_state.get('logged_in', False):
        if st.button("🚪 登出", use_container_width=True, key="logout_football"):
            for k in ['logged_in', 'username', 'role', 'group', 'level']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

# ==========================================
# 輸入區
# ==========================================
with st.container(border=True):
    st.subheader("📋 請貼上賽事資料")
    st.markdown("<span style='color: #666; font-size: 14px;'>支援任何格式（打直、打橫、連埋一齊都得），直接喺馬會 Copy 一大段掟落嚟：</span>", unsafe_allow_html=True)
    
    default_text = """法國 比利時 1.32 4.60 6.20
意大利 土耳其 1.25 5.00 7.50"""
    pasted_text = st.text_area("貼上資料：", value=default_text, height=200, label_visibility="collapsed")

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
    
    for match in matches:
        home_team, away_team, odds_h_str, odds_d_str, odds_a_str = match
        
        home_team = re.sub(r'(?i)\bvs\b|對', '', home_team).strip()
        away_team = re.sub(r'(?i)\bvs\b|對', '', away_team).strip()
        
        odds_h = float(odds_h_str)
        odds_d = float(odds_d_str)
        odds_a = float(odds_a_str)
        
        # 1. 計算市場隱含概率
        imp_h, imp_d, imp_a = 1/odds_h, 1/odds_d, 1/odds_a
        total = imp_h + imp_d + imp_a
        prob_h, prob_d, prob_a = imp_h/total, imp_d/total, imp_a/total

        # ==========================================
        # 🚀 Level 1：讀取基本面數據
        # ==========================================
        home_avg = None
        away_avg = None
        
        if os.path.exists("team_stats_summary.csv"):
            try:
                df_stats = pd.read_csv("team_stats_summary.csv")
                team_mapping = {
                    "曼聯": "Man United", "曼城": "Man City", "利物浦": "Liverpool", "阿仙奴": "Arsenal",
                    "車路士": "Chelsea", "熱刺": "Tottenham", "愛華頓": "Everton", "紐卡素": "Newcastle",
                    "李斯特城": "Leicester", "韋斯咸": "West Ham", "水晶宮": "Crystal Palace", "修咸頓": "Southampton",
                    "般尼": "Burnley", "屈福特": "Watford", "般尼茅夫": "Bournemouth", "諾域治": "Norwich",
                    "史雲斯": "Swansea", "史篤城": "Stoke", "西布朗": "West Brom", "新特蘭": "Sunderland",
                    "阿士東維拉": "Aston Villa", "皇家馬德里": "Real Madrid", "巴塞隆拿": "Barcelona",
                    "拜仁慕尼黑": "Bayern Munich", "祖雲達斯": "Juventus", "巴黎聖日耳門": "Paris SG",
                    "多蒙特": "Dortmund", "法國": "France", "比利時": "Belgium", "意大利": "Italy", "土耳其": "Turkey"
                }
                
                eng_home = team_mapping.get(home_team, home_team)
                eng_away = team_mapping.get(away_team, away_team)
                
                h_row = df_stats[df_stats['Team'].str.lower() == eng_home.lower()]
                a_row = df_stats[df_stats['Team'].str.lower() == eng_away.lower()]
                
                if not h_row.empty and not a_row.empty:
                    league_avg = 1.35
                    h_attack = h_row['AvgScored'].values[0]
                    h_defense = h_row['AvgConceded'].values[0]
                    a_attack = a_row['AvgScored'].values[0]
                    a_defense = a_row['AvgConceded'].values[0]
                    
                    home_avg = (h_attack * a_defense) / league_avg
                    away_avg = (a_attack * h_defense) / league_avg
                    
                    st.info(f"📊 **已載入基本面數據**：{eng_home} 場均入球 {h_attack:.2f} / 失球 {h_defense:.2f}；{eng_away} 場均入球 {a_attack:.2f} / 失球 {a_defense:.2f}")
                else:
                    st.warning(f"⚠️ 數據庫搵唔到隊名 ({eng_home} vs {eng_away})，改用賠率反推。")
            except Exception as e:
                pass

        if not home_avg or not away_avg:
            home_avg = prob_h * 2.5 + 0.1
            away_avg = prob_a * 2.5 + 0.1

        # 3. 建立全場泊松矩陣
        max_goals = 6
        matrix = np.zeros((max_goals+1, max_goals+1))
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                matrix[i, j] = poisson.pmf(i, home_avg) * poisson.pmf(j, away_avg)

        # 計算模型概率
        model_prob_h = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i > j)
        model_prob_d = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i == j)
        model_prob_a = sum(matrix[i][j] for i in range(max_goals+1) for j in range(max_goals+1) if i < j)

        # 用外框包住每場賽事
        with st.container(border=True):
            st.header(f"🏆 {home_team} vs {away_team}")
            
            # ==========================================
            # 🚀 Level 2 升級：市場 vs 模型概率
            # ==========================================
            st.markdown("### 📊 市場賠率 vs 模型預測 (雙軌對比)")
            col_cmp1, col_cmp2, col_cmp3 = st.columns(3)
            
            with col_cmp1:
                st.metric("主勝 (市場)", f"{prob_h:.2%}", f"賠率: {odds_h}")
                st.metric("主勝 (模型)", f"{model_prob_h:.2%}", delta=f"{(model_prob_h - prob_h):+.2%}", delta_color="normal")
            with col_cmp2:
                st.metric("和局 (市場)", f"{prob_d:.2%}", f"賠率: {odds_d}")
                st.metric("和局 (模型)", f"{model_prob_d:.2%}", delta=f"{(model_prob_d - prob_d):+.2%}", delta_color="normal")
            with col_cmp3:
                st.metric("客勝 (市場)", f"{prob_a:.2%}", f"賠率: {odds_a}")
                st.metric("客勝 (模型)", f"{model_prob_a:.2%}", delta=f"{(model_prob_a - prob_a):+.2%}", delta_color="normal")

            # ==========================================
            # 📥 新增：保存預測至 Supabase
            # ==========================================
            col_save1, col_save2 = st.columns([1, 4])
            with col_save1:
                if st.button("📥 保存此預測", key=f"save_{home_team}_{away_team}"):
                    if st.session_state.get('logged_in', False):
                        username = st.session_state.get('username', 'unknown')
                        max_prob = max(model_prob_h, model_prob_d, model_prob_a)
                        if max_prob == model_prob_h:
                            pred_res = "主勝"
                        elif max_prob == model_prob_d:
                            pred_res = "和局"
                        else:
                            pred_res = "客勝"
                            
                        data = {
                            "username": username,
                            "match_date": pd.Timestamp.now().strftime('%Y-%m-%d'),
                            "home_team": home_team, "away_team": away_team,
                            "odds_h": odds_h, "odds_d": odds_d, "odds_a": odds_a,
                            "prob_h": round(prob_h, 4), "prob_d": round(prob_d, 4), "prob_a": round(prob_a, 4),
                            "model_prob_h": round(model_prob_h, 4), "model_prob_d": round(model_prob_d, 4), "model_prob_a": round(model_prob_a, 4),
                            "predicted_result": pred_res, "bet_type": "主客和"
                        }
                        try:
                            supabase.table("football_predictions").insert(data).execute()
                            st.success("✅ 已成功保存至雲端！")
                        except Exception as e:
                            st.error(f"❌ 保存失敗：{e}")
                    else:
                        st.warning("⚠️ 請先登入！")

            # --- EV & 凱利 ---
            ev_h = (model_prob_h * odds_h) - 1
            ev_d = (model_prob_d * odds_d) - 1
            ev_a = (model_prob_a * odds_a) - 1
            
            kelly_h = (model_prob_h * odds_h - 1) / (odds_h - 1) if odds_h > 1 else 0
            kelly_d = (model_prob_d * odds_d - 1) / (odds_d - 1) if odds_d > 1 else 0
            kelly_a = (model_prob_a * odds_a - 1) / (odds_a - 1) if odds_a > 1 else 0

            with st.expander("💰 展開查看：基於模型概率嘅投注價值 (EV) 及 凱利建議注碼", expanded=False):
                ev_data = {
                    "選項": [f"主勝 ({home_team})", "和局", f"客勝 ({away_team})"],
                    "市場概率": [f"{prob_h:.2%}", f"{prob_d:.2%}", f"{prob_a:.2%}"],
                    "模型概率": [f"{model_prob_h:.2%}", f"{model_prob_d:.2%}", f"{model_prob_a:.2%}"],
                    "EV (期望值)": [f"{ev_h:+.2f}", f"{ev_d:+.2f}", f"{ev_a:+.2f}"],
                    "凱利建議注碼": [f"{max(0, kelly_h)*100:.1f}%", f"{max(0, kelly_d)*100:.1f}%", f"{max(0, kelly_a)*100:.1f}%"]
                }
                st.table(pd.DataFrame(ev_data))

            st.divider()

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

            st.divider()

            # --- 半場及半全場 ---
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
                st.write(f"主勝：**{ht_h:.2%}**")
                st.write(f"和局：**{ht_d:.2%}**")
                st.write(f"客勝：**{ht_a:.2%}**")
                
            with col_ht2:
                st.write("**半場波膽 Top 2**")
                ht_scores = [(f"{i}:{j}", ht_matrix[i][j]) for i in range(max_goals+1) for j in range(max_goals+1)]
                ht_scores.sort(key=lambda x: x[1], reverse=True)
                df_ht = pd.DataFrame(ht_scores[:2], columns=["波膽", "概率"])
                df_ht["概率"] = df_ht["概率"].apply(lambda x: f"{x:.2%}")
                st.dataframe(df_ht, hide_index=True, use_container_width=True)
                
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
                
                ht_ft_mapping = {
                    "H-H": "主-主", "H-D": "主-和", "H-A": "主-客",
                    "D-H": "和-主", "D-D": "和-和", "D-A": "和-客",
                    "A-H": "客-主", "A-D": "客-和", "A-A": "客-客"
                }
                df_htft["組合"] = df_htft["組合"].replace(ht_ft_mapping)
                st.dataframe(df_htft, hide_index=True, use_container_width=True)

        st.write("")
