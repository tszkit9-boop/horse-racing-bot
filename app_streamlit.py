#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - Streamlit 網頁版（直接整合預測功能）
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import sys
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier

# ============================================================
# 1. 設定頁面
# ============================================================
st.set_page_config(page_title="🏇 賽馬預測系統", layout="wide")
st.title("🏇 賽馬預測系統")
st.markdown("AI 驅動・即時預測・彩池推薦")

# ============================================================
# 2. 載入模型（用 @st.cache_data 加快速度）
# ============================================================
@st.cache_resource
def load_models():
    """載入三個模型"""
    try:
        with open('hk_racing_model.pkl', 'rb') as f:
            xgb_obj = pickle.load(f)
            xgb_model = xgb_obj[0] if isinstance(xgb_obj, tuple) else xgb_obj
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        with open('hk_ranking_model.pkl', 'rb') as f:
            rank_obj = pickle.load(f)
            rank_model = rank_obj[0] if isinstance(rank_obj, tuple) else rank_obj
        return xgb_model, cat_model, rank_model
    except Exception as e:
        st.error(f"❌ 模型載入失敗：{e}")
        return None, None, None

# ============================================================
# 3. 預測函數（直接執行，唔用 subprocess）
# ============================================================
def run_prediction(date_str, race_no):
    """直接執行預測，回傳結果 DataFrame 同彩池推薦"""
    xgb_model, cat_model, rank_model = load_models()
    if xgb_model is None:
        return None, None
    
    # 讀取排位表
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    except Exception as e:
        st.error(f"讀取排位表失敗：{e}")
        return None, None
    
    # 處理日期
    df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
    target = pd.to_datetime(date_str)
    race_sel = df[(df['race_date'].dt.date == target.date()) & (df['race_no'] == race_no)]
    
    if race_sel.empty:
        st.error(f"❌ 日期 {date_str} 第 {race_no} 場無數據")
        return None, None
    
    # 簡化版特徵生成（省略複雜特徵，直接用基本特徵）
    # 實際使用時可加入完整特徵工程
    features = ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']
    X = race_sel[features].copy()
    X = X.fillna(0)
    
    # 預測
    prob_xgb = xgb_model.predict_proba(X)[:, 1]
    prob_cat = cat_model.predict_proba(X)[:, 1]
    prob_final = (prob_xgb * 25 + prob_cat) / 26
    
    # 結果
    result = race_sel[['horse_id', 'draw', 'win_odds']].copy()
    result['馬匹名稱'] = result['horse_id']  # 如果有中文名對照可加入
    result['預測勝率'] = prob_final
    result['值博指數'] = result['預測勝率'] / result['win_odds'].replace(0, 4.0)
    result = result.sort_values('值博指數', ascending=False)
    
    # 彩池推薦（簡化版）
    pool_rec = "【獨贏】\n"
    for i, row in result.head(3).iterrows():
        pool_rec += f"  {row['馬匹名稱']} (勝率 {row['預測勝率']:.2%})\n"
    
    return result, pool_rec

# ============================================================
# 4. 側邊欄
# ============================================================
with st.sidebar:
    st.header("🎯 控制面板")
    date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"))
    race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8)
    predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)

# ============================================================
# 5. 主區域
# ============================================================
st.subheader("📅 今日賽程")
try:
    df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    df_sched['race_date'] = pd.to_datetime(df_sched['race_date'], errors='coerce')
    today = datetime.now().date()
    day_races = df_sched[df_sched['race_date'].dt.date == today]
    if day_races.empty:
        st.info("今日沒有賽事")
    else:
        for course in day_races['race_course'].unique():
            races = day_races[day_races['race_course'] == course]['race_no'].unique()
            st.write(f"🏟️ **{course}**：第 {', '.join(map(str, sorted(races)))} 場")
except:
    st.warning("無法載入賽程")

# ============================================================
# 6. 執行預測
# ============================================================
if predict_btn:
    date_str = date.strftime('%Y-%m-%d')
    with st.spinner(f"執行預測 {date_str} 第 {race_no} 場..."):
        result, pool = run_prediction(date_str, race_no)
        if result is not None:
            st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
            st.subheader("🏇 預測 TOP 5")
            display_df = result.head(5)[['馬匹名稱', 'draw', '預測勝率', '值博指數']].copy()
            display_df.columns = ['馬匹名稱', '檔位', '預測勝率', '值博指數']
            display_df['預測勝率'] = display_df['預測勝率'].apply(lambda x: f"{x:.2%}")
            st.dataframe(display_df, use_container_width=True)
            if pool:
                st.subheader("🎯 彩池推薦")
                st.text(pool)

# ============================================================
# 7. 底部
# ============================================================
st.divider()
st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("🔐 數據來源：HKJC | 系統版本：v3.0")
