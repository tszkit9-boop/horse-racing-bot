import streamlit as st
import json
from datetime import datetime
from supabase import create_client, Client

# 從 Streamlit Secrets 讀取連線資訊
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def save_prediction(key, data):
    """儲存預測記錄到 Supabase（如果已存在就更新）"""
    try:
        supabase = get_supabase()
        supabase.table("predictions").upsert({
            "key": key,
            "date": data.get('date'),
            "race": data.get('race'),
            "top_horse": data.get('top_horse'),
            "top_prob": data.get('top_prob'),
            "all_horses": json.dumps(data.get('all_horses', []), ensure_ascii=False),
            "model_used": json.dumps(data.get('model_used', []), ensure_ascii=False),
            "predicted_at": data.get('predicted_at', datetime.now().isoformat())
        }).execute()
    except Exception as e:
        print(f"⚠️ Supabase 儲存失敗：{e}")

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
        print(f"⚠️ Supabase 讀取失敗：{e}")
        return {}
