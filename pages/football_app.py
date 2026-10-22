st.set_page_config(page_title="一鍵貼上預測", page_icon="⚽", layout="wide")

# ==========================================
# 頂部導航排版 (左邊標題，右邊按鈕)
# ==========================================
col1, col2 = st.columns([8, 2])  # 左邊佔 8 份，右邊佔 2 份

with col1:
    st.title("⚽ 一鍵貼上賠率預測 (終極版)")

with col2:
    st.write("") # 加點空行讓按鈕跟標題水平對齊
    st.write("") 
    # 使用 Streamlit 的頁面鏈接組件跳轉回主頁
    # 注意：這裡的 "app_streamlit.py" 必須跟你 GitHub 主程式的檔案名稱完全一致
    st.page_link("app_streamlit.py", label="🏇 前往賽馬預測", icon="🏇")

st.markdown("請直接將馬會嘅賽事及賠率 **Copy & Paste** 落下面，系統會自動分析！")
# ==========================================
