#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 自動訓練 XGBoost + CatBoost 模型（靈活欄位對應）
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

results_df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig')
print(f"  賽果數據：{len(results_df)} 筆")
print(f"  賽果欄位：{results_df.columns.tolist()}")

racecard_df = pd.read_csv("HKCJ_FULL_YEAR_DATA.csv", encoding='utf-8-sig')
print(f"  排位表：{len(racecard_df)} 筆")
print(f"  排位表欄位：{racecard_df.columns.tolist()}")

# ============================================================
# 2️⃣ 標準化欄位（靈活對應）
# ============================================================
print("🔧 標準化欄位...")

def standardize_columns(df, name="df"):
    """統一欄位名：將常見中文欄位名轉為英文，並自動偵測"""
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course',
        '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name', '馬匹名稱': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
        '比賽日期': 'race_date', '日期': 'race_date'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    
    # 如果仲係冇 horse_name，嘗試搵任何包含「名」或「馬」嘅欄位
    if 'horse_name' not in df.columns:
        for col in df.columns:
            if '名' in col or '馬' in col:
                if 'horse' not in col.lower():
                    df.rename(columns={col: 'horse_name'}, inplace=True)
                    print(f"  將欄位 '{col}' 映射為 'horse_name'")
                    break
    
    # 如果仲係冇 race_date，嘗試搵任何包含「日期」或「date」嘅欄位
    if 'race_date' not in df.columns:
        for col in df.columns:
            if 'date' in col.lower() or '日期' in col:
                df.rename(columns={col: 'race_date'}, inplace=True)
                print(f"  將欄位 '{col}' 映射為 'race_date'")
                break
    
    return df

racecard_df = standardize_columns(racecard_df, "排位表")
results_df = standardize_columns(results_df, "賽果")

print(f"  排位表標準化後欄位：{racecard_df.columns.tolist()}")
print(f"  賽果標準化後欄位：{results_df.columns.tolist()}")

# ============================================================
# 3️⃣ 確認必要欄位
# ============================================================
required_racecard = ['race_date', 'race_no']
required_results = ['race_date', 'race_no', 'finish_position']

# 檢查排位表有冇馬名或馬ID
if 'horse_name' in racecard_df.columns:
    racecard_key = 'horse_name'
elif 'horse_id' in racecard_df.columns:
    racecard_key = 'horse_id'
else:
    print("❌ 排位表缺少 'horse_name' 或 'horse_id' 欄位")
    exit(1)

if 'horse_name' in results_df.columns:
    results_key = 'horse_name'
elif 'horse_id' in results_df.columns:
    results_key = 'horse_id'
else:
    print("❌ 賽果表缺少 'horse_name' 或 'horse_id' 欄位")
    exit(1)

print(f"  排位表使用 key：{racecard_key}")
print(f"  賽果表使用 key：{results_key}")

# 如果兩邊嘅 key 唔同名，改為同名
if racecard_key != results_key:
    if racecard_key == 'horse_id' and results_key == 'horse_name':
        # 用 horse_id 對應 horse_name：需要 mapping
        # 先假設兩個檔案嘅馬匹命名一致，用 horse_name 作為 key
        # 但排位表冇 horse_name，所以要用 horse_id 黎合併
        # 最簡單：強制兩邊都用 horse_id（如果賽果表有 horse_id）
        if 'horse_id' in results_df.columns:
            results_key = 'horse_id'
            print("  改用 horse_id 做合併 key")
        else:
            # 賽果表冇 horse_id，只能靠 horse_name，但排位表冇 horse_name，咁就麻煩
            print("❌ 排位表有 horse_id，賽果表有 horse_name，但兩者無法直接合併")
            print("   請確保兩個檔案都有 horse_name 或 horse_id")
            exit(1)
    elif racecard_key == 'horse_name' and results_key == 'horse_id':
        # 反過來，如果排位表有 horse_name，賽果表有 horse_id
        if 'horse_name' in results_df.columns:
            results_key = 'horse_name'
            print("  改用 horse_name 做合併 key")
        else:
            print("❌ 排位表有 horse_name，賽果表有 horse_id，但無法直接合併")
            exit(1)
    else:
        # 如果兩邊嘅 key 都係 horse_id 或 horse_name，但名唔同，rename
        pass

# 確保兩邊嘅 key 名一致
if racecard_key != results_key:
    # 將 results_df 嘅 key 改為同 racecard_key 一樣
    results_df.rename(columns={results_key: racecard_key}, inplace=True)
    results_key = racecard_key
    print(f"  已統一合併 key 為：{racecard_key}")

# ============================================================
# 4️⃣ 日期處理
# ============================================================
racecard_df['race_date'] = pd.to_datetime(racecard_df['race_date'], errors='coerce')
results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')

racecard_df = racecard_df.dropna(subset=['race_date'])
results_df = results_df.dropna(subset=['race_date'])

print(f"  排位表有效日期：{len(racecard_df)} 筆")
print(f"  賽果有效日期：{len(results_df)} 筆")

# ============================================================
# 5️⃣ 合併數據
# ============================================================
print("🔗 合併數據...")

# 確保合併 key 嘅類型一致
racecard_df['race_no'] = racecard_df['race_no'].astype(str)
results_df['race_no'] = results_df['race_no'].astype(str)

# 選取合併所需欄位
merge_keys = ['race_date', 'race_no', racecard_key]
results_keep = ['race_date', 'race_no', racecard_key, 'finish_position']

merged = racecard_df.merge(
    results_df[results_keep],
    on=merge_keys,
    how='inner'
)
print(f"  合併後：{len(merged)} 筆記錄")

if merged.empty:
    print("❌ 無數據可訓練，請確認 CSV 檔案齊全及日期匹配")
    exit(1)

# 標籤：頭馬（finish_position == 1）
merged['target'] = (merged['finish_position'] == 1).astype(int)

# ============================================================
# 6️⃣ 特徵工程（簡化版）
# ============================================================
print("🔧 特徵工程...")

# 定義可能用到嘅特徵（根據現有欄位盡量填）
FEATURES_EN = [
    'draw', 'act_wt', 'distance', 'rtg', 'win_odds'
]

# 補上其他可能存在嘅特徵
extra_features = ['weight', 'jockey', 'trainer', 'going', 'race_course']
for f in extra_features:
    if f in merged.columns and f not in FEATURES_EN:
        FEATURES_EN.append(f)

# 確保所有特徵欄位存在
for f in FEATURES_EN:
    if f not in merged.columns:
        merged[f] = 0
    else:
        merged[f] = merged[f].fillna(0)

X = merged[FEATURES_EN].copy()
y = merged['target'].copy()

# 將類別特徵轉為數值
for col in X.columns:
    if X[col].dtype == 'object':
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

print(f"  特徵矩陣：{X.shape}")

# ============================================================
# 7️⃣ 分割訓練/測試集
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  訓練集：{len(X_train)} 筆，測試集：{len(X_test)} 筆")

# ============================================================
# 8️⃣ 訓練 XGBoost
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
# 9️⃣ 訓練 CatBoost
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
# 🔟 儲存模型
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
