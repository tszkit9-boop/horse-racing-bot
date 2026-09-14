import streamlit as st

st.set_page_config(
    page_title="常見問題 | SHTSN",
    page_icon="❓",
    layout="wide"
)

st.title("❓ 常見問題 FAQ")
st.caption("SHTSN 賽馬預測系統")

# ========== 一、一般問題 ==========
st.header("一、一般問題")

with st.expander("Q1：SHTSN 係咩嚟？"):
    st.write("SHTSN 係一個 AI 賽馬預測系統，用 XGBoost、CatBoost、Ranking 三模型融合，提供賽馬預測同彩池推薦。")

with st.expander("Q2：呢個系統準唔準？"):
    st.write("根據 2026-09-13 統計，場次命中率約 44.4%，馬匹命中率約 16.7%。我哋會每日公開更新，唔會隱瞞。")

with st.expander("Q3：免費定收費？"):
    st.write("有免費預測次數（由 free_limit 控制），付費可解鎖更多彩池同無限預測。")

with st.expander("Q4：點樣開始用？"):
    st.write("註冊帳號 → 登入 → 揀場次 → 睇預測。")

# ========== 二、預測相關 ==========
st.header("二、預測相關")

with st.expander("Q5：預測係點計出嚟？"):
    st.write("用三模型融合（XGBoost + CatBoost + Ranking），權重為 XGB 0.3、Cat 0.5、Rank 0.2。")

with st.expander("Q6：點解有時預測唔中？"):
    st.write("賽馬本身隨機性高，冇模型可以 100% 命中。我哋會持續改善模型同數據。")

with st.expander("Q7：可以預測邊啲場次？"):
    st.write("香港賽馬會嘅沙田同跑馬地賽事，只要排位表出咗就可以預測。")

with st.expander("Q8：預測會唔會日日更新？"):
    st.write("會。每次賽事有新排位表，我哋就會更新預測。")

with st.expander("Q9：可唔可以只睇某幾場？"):
    st.write("可以。你可以揀指定場次，或者用「一鍵預測所有場次」。")

# ========== 三、會員 / 收費 ==========
st.header("三、會員 / 收費")

with st.expander("Q10：有咩會員級別？"):
    st.write("free（免費）、paid（日費/月費）、VIP（季費/年費）、super_admin（管理員）。")

with st.expander("Q11：free 同 paid 有咩分別？"):
    st.write("free 有限預測次數，只可睇獨贏、位置、連贏、位置Q；paid 無限預測，可睇三重彩、單T；VIP 可睇全部彩池。")

with st.expander("Q12：點樣付款？"):
    st.write("支援 FPS 轉數快，提交付款申請後由管理員審核，批准即自動升級。")

with st.expander("Q13：付款要等幾耐？"):
    st.write("通常即日處理，視乎管理員審核時間。")

with st.expander("Q14：可以退款嗎？"):
    st.write("虛擬服務一般唔設退款，如有特殊情況請聯絡管理員。")

# ========== 四、彩池相關 ==========
st.header("四、彩池相關")

with st.expander("Q15：有咩彩池可以睇？"):
    st.write("單場有 9 種：獨贏、位置、連贏、位置Q、三重彩、單T、四重彩、二重彩、四連環；跨場有孖寶、三寶、六環彩。")

with st.expander("Q16：點解有啲彩池睇唔到？"):
    st.write("彩池按會員級別開放，升級會員就可以解鎖。")

with st.expander("Q17：跨場彩池點用？"):
    st.write("先執行「一鍵預測所有場次」，再手動揀起始場次，就會顯示孖寶、三寶、六環彩。")

with st.expander("Q18：每個彩池會出幾多個組合？"):
    st.write("每個彩池只顯示一個推薦組合。")

# ========== 五、抽獎 / 商城 ==========
st.header("五、抽獎 / 商城")

with st.expander("Q19：抽獎幾時重置？"):
    st.write("每晚香港時間 00:00 自動重置，每日派發 1 次抽獎機會。")

with st.expander("Q20：抽獎有咩獎品？"):
    st.write("虛擬幣、VIP 天數、免費預測次數、優惠碼、自訂獎品、或者「唔中」。")

with st.expander("Q21：商城有咩買？"):
    st.write("預測次數、VIP 天數、抽獎次數、稱號、神秘盒等。")

with st.expander("Q22：商城物品可以改價錢嗎？"):
    st.write("管理員可以喺後台直接編輯價錢、庫存同名稱。")

# ========== 六、帳戶 / 技術 ==========
st.header("六、帳戶 / 技術")

with st.expander("Q23：點樣改密碼？"):
    st.write("登入後入「個人中心」→「更改密碼」。")

with st.expander("Q24：唔記得密碼點算？"):
    st.write("請聯絡管理員協助重置。")

with st.expander("Q25：點樣睇自己嘅預測記錄？"):
    st.write("登入後入「個人中心」→「預測記錄」。")

with st.expander("Q26：點解有時網站好慢？"):
    st.write("可能係同時使用人數多，或者 Streamlit Cloud 負載高，請稍後再試。")

with st.expander("Q27：點解預測記錄突然冇咗？"):
    st.write("Streamlit Cloud 重新部署時，本地寫入嘅檔案可能會被重置。建議定期備份。")

# ========== 七、邀請 / 獎勵 ==========
st.header("七、邀請 / 獎勵")

with st.expander("Q28：點樣邀請朋友？"):
    st.write("喺「個人中心」攞你嘅邀請碼，分享俾朋友註冊時填寫。")

with st.expander("Q29：邀請有咩獎勵？"):
    st.write("多級下線獎勵：level1 +5 次、level2 +2 次、level3 +1 次。")

with st.expander("Q30：點樣升級等級？"):
    st.write("透過預測、邀請、消費等累積，等級由銅牌 → 銀牌 → 金牌 → 鑽石 → 傳說。")

# ========== 八、法律 / 免責 ==========
st.header("八、法律 / 免責")

with st.expander("Q31：呢個系統係咪賭博？"):
    st.write("SHTSN 係數據分析同預測工具，唔涉及直接投注。用戶需自行決定是否投注，並自負風險。")

with st.expander("Q32：預測結果有冇保證？"):
    st.write("冇。賽馬有隨機性，預測僅供參考，唔構成任何投注建議。")

with st.expander("Q33：資料會唔會外洩？"):
    st.write("我哋會盡力保護用戶資料，但請避免使用重要密碼。")

st.divider()
st.caption("© 2026 SHTSN 賽馬預測系統")