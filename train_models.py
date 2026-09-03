#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 自動訓練 XGBoost + CatBoost 模型
用法: python train_models.py
"""

import pandas as pd
import numpy as np
import pickle
import os
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from catboost import CatBoostClassifier

# ============================================================
# 1️⃣ 讀取數據
# ============================================================
print("📊 讀取數據...")

# 讀取歷史賽果（用作標籤）
results_df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig')
print(f"  賽果數據：{len(results_df)} 筆")

# 讀取排位表（用作特徵）
racecard_df = pd.read_csv("HKCJ_FULL_YEAR_DATA.csv", encoding='utf-8-sig')
print(f"  排位表：{len(racecard_df)} 筆")

# ============================================================
# 2️⃣ 合併數據（特徵 + 標籤）
# ============================================================
print("🔗 合併數據...")

# 標準化欄位（跟 app_streamlit.py 一致）
def standardize_columns(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course',
        '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
        '比賽日期': 'race_date'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    return df

racecard_df = standardize_columns(racecard_df)
results_df = standardize_columns(results_df)

# 確保日期格式
# ---- 完整修復代碼開始 ----

# 1. 檢查並刪除所有重複嘅欄位名（保留第一個出現嘅）
# 呢步可以徹底解決 "cannot assemble with duplicate keys" 嘅問題
racecard_df = racecard_df.loc[:, ~racecard_df.columns.duplicated()]

# 2. 重置索引，防止因為索引重複而產生其他合併錯誤
racecard_df = racecard_df.reset_index(drop=True)

# 3. 安全地將 race_date 轉換成日期格式 (遇到無法解析嘅日期會變成 NaT，而唔會令程式崩潰)
racecard_df['race_date'] = pd.to_datetime(racecard_df['race_date'], errors='coerce')

# ---- 完整修復代碼結束 ----
results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')

# 合併：用 race_date, race_no, horse_name 做 key
merged = racecard_df.merge(
    results_df[['race_date', 'race_no', 'horse_name', 'finish_position']],
    on=['race_date', 'race_no', 'horse_name'],
    how='inner'
)
print(f"  合併後：{len(merged)} 筆記錄")

if merged.empty:
    print("❌ 無數據可訓練，請確認 CSV 檔案齊全")
    exit(1)

# 標籤：頭馬（finish_position == 1）
merged['target'] = (merged['finish_position'] == 1).astype(int)

# ============================================================
# 3️⃣ 特徵工程（跟 app_streamlit.py 一致）
# ============================================================
print("🔧 特徵工程...")

FEATURES_EN = [
    'draw', 'act_wt', 'distance', 'rtg', 'avg_rank_last3',
    'jockey_win_rate_50', 'trainer_win_rate_50',
    'distance_win_rate', 'distance_avg_rank',
    'win_odds', 'weight_change', 'jockey_trainer_win_rate',
    'course_win_rate', 'course_avg_rank',
    'days_since_last_run', 'odds_rank_in_race',
    'rtg_change', 'jockey_horse_win_rate',
    'races_last14days', 'going_win_rate',
    'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
    'early_pace', 'finish_speed',
    'last_trial_rank', 'last_trial_time',
    'jockey_win_rate_5', 'jockey_win_rate_10', 'draw_win_rate',
    'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
    'total_injuries', 'injury_severity'
]

# 由於完整特徵工程需要歷史數據，呢度簡化為只使用已有欄位
# 實際應用時，應複製 app_streamlit.py 入面嘅 compute_stats 邏輯
# 但為咗訓練能夠執行，我哋盡量用現有欄位

# 確保所有 FEATURES_EN 都存在
for f in FEATURES_EN:
    if f not in merged.columns:
        merged[f] = 0
    else:
        merged[f] = merged[f].fillna(0)

X = merged[FEATURES_EN].copy()
y = merged['target'].copy()

# 將類別特徵轉為數值（如果有）
for col in X.columns:
    if X[col].dtype == 'object':
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

print(f"  特徵矩陣：{X.shape}")

# ============================================================
# 4️⃣ 分割訓練/測試集
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  訓練集：{len(X_train)} 筆，測試集：{len(X_test)} 筆")

# ============================================================
# 5️⃣ 訓練 XGBoost 模型
# ============================================================
print("🚀 訓練 XGBoost 模型...")
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)
xgb_acc = xgb_model.score(X_test, y_test)
print(f"  XGBoost 測試準確度：{xgb_acc:.2%}")

# ============================================================
# 6️⃣ 訓練 CatBoost 模型
# ============================================================
print("🚀 訓練 CatBoost 模型...")
cat_model = CatBoostClassifier(
    iterations=100,
    learning_rate=0.1,
    depth=5,
    random_seed=42,
    verbose=False
)
cat_model.fit(X_train, y_train)
cat_acc = cat_model.score(X_test, y_test)
print(f"  CatBoost 測試準確度：{cat_acc:.2%}")

# ============================================================
# 7️⃣ 儲存模型
# ============================================================
print("💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)

cat_model.save_model('hk_catboost_model.cbm')

print("✅ 模型已儲存：")
print("  - hk_racing_model.pkl")
print("  - hk_catboost_model.cbm")

# 記錄訓練資訊（可選）
info = {
    "trained_at": datetime.now().isoformat(),
    "xgb_accuracy": xgb_acc,
    "cat_accuracy": cat_acc,
    "train_samples": len(X_train),
    "test_samples": len(X_test)
}
with open("model_info.json", "w", encoding='utf-8') as f:
    import json
    json.dump(info, f, ensure_ascii=False, indent=2)

print("📝 訓練資訊已儲存到 model_info.json")
