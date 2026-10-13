#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Accuracy_Report.py - 命中率報告頁面
分場地顯示（沙田、跑馬地分開）
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from database import get_supabase

st.set_page_config(page_title="命中率報告", page_icon="📊")

st.title("📊 命中率報告")
st.caption("對比預測結果同實際賽果，分場地統計 Top-1 同 Top-3 命中率。")

# ===== 權限檢查 =====
user_role = st.session_state.get('role', 'free')
if user_role not in ['admin', 'super_admin']:
    st.error("❌ 只有管理員可以查看此頁面")
    st.stop()


# ===== 讀取預測記錄 =====
@st.cache_data(ttl=300)
def load_predictions():
    try:
        supabase = get_supabase()
        response = supabase.table("predictions").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ 讀取預測記錄失敗：{e}")
        return pd.DataFrame()


# ===== 讀取賽果 =====
@st.cache_data(ttl=300)
def load_results():
    try:
        df = pd.read_csv("race_results_clean.csv", encoding="utf-8-sig", low_memory=False)
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
        df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce').fillna(0).astype(int)
        df['finish_position'] = pd.to_numeric(df['finish_position'], errors='coerce')
        df = df.dropna(subset=['race_date', 'finish_position'])
        return df
    except Exception as e:
        st.error(f"❌ 讀取賽果失敗：{e}")
        return pd.DataFrame()


# ===== 判斷場地 =====
def get_venue(race_date_str):
    """根據日期判斷場地：星期三 = HV，其他 = ST"""
    try:
        d = pd.to_datetime(race_date_str)
        return 'HV' if d.weekday() == 2 else 'ST'
    except Exception:
        return 'ST'


# ===== 主邏輯 =====
with st.spinner("🔧 計算命中率中..."):
    pred_df = load_predictions()
    results_df = load_results()

if pred_df.empty or results_df.empty:
    st.warning("⚠️ 冇足夠數據")
    st.stop()

# 逐條預測對比
rows = []
for _, pred in pred_df.iterrows():
    pred_date = pred.get('date', '')
    pred_race = pred.get('race', 0)
    top_horse = pred.get('top_horse', '')
    all_horses_raw = pred.get('all_horses', '')
    if isinstance(all_horses_raw, str):
        try:
            all_horses = json.loads(all_horses_raw)
        except Exception:
            all_horses = []
    else:
        all_horses = all_horses_raw if isinstance(all_horses_raw, list) else []

    # 搵返該場實際賽果
    sub = results_df[
        (results_df['race_date'].dt.strftime('%Y-%m-%d') == pred_date) &
        (results_df['race_no'] == pred_race)
    ]
    if sub.empty:
        continue

    winner_row = sub[sub['finish_position'] == 1]
    if winner_row.empty:
        continue
    actual_winner = winner_row.iloc[0]['horse_name']

    # Top-1 命中：top_horse 係咪實際頭馬
    top1_hit = (top_horse == actual_winner)

    # Top-3 命中：all_horses 前 3 名有冇包含實際頭馬
    top3_hit = (actual_winner in all_horses[:3])

    venue = get_venue(pred_date)
    rows.append({
        'date': pred_date,
        'race': pred_race,
        'venue': venue,
        'top_horse': top_horse,
        'actual_winner': actual_winner,
        'top1_hit': top1_hit,
        'top3_hit': top3_hit,
    })

detail_df = pd.DataFrame(rows)

if detail_df.empty:
    st.warning("⚠️ 冇匹配到任何預測同賽果")
    st.stop()

# ===== 分場地統計 =====
st.divider()
st.subheader("📊 分場地命中率")

for venue in ['ST', 'HV']:
    venue_df = detail_df[detail_df['venue'] == venue]
    if venue_df.empty:
        continue

    total = len(venue_df)
    top1_hits = int(venue_df['top1_hit'].sum())
    top3_hits = int(venue_df['top3_hit'].sum())

    venue_name = '沙田（ST）' if venue == 'ST' else '跑馬地（HV）'
    st.markdown(f"### {venue_name}")
    col1, col2, col3 = st.columns(3)
    col1.metric("總場次", f"{total}")
    col2.metric("Top-1 命中", f"{top1_hits}（{top1_hits/total:.1%}）")
    col3.metric("Top-3 命中", f"{top3_hits}（{top3_hits/total:.1%}）")

# ===== 整體統計 =====
st.divider()
st.subheader("📈 整體命中率")

total = len(detail_df)
top1_hits = int(detail_df['top1_hit'].sum())
top3_hits = int(detail_df['top3_hit'].sum())

col1, col2, col3 = st.columns(3)
col1.metric("總場次", f"{total}")
col2.metric("Top-1 命中", f"{top1_hits}（{top1_hits/total:.1%}）")
col3.metric("Top-3 命中", f"{top3_hits}（{top3_hits/total:.1%}）")

# ===== 詳細記錄 =====
st.divider()
st.subheader("📋 詳細記錄")

# 篩選器
venue_filter = st.selectbox("篩選場地", ["全部", "沙田（ST）", "跑馬地（HV）"])
if venue_filter == "沙田（ST）":
    display_df = detail_df[detail_df['venue'] == 'ST']
elif venue_filter == "跑馬地（HV）":
    display_df = detail_df[detail_df['venue'] == 'HV']
else:
    display_df = detail_df

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ===== 匯出 CSV =====
st.divider()
csv = detail_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 下載完整 CSV",
    data=csv,
    file_name="accuracy_report.csv",
    mime="text/csv"
)