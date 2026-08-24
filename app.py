def main():
    # 初始化 session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False

    # ----- 如果啟用註冊，未登入就顯示登入頁 -----
    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    # ----- 如果係管理員模式 -----
    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        if st.button("⬅️ 返回主頁"):
            st.session_state.show_admin = False
            st.rerun()
        return

    # ----- 主頁面（標題 + 管理按鈕）-----
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("🏇 賽馬預測系統")
        st.markdown("AI 驅動・即時預測・彩池推薦")
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')} · 36個特徵 · 三模型融合 · 六種彩池")
    with col2:
        if CONFIG["enable_admin"]:
            if st.button("🔐 後台", use_container_width=True):
                st.session_state.show_admin = True
                st.rerun()

    # ----- 側邊欄（原有控制）-----
    with st.sidebar:
        st.header("🎯 控制面板")
        # ... 你原有嘅側邊欄內容（日期、場次、預測按鈕）...
        # 注意：將側邊欄底部嘅「後台管理」按鈕刪除

    # ----- 今日賽程、預測等（原有內容）-----
    # ...
