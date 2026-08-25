# ============================================================
# 付款審核模組 — 功能齊全版
# ============================================================

import streamlit as st
import json
import os
from datetime import datetime, timedelta
import re

# ---------- 輔助函數 ----------
def load_json(filepath, default=None):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_files():
    for f in ["payment_proofs.json", "payment_audit.json"]:
        if not os.path.exists(f):
            save_json(f, {"records": []} if f == "payment_proofs.json" else {"logs": []})
    if not os.path.exists("users.json"):
        save_json("users.json", {})

# ---------- 主頁面 ----------
def payment_review_page():
    st.header("💳 付款審核管理")
    
    # 初始化檔案
    init_files()
    
    # 權限檢查
    if not st.session_state.get("is_admin", False):
        st.error("⛔ 你沒有權限訪問此頁面")
        return
    
    # 載入數據
    proofs_data = load_json("payment_proofs.json", {"records": []})
    records = proofs_data.get("records", [])
    users_data = load_json("users.json", {})
    audit_logs = load_json("payment_audit.json", {"logs": []})
    
    # ---------- 統計卡片 ----------
    total_pending = sum(1 for r in records if r.get("status") == "pending")
    total_approved = sum(1 for r in records if r.get("status") == "approved")
    total_rejected = sum(1 for r in records if r.get("status") == "rejected")
    total_amount = sum(r.get("amount", 0) for r in records if r.get("status") == "approved")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏳ 待審批", total_pending)
    col2.metric("✅ 已批准", total_approved)
    col3.metric("❌ 已拒絕", total_rejected)
    col4.metric("💰 總收入", f"${total_amount:,}")
    
    st.divider()
    
    # ---------- 篩選與搜尋 ----------
    with st.expander("🔍 篩選與搜尋", expanded=True):
        col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
        with col_s1:
            search_term = st.text_input("搜尋用戶名 / ID", placeholder="輸入關鍵字")
        with col_s2:
            status_filter = st.selectbox(
                "狀態篩選",
                ["全部", "pending", "approved", "rejected"],
                format_func=lambda x: {"pending": "待審批", "approved": "已批准", "rejected": "已拒絕", "全部": "全部"}[x]
            )
        with col_s3:
            # 批量操作按鈕（只顯示待審批記錄時可用）
            if status_filter in ["pending", "全部"] and total_pending > 0:
                if st.button("📦 批量批准全部待審"):
                    batch_approve_all(records, users_data)
                    st.rerun()
    
    # ---------- 過濾記錄 ----------
    filtered = records.copy()
    if search_term:
        filtered = [r for r in filtered if search_term.lower() in r.get("username", "").lower() or search_term in r.get("user_id", "")]
    if status_filter != "全部":
        filtered = [r for r in filtered if r.get("status") == status_filter]
    
    if not filtered:
        st.info("📭 沒有符合條件的記錄")
        return
    
    st.subheader(f"📋 共 {len(filtered)} 條記錄")
    
    # ---------- 顯示每一條記錄 ----------
    for idx, record in enumerate(filtered):
        # 找出原始索引（用於更新）
        original_idx = records.index(record)
        status = record.get("status", "pending")
        
        with st.container():
            cols = st.columns([2, 2, 2, 1.5, 2.5])
            with cols[0]:
                st.write(f"**👤 {record.get('username', '未知')}**")
                st.caption(f"ID: `{record.get('user_id', '')}`")
                st.caption(f"📧 {record.get('email', 'N/A')}")
            with cols[1]:
                plan = record.get('plan', '未指定')
                amount = record.get('amount', 0)
                st.write(f"**{plan}**")
                st.write(f"金額：**${amount}**")
                st.caption(f"上傳時間：{record.get('upload_time', '')}")
            with cols[2]:
                # 圖片預覽
                proof_img = record.get('proof_image', '')
                if proof_img and os.path.exists(proof_img):
                    # 點擊放大（用 st.image 並設定 use_column_width）
                    st.image(proof_img, width=120, caption="點擊放大" if not st.session_state.get(f"img_expand_{original_idx}", False) else "")
                    if st.button("🔍 放大", key=f"expand_{original_idx}"):
                        st.session_state[f"img_expand_{original_idx}"] = not st.session_state.get(f"img_expand_{original_idx}", False)
                        st.rerun()
                    if st.session_state.get(f"img_expand_{original_idx}", False):
                        st.image(proof_img, width=400)
                else:
                    st.caption("無圖片")
            with cols[3]:
                # 狀態標籤
                if status == "pending":
                    st.warning("⏳ 待審批")
                elif status == "approved":
                    st.success("✅ 已批准")
                    if "expiry" in record:
                        st.caption(f"到期：{record['expiry'][:10]}")
                elif status == "rejected":
                    st.error("❌ 已拒絕")
                else:
                    st.info(status)
                # 顯示備註
                if record.get("review_notes"):
                    st.caption(f"📝 {record['review_notes']}")
            with cols[4]:
                # 操作按鈕
                if status == "pending":
                    col_a, col_r = st.columns(2)
                    with col_a:
                        if st.button("✅ 批准", key=f"approve_{original_idx}"):
                            handle_approve(original_idx, record, users_data)
                            st.rerun()
                    with col_r:
                        if st.button("❌ 拒絕", key=f"reject_{original_idx}"):
                            handle_reject(original_idx, record)
                            st.rerun()
                    # 可輸入備註
                    note_key = f"note_{original_idx}"
                    default_note = record.get("review_notes", "")
                    note_input = st.text_input("備註", value=default_note, key=note_key, placeholder="可選")
                    if note_input != default_note:
                        # 即時儲存備註（當離開輸入框時）
                        record["review_notes"] = note_input
                        save_json("payment_proofs.json", proofs_data)
                elif status == "approved":
                    # 已批准可退款（降級）
                    if st.button("↩️ 退款（降級）", key=f"refund_{original_idx}"):
                        handle_refund(original_idx, record, users_data)
                        st.rerun()
                else:
                    st.write("已處理")
            st.divider()
    
    # ---------- 操作日誌 ----------
    with st.expander("📜 操作日誌（最近20條）"):
        logs = audit_logs.get("logs", [])[-20:]
        if logs:
            for log in reversed(logs):
                st.text(f"[{log['time']}] {log['actor']} - {log['action']} - {log.get('detail', '')}")
        else:
            st.info("暫無日誌")

# ---------- 處理函數 ----------
def _log_action(action, detail=""):
    log_file = "payment_audit.json"
    data = load_json(log_file, {"logs": []})
    data["logs"].append({
        "time": datetime.now().isoformat(),
        "actor": st.session_state.get("username", "admin"),
        "action": action,
        "detail": detail
    })
    save_json(log_file, data)

def handle_approve(original_idx, record, users_data):
    # 更新 payment_proofs.json
    proofs = load_json("payment_proofs.json", {"records": []})
    proofs["records"][original_idx]["status"] = "approved"
    proofs["records"][original_idx]["review_time"] = datetime.now().isoformat()
    proofs["records"][original_idx]["reviewer"] = st.session_state.get("username", "admin")
    # 備註保留
    save_json("payment_proofs.json", proofs)
    
    # 升級用戶
    user_id = record.get("user_id")
    if user_id and user_id in users_data:
        users_data[user_id]["level"] = "付費用戶"
        plan = record.get("plan", "月費")
        days_map = {"日費": 1, "月費": 30, "季費": 90}
        days = days_map.get(plan, 30)
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        users_data[user_id]["expiry"] = expiry
        if "subscription_history" not in users_data[user_id]:
            users_data[user_id]["subscription_history"] = []
        users_data[user_id]["subscription_history"].append({
            "plan": plan,
            "amount": record.get("amount"),
            "approved_at": datetime.now().isoformat()
        })
        save_json("users.json", users_data)
        st.success(f"✅ 已批准 {record.get('username')} 並升級，有效期至 {expiry[:10]}")
        _log_action("批准付款", f"用戶 {record.get('username')} ({user_id})，方案 {plan}")
    else:
        st.warning(f"⚠️ 用戶 {user_id} 不存在於 users.json，請手動處理")
        _log_action("批准付款但用戶不存在", f"用戶ID {user_id}")

def handle_reject(original_idx, record):
    proofs = load_json("payment_proofs.json", {"records": []})
    proofs["records"][original_idx]["status"] = "rejected"
    proofs["records"][original_idx]["review_time"] = datetime.now().isoformat()
    proofs["records"][original_idx]["reviewer"] = st.session_state.get("username", "admin")
    save_json("payment_proofs.json", proofs)
    st.warning(f"❌ 已拒絕 {record.get('username')} 的申請")
    _log_action("拒絕付款", f"用戶 {record.get('username')} ({record.get('user_id')})")

def handle_refund(original_idx, record, users_data):
    # 退款：將用戶降級為免費，移除到期日
    user_id = record.get("user_id")
    if user_id and user_id in users_data:
        users_data[user_id]["level"] = "免費用戶"
        users_data[user_id].pop("expiry", None)
        save_json("users.json", users_data)
        # 同時更新付款記錄（可增加退款標記）
        proofs = load_json("payment_proofs.json", {"records": []})
        proofs["records"][original_idx]["refunded"] = True
        proofs["records"][original_idx]["refund_time"] = datetime.now().isoformat()
        save_json("payment_proofs.json", proofs)
        st.info(f"↩️ 已為 {record.get('username')} 辦理退款，用戶已降級")
        _log_action("退款", f"用戶 {record.get('username')} ({user_id})")
    else:
        st.error("❌ 無法找到該用戶")

def batch_approve_all(records, users_data):
    pending_indices = [i for i, r in enumerate(records) if r.get("status") == "pending"]
    if not pending_indices:
        st.warning("沒有待審批記錄")
        return
    for idx in pending_indices:
        handle_approve(idx, records[idx], users_data)
    st.success(f"✅ 已批量批准 {len(pending_indices)} 條記錄")
    _log_action("批量批准", f"共 {len(pending_indices)} 條")