#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - Streamlit 網頁版（完整診斷版 + 數值修正）
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
# 2. 診斷：顯示排位表資訊
# ============================================================
st.subheader("📋 排位表診斷")
try:
    df_debug = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    st.write(f"✅ 成功讀取排位表，共 {len(df_debug)} 筆記錄")
    st.write(f"欄位名稱：{df_debug.columns.tolist()}")
    
    if 'race_date' in df_debug.columns:
        st.write(f"日期欄位樣本（前10個）：{df_debug['race_date'].head(10).tolist()}")
    elif '比賽日期' in df_debug.columns:
        st.write(f"日期欄位樣本（前10個）：{df_debug['比賽日期'].head(10).tolist()}")
    else:
        st.warning("找不到日期欄位")
    
    if 'race_no' in df_debug.columns:
        st.write(f"場次欄位樣本（前10個）：{df_debug['race_no'].head(10).tolist()}")
    elif '場次' in df_debug.columns:
        st.write(f"場次欄位樣本（前10個）：{df_debug['場次'].head(10).tolist()}")
    else:
        st.warning("找不到場次欄位")
        
except Exception as e:
    st.error(f"讀取排位表失敗：{e}")

st.divider()

# ============================================================
# 3. 載入模型
# ============================================================
@st.cache_resource
def load_models():
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
# 4. 預測函數（含日期和場次處理 + 數值強制轉換）
# ============================================================
def run_prediction(date_str, race_no):
    xgb_model, cat_model, rank_model = load_models()
    if xgb_model is None:
        return None, None
    
    # 讀取排位表
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    except Exception as e:
        st.error(f"讀取排位表失敗：{e}")
        return None, None
    
    # 處理日期欄位
    if 'race_date' in df.columns:
        date_col = 'race_date'
    elif '比賽日期' in df.columns:
        date_col = '比賽日期'
    else:
        st.error("找不到日期欄位")
        return None, None
    
    df[date_col] = df[date_col].astype(str).str.replace('/', '-')
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    
    # 處理場次欄位
    if 'race_no' in df.columns:
        race_col = 'race_no'
    elif '場次' in df.columns:
        race_col = '場次'
    else:
        st.error("找不到場次欄位")
        return None, None
    
    df[race_col] = df[race_col].astype(str).str.extract(r'(\d+)')[0]
    df[race_col] = pd.to_numeric(df[race_col], errors='coerce')
    df = df.dropna(subset=[race_col])
    
    # 篩選
    target = pd.to_datetime(date_str)
    race_sel = df[(df[date_col].dt.date == target.date()) & (df[race_col] == race_no)]
    
    if race_sel.empty:
        st.error(f"❌ 日期 {date_str} 第 {race_no} 場無數據")
        return None, None
    
    # 特徵準備
    features = ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']
    for f in features:
        if f not in race_sel.columns:
            race_sel[f] = 0
    X = race_sel[features].copy()
    
    # ===== 關鍵修正：強制轉換所有特徵為數值 =====
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X = X.fillna(0)
    # =============================================
    
    # 預測
    prob_xgb = xgb_model.predict_proba(X)[:, 1]
    prob_cat = cat_model.predict_proba(X)[:, 1]
    prob_final = (prob_xgb * 25 + prob_cat) / 26
    
    # 結果
    result = race_sel[['horse_id', 'draw', 'win_odds']].copy()
    try:
        name_map = pd.read_csv('horse_name_mapping.csv', encoding='utf-8-sig')
        name_dict = dict(zip(name_map['horse_id'], name_map['馬名']))
        result['馬匹名稱'] = result['horse_id'].map(name_dict).fillna(result['horse_id'])
    except:
        result['馬匹名稱'] = result['horse_id']
    
    result['預測勝率'] = prob_final
    result['值博指數'] = result['預測勝率'] / result['win_odds'].replace(0, 4.0)
    result = result.sort_values('值博指數', ascending=False)
    
    # 彩池推薦
    pool_rec = "【獨贏】\n"
    for i, row in result.head(3).iterrows():
        pool_rec += f"  {row['馬匹名稱']} (勝率 {row['預測勝率']:.2%})\n"
    
    return result, pool_rec

# ============================================================
# 5. 側邊欄
# ============================================================
with st.sidebar:
    st.header("🎯 控制面板")
    date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"))
    race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8)
    predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)

# ============================================================
# 6. 今日賽程
# ============================================================
st.subheader("📅 今日賽程")
try:
    df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    if 'race_date' in df_sched.columns:
        date_col_sched = 'race_date'
    elif '比賽日期' in df_sched.columns:
        date_col_sched = '比賽日期'
    else:
        st.warning("找不到日期欄位")
        date_col_sched = None
    if date_col_sched:
        df_sched[date_col_sched] = df_sched[date_col_sched].astype(str).str.replace('/', '-')
        df_sched[date_col_sched] = pd.to_datetime(df_sched[date_col_sched], errors='coerce')
        today = datetime.now().date()
        day_races = df_sched[df_sched[date_col_sched].dt.date == today]
        if day_races.empty:
            st.info("今日沒有賽事")
        else:
            for course in day_races['race_course'].unique():
                races = day_races[day_races['race_course'] == course]['race_no'].unique()
                st.write(f"🏟️ **{course}**：第 {', '.join(map(str, sorted(races)))} 場")
except Exception as e:
    st.warning(f"無法載入賽程：{e}")

# ============================================================
# 7. 執行預測
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
# 8. 底部
# ============================================================
st.divider()
st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("🔐 數據來源：HKJC | 系統版本：v3.0")
