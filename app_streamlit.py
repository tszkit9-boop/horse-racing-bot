#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 終極除錯版（強制顯示所有錯誤）
"""

import streamlit as st
import sys
import traceback

# 強制顯示所有錯誤
st.set_page_config(page_title="🏇 賽馬預測系統", layout="wide")
st.title("🏇 賽馬預測系統 (除錯模式)")
st.warning("⚠️ 除錯模式已啟用，所有錯誤會直接顯示")

# 匯入套件（如果失敗會顯示錯誤）
try:
    import pandas as pd
    import numpy as np
    import pickle
    import os
    from datetime import datetime
    from catboost import CatBoostClassifier
    st.success("✅ 所有套件匯入成功")
except Exception as e:
    st.error(f"❌ 套件匯入失敗：{e}")
    st.code(traceback.format_exc())
    st.stop()

# ============================================================
# 側邊欄
# ============================================================
with st.sidebar:
    st.header("🎯 控制面板")
    date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-03-02"))
    race_no = st.selectbox("🏇 選擇場次", list(range(1, 10)), index=8)
    predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)

# ============================================================
# 執行預測（所有錯誤直接顯示）
# ============================================================
if predict_btn:
    st.divider()
    st.subheader("📊 執行日誌")
    
    date_str = date.strftime('%Y-%m-%d')
    log = st.empty()
    
    def log_message(msg):
        log.text(f"🔍 {msg}")
    
    try:
        log_message("Step 1: 載入模型中...")
        
        # 載入 XGBoost 模型
        with open('hk_racing_model.pkl', 'rb') as f:
            xgb_obj = pickle.load(f)
            xgb_model = xgb_obj[0] if isinstance(xgb_obj, tuple) else xgb_obj
        log_message("✅ XGBoost 模型載入成功")
        
        # 載入 CatBoost 模型
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        log_message("✅ CatBoost 模型載入成功")
        
        # 載入排名模型
        with open('hk_ranking_model.pkl', 'rb') as f:
            rank_obj = pickle.load(f)
            rank_model = rank_obj[0] if isinstance(rank_obj, tuple) else rank_obj
        log_message("✅ 排名模型載入成功")
        
        log_message("Step 2: 讀取排位表...")
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        log_message(f"✅ 排位表讀取成功，共 {len(df)} 筆")
        
        # 簡單測試：顯示排位表頭幾行
        st.write("### 排位表頭 5 行")
        st.dataframe(df.head(5))
        
        # 檢查日期
        log_message("Step 3: 檢查日期...")
        if 'race_date' in df.columns:
            dates = df['race_date'].unique()
            st.write(f"可用日期：{dates[:10]}")
            log_message(f"✅ 找到日期欄位，共 {len(dates)} 個獨特日期")
        else:
            st.error("❌ 找不到 race_date 欄位")
            st.stop()
        
        # 檢查場次
        log_message("Step 4: 檢查場次...")
        if 'race_no' in df.columns:
            races = df['race_no'].unique()
            st.write(f"可用場次：{races[:10]}")
            log_message(f"✅ 找到場次欄位，共 {len(races)} 個獨特場次")
        else:
            st.error("❌ 找不到 race_no 欄位")
            st.stop()
        
        # 篩選指定日期和場次
        log_message(f"Step 5: 篩選 {date_str} 第 {race_no} 場...")
        target = pd.to_datetime(date_str)
        
        # 嘗試標準化日期
        if 'race_date' in df.columns:
            df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
        
        # 標準化場次
        if 'race_no' in df.columns:
            df['race_no'] = df['race_no'].astype(str).str.extract(r'(\d+)')[0]
            df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce')
        
        race_sel = df[(df['race_date'].dt.date == target.date()) & (df['race_no'] == race_no)]
        
        if race_sel.empty:
            st.error(f"❌ 日期 {date_str} 第 {race_no} 場無數據")
            st.write("### 資料診斷")
            st.write(f"日期範圍：{df['race_date'].min()} 至 {df['race_date'].max()}")
            st.write(f"場次範圍：{df['race_no'].min()} 至 {df['race_no'].max()}")
            st.stop()
        
        st.success(f"✅ 找到 {len(race_sel)} 匹馬")
        st.dataframe(race_sel[['horse_id', 'draw', 'act_wt', 'win_odds']].head())
        
        log_message("Step 6: 載入歷史數據...")
        try:
            history = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
            log_message(f"✅ 歷史數據載入成功，共 {len(history)} 筆")
        except Exception as e:
            st.error(f"❌ 歷史數據載入失敗：{e}")
            st.stop()
        
        log_message("Step 7: 生成特徵...")
        # 簡化版特徵（只用 5 個基本特徵）
        features = ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']
        X = race_sel[features].copy()
        X = X.fillna(0)
        
        # 確保所有特徵都是數值
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
        
        st.write("### 特徵矩陣")
        st.dataframe(X)
        
        log_message("Step 8: 執行預測...")
        prob_xgb = xgb_model.predict_proba(X)[:, 1]
        prob_cat = cat_model.predict_proba(X)[:, 1]
        prob_final = (prob_xgb * 25 + prob_cat) / 26
        log_message("✅ 預測完成")
        
        # 顯示結果
        st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
        st.subheader("🏇 預測結果")
        
        result = race_sel[['horse_id', 'draw', 'win_odds']].copy()
        result['預測勝率'] = prob_final
        result['值博指數'] = result['預測勝率'] / result['win_odds'].replace(0, 4.0)
        result = result.sort_values('值博指數', ascending=False)
        
        display_df = result.head(5)[['horse_id', 'draw', '預測勝率', '值博指數']].copy()
        display_df.columns = ['馬匹編號', '檔位', '預測勝率', '值博指數']
        display_df['預測勝率'] = display_df['預測勝率'].apply(lambda x: f"{x:.2%}")
        st.dataframe(display_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ 預測過程中發生錯誤")
        st.code(f"錯誤類型：{type(e).__name__}\n錯誤訊息：{str(e)}\n\n詳細堆疊：\n{traceback.format_exc()}")

# ============================================================
# 底部
# ============================================================
st.divider()
st.caption("🔐 數據來源：HKJC | 系統版本：v3.0-除錯版")
