import streamlit as st
import json
from datetime import datetime
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    # 👇 強制寫死，跳過 Streamlit Secrets 測試
    url = "https://dofdjvjxmgujnscemuko.supabase.co"
    key = "sb_publishable_GUU7ZYIZcBtYH6bpnI9u2A_bM5rIi9x"
    return create_client(url, key)

def save_prediction(key, data):
    """儲存預測記錄到 Supabase（如果已存在就更新）"""
    try:
        supabase = get_supabase()
        # 強制轉換數據類型，避免 Supabase 型別錯誤
        payload = {
            "key": str(key),
            "date": str(data.get('date')),
            "race": int(data.get('race', 0)), # 👈 強制轉 int，因為 Supabase 欄位係 int4
            "top_horse": str(data.get('top_horse', '')),
            "top_prob": float(data.get('top_prob', 0.0)),
            "all_horses": json.dumps(data.get('all_horses', []), ensure_ascii=False),
            "model_used": json.dumps(data.get('model_used', []), ensure_ascii=False),
            "predicted_at": str(data.get('predicted_at', datetime.now().isoformat()))
        }
        supabase.table("predictions").upsert(payload).execute()
        return True
    except Exception as e:
        # 👈 關鍵：喺前台顯示錯誤，唔再靜靜雞失敗！
        st.error(f"❌ Supabase 儲存失敗：{e}")
        return False

def load_predictions():
    """從 Supabase 讀取所有預測記錄"""
    try:
        supabase = get_supabase()
        response = supabase.table("predictions").select("*").execute()
        result = {}
        for row in response.data:
            result[row["key"]] = {
                "date": row["date"],
                "race": row["race"],
                "top_horse": row["top_horse"],
                "top_prob": row["top_prob"],
                "all_horses": json.loads(row["all_horses"]) if row["all_horses"] else [],
                "model_used": json.loads(row["model_used"]) if row["model_used"] else [],
                "predicted_at": row["predicted_at"]
            }
        return result
    except Exception as e:
        st.error(f"❌ Supabase 讀取失敗：{e}")
        return {}
