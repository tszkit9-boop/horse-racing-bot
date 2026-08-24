#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - Streamlit 網頁版（Cloud 修正版）
"""

import streamlit as st
import pandas as pd
import subprocess
import os
import sys
from datetime import datetime

st.set_page_config(page_title="🏇 賽馬預測系統", layout="wide")

# 標題
st.title("🏇 賽馬預測系統")
st.markdown("AI 驅動・即時預測・彩池推薦")

# ============================================================
# 設定工作目錄（Cloud 適用）
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# 除錯：顯示當前目錄（可選）
# st.write(f"當前工作目錄：{os.getcwd()}")

# ============================================================
# 側邊欄控制
# ============================================================
with st.sidebar:
    st.header("🎯 控制面板")
    
    # 日期選擇
    date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"))
    
    # 場次選擇
    race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8)
    
    # 按鈕
    predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)
    compare_btn = st.button("📊 賽果對比", use_container_width=True)
    
    st.divider()
    
    # 系統狀態
    st.caption(f"📁 工作目錄：{os.getcwd()}")

# ============================================================
# 主區域
# ============================================================
col1, col2 = st.columns([2, 1])

# 今日賽程
with col1:
    st.subheader("📅 今日賽程")
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
        today = datetime.now().date()
        day_races = df[df['race_date'].dt.date == today]
        if day_races.empty:
            st.info("今日沒有賽事")
        else:
            for course in day_races['race_course'].unique():
                races = day_races[day_races['race_course'] == course]['race_no'].unique()
                st.write(f"🏟️ **{course}**：第 {', '.join(map(str, sorted(races)))} 場")
    except Exception as e:
        st.warning(f"無法載入賽程：{e}")

# ============================================================
# 預測功能
# ============================================================
if predict_btn:
    with st.spinner("執行預測中..."):
        date_str = date.strftime('%Y-%m-%d')
        cmd = ['python', 'predict_race_card.py', '--date', date_str, '--race', str(race_no)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
            
            # 讀取預測結果
            try:
                df = pd.read_csv('prediction_result.csv')
                
                # 顯示 TOP 5
                st.subheader("🏇 預測 TOP 5")
                display_df = df.head(5)[['馬匹名稱', '檔位', '預測勝率', '值博指數']].copy()
                display_df['預測勝率'] = display_df['預測勝率'].apply(lambda x: f"{x:.2%}")
                display_df['值博指數'] = display_df['值博指數'].apply(lambda x: f"{x:.4f}")
                st.dataframe(display_df, use_container_width=True)
                
                # 彩池推薦
                try:
                    with open('pool_recommendations.txt', 'r', encoding='utf-8') as f:
                        pool = f.read()
                    st.subheader("🎯 彩池推薦")
                    st.text(pool)
                except:
                    pass
            except Exception as e:
                st.error(f"讀取結果失敗：{e}")
        else:
            st.error(f"預測失敗：{result.stderr[:200]}")

# ============================================================
# 賽果對比功能
# ============================================================
if compare_btn:
    with st.spinner("執行對比中..."):
        date_str = date.strftime('%Y-%m-%d')
        cmd = ['python', 'compare_results.py', '--date', date_str]
        if race_no:
            cmd.extend(['--race', str(race_no)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            try:
                with open('compare_report.txt', 'r', encoding='utf-8') as f:
                    report = f.read()
                st.subheader("📊 賽果對比報告")
                st.text(report)
            except:
                pass
        else:
            st.error(f"對比失敗：{result.stderr[:200]}")

# ============================================================
# 底部資訊
# ============================================================
st.divider()
st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("🔐 數據來源：HKJC | 系統版本：v3.0")