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
    st.write("我哋會定期公開更新命中率，你可以喺網站主頁或相關頁面睇到實際表現。賽馬本身有隨機性，命中率會隨時間同數據累積而變化。")

with st.expander("Q3：免費定收費？"):
    st.write("免費。新用戶會有預測次數（由 free_limit 控制）。如果你想支持我哋，可以透過「❤️ 打賞支持」自願贊助，打賞屬自願性質，唔會解鎖任何 VIP 功能。")

with st.expander("Q4：點樣開始用？"):
    st.write("註冊帳號 → 登入 → 揀場次 → 睇預測。")

# ========== 二、預測相關 ==========
st.header("二、預測相關")

with st.expander("Q5：預測係點計出嚟？"):
    st.write("用三模型融合（XGBoost + CatBoost + Ranking），系統會根據場地（沙田 ST / 跑馬地 HV）自動調整權重。")

with st.expander("Q6：點解有時預測唔中？"):
    st.write("賽馬本身隨機性高，冇模型可以 100% 命中。我哋會持續改善模型同數據。")

with st.expander("Q7：可以預測邊啲場次？"):
    st.write("香港賽馬會嘅沙田同跑馬地賽事，只要排位表出咗就可以預測。")

with st.expander("Q8：預測會唔會日日更新？"):
    st.write("會。每次賽事有新排位表，我哋就會更新預測。")

with st.expander("Q9：可唔可以只睇某幾場？"):
    st.write("可以。你可以點擊場次按鈕，揀選指定場次去睇預測。")

# ========== 三、打賞支持 ==========
st.header("三、打賞支持")

with st.expander("Q10：打賞支持係咩？"):
    st.write("打賞係自願性質，純粹支持網站營運同伺服器費用。打賞唔會解鎖任何 VIP 功能，亦唔會影響你嘅預測次數。")

with st.expander("Q11：點樣打賞支持？"):
    st.write("去「❤️ 打賞支持」，輸入你想支持嘅金額，然後用 FPS 轉數快過數，再撳「我已經付款」提交。")

with st.expander("Q12：打賞要等幾耐先確認？"):
    st.write("通常即日處理，視乎管理員審核時間。管理員只會確認你嘅付款狀態，唔會加任何 VIP 天數。")

with st.expander("Q13：打賞可以退款嗎？"):
    st.write("打賞屬自願性質，一般不設退款。")

# ========== 四、彩池相關 ==========
st.header("四、彩池相關")

with st.expander("Q14：有咩彩池可以睇？"):
    st.write("單場有 9 種：獨贏、位置、連贏、位置Q、三重彩、單T、四重彩、二重彩、四連環。")

with st.expander("Q15：點解有啲彩池睇唔到？"):
    st.write("因為部分彩池屬於進階彩池，需要累積一定免費次數或者解鎖（可透過每日簽到、抽獎、商城獲得）。")

with st.expander("Q16：每個彩池會出幾多個組合？"):
    st.write("每個彩池只顯示一個推薦組合。")

# ========== 五、抽獎 / 商城 / 簽到 ==========
st.header("五、抽獎 / 商城 / 簽到")

with st.expander("Q17：抽獎幾時重置？"):
    st.write("每晚香港時間 00:00 自動重置，每日派發 1 次抽獎機會。")

with st.expander("Q18：抽獎有咩獎品？"):
    st.write("虛擬幣、VIP 天數、免費預測次數、優惠碼、自訂獎品、或者「唔中」。")

with st.expander("Q19：商城有咩買？"):
    st.write("預測次數、VIP 天數、抽獎次數、稱號、神秘盒等。")

with st.expander("Q20：商城物品可以改價錢嗎？"):
    st.write("管理員可以喺後台直接編輯價錢、庫存同名稱。")

with st.expander("Q21：每日簽到有咩獎勵？"):
    st.write("連續 7 日簽到可獲得金幣（500 / 800 / 1100 / 1400 / 1700 / 2000 / 2500），第 7 日額外送 VIP 1 日。連續中斷會重置做 1。")

# ========== 六、帳戶 / 技術 ==========
st.header("六、帳戶 / 技術")

with st.expander("Q22：點樣改密碼？"):
    st.write("登入後入「個人中心」→「更改密碼」。")

with st.expander("Q23：唔記得密碼點算？"):
    st.write("請聯絡管理員協助重置。")

with st.expander("Q24：點樣睇自己嘅預測記錄？"):
    st.write("登入後入「個人中心」→「預測記錄」。")

with st.expander("Q25：點解有時網站好慢？"):
    st.write("因為我哋用咗雲端數據庫（Supabase），每次操作都要經互聯網讀寫。通常幾秒內完成，如果持續緩慢，請稍後再試。")

with st.expander("Q26：點解預測記錄突然冇咗？"):
    st.write("我哋已經改用 Supabase 雲端數據庫，理論上數據唔會再因為網站重啟而消失。如果發現記錄唔見咗，請聯絡管理員。")

with st.expander("Q27：有冇聊天室？"):
    st.write("有。前台主頁有 Popover 彈出式聊天室，所有用戶共用一個聊天室，每 5 秒自動刷新。")

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