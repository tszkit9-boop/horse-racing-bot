#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 自動訓練 XGBoost + CatBoost 模型（修正欄位映射）
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
# 2️⃣ 標準化欄位（自動偵測中文/英文）
# ============================================================
print("🔧 標準化欄位...")

def standardize_columns(df):
    """統一欄位名：中文轉英文，確保必要欄位存在"""
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course',
        '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name',   # 確保「馬名」轉為「horse_name」
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
        '比賽日期': 'race_date', '日期': 'race_date'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    
    # 如果仲係冇 horse_name，嘗試搵任何包含「馬名」嘅欄位
    if 'horse_name' not in df.columns:
        for col in df.columns:
            if '名' in col and 'horse' not in col.lower():
                df.rename(columns={col: 'horse_name'}, inplace=True)
                break
    
    # 確保日期欄位
    if 'race_date' not in df.columns:
        for col in df.columns:
            if 'date' in col.lower() or '日期' in col:
                df.rename(columns={col: 'race_date'}, inplace=True)
                break
    
    return df

racecard_df = standardize_columns(racecard_df)
results_df = standardize_columns(results_df)

# 檢查必須欄位
required_racecard = ['race_date', 'race_no', 'horse_name']
required_results = ['race_date', 'race_no', 'horse_name', 'finish_position']

missing_racecard = [c for c in required_racecard if c not in racecard_df.columns]
missing_results = [c for c in required_results if c not in results_df.columns]

if missing_racecard:
    print(f"❌ 排位表缺少欄位：{missing_racecard}")
    print(f"   現有欄位：{racecard_df.columns.tolist()}")
    exit(1)

if missing_results:
    print(f"❌ 賽果表缺少欄位：{missing_results}")
    print(f"   現有欄位：{results_df.columns.tolist()}")
    exit(1)

# 日期格式
racecard_df['race_date'] = pd.to_datetime(racecard_df['race_date'], errors='coerce')
results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')

# 刪除無效日期
racecard_df = racecard_df.dropna(subset=['race_date'])
results_df = results_df.dropna(subset=['race_date'])

print(f"  排位表有效日期：{len(racecard_df)} 筆")
print(f"  賽果有效日期：{len(results_df)} 筆")

# ============================================================
# 3️⃣ 合併數據
# ============================================================
print("🔗 合併數據...")

# 確保合併 key 嘅類型一致
racecard_df['race_no'] = racecard_df['race_no'].astype(str)
results_df['race_no'] = results_df['race_no'].astype(str)

merged = racecard_df.merge(
    results_df[['race_date', 'race_no', 'horse_name', 'finish_position']],
    on=['race_date', 'race_no', 'horse_name'],
    how='inner'
)
print(f"  合併後：{len(merged)} 筆記錄")

if merged.empty:
    print("❌ 無數據可訓練，請確認 CSV 檔案齊全及日期匹配")
    exit(1)

# 標籤：頭馬（finish_position == 1）
merged['target'] = (merged['finish_position'] == 1).astype(int)

# ============================================================
# 4️⃣ 特徵工程
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

# 確保所有特徵欄位存在
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
# 5️⃣ 分割訓練/測試集
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  訓練集：{len(X_train)} 筆，測試集：{len(X_test)} 筆")

# ============================================================
# 6️⃣ 訓練 XGBoost
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
# 7️⃣ 訓練 CatBoost
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
# 8️⃣ 儲存模型
# ============================================================
print("💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)

cat_model.save_model('hk_catboost_model.cbm')

print("✅ 模型已儲存：")
print("  - hk_racing_model.pkl")
print("  - hk_catboost_model.cbm")

# 記錄訓練資訊
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
print("🎉 自動訓練完成！")
