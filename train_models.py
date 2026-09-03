#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 自動訓練 XGBoost + CatBoost 模型（強健版）
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
print(f"  賽果欄位數量：{len(results_df.columns)}")

racecard_df = pd.read_csv("HKCJ_FULL_YEAR_DATA.csv", encoding='utf-8-sig')
print(f"  排位表：{len(racecard_df)} 筆")
print(f"  排位表欄位數量：{len(racecard_df.columns)}")

# ============================================================
# 2️⃣ 處理重複欄位
# ============================================================
print("🔧 處理重複欄位...")

def dedup_columns(df, name="df"):
    if df.columns.duplicated().any():
        dup_cols = df.columns[df.columns.duplicated()].tolist()
        print(f"  {name} 發現重複欄位：{dup_cols[:5]}...")
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        print(f"  {name} 已移除重複欄位，現有 {len(df.columns)} 個欄位")
    return df

racecard_df = dedup_columns(racecard_df, "排位表")
results_df = dedup_columns(results_df, "賽果")

# ============================================================
# 3️⃣ 標準化欄位
# ============================================================
print("🔧 標準化欄位...")

def standardize_columns(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course',
        '實際負磅': 'act_wt', '負磅': 'act_wt', 'Act.Wt.': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position', 'Pla.': 'finish_position',
        '馬名': 'horse_name', '馬匹名稱': 'horse_name', 'Name': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds', 'Win Odds': 'win_odds',
        '比賽日期': 'race_date', '日期': 'race_date', 'Date': 'race_date'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    
    if 'horse_name' not in df.columns:
        for col in df.columns:
            if '名' in col or '馬' in col or 'Name' in col:
                if 'horse' not in col.lower():
                    df.rename(columns={col: 'horse_name'}, inplace=True)
                    break
    
    if 'race_date' not in df.columns:
        for col in df.columns:
            if 'date' in col.lower() or '日期' in col:
                df.rename(columns={col: 'race_date'}, inplace=True)
                break
    
    return df

racecard_df = standardize_columns(racecard_df)
results_df = standardize_columns(results_df)

print(f"  排位表標準化後欄位（前10個）：{racecard_df.columns[:10].tolist()}")
print(f"  賽果標準化後欄位（前10個）：{results_df.columns[:10].tolist()}")

# ============================================================
# 4️⃣ 檢查必要欄位
# ============================================================
print("🔍 檢查必要欄位...")

def check_column_exists(df, col, name):
    if col not in df.columns:
        print(f"❌ {name} 缺少 '{col}' 欄位")
        return False
    return True

ok = True
for col in ['race_date', 'race_no']:
    if not check_column_exists(racecard_df, col, "排位表"):
        ok = False
for col in ['race_date', 'race_no', 'finish_position']:
    if not check_column_exists(results_df, col, "賽果"):
        ok = False

if not ok:
    print("  請檢查 CSV 檔案欄位名是否正確")
    exit(1)

# 決定合併 key
merge_key = None
if 'horse_name' in racecard_df.columns and 'horse_name' in results_df.columns:
    merge_key = 'horse_name'
elif 'horse_id' in racecard_df.columns and 'horse_id' in results_df.columns:
    merge_key = 'horse_id'
else:
    common_cols = set(racecard_df.columns) & set(results_df.columns)
    for k in ['horse_id', 'horse_name', '馬名', '馬匹編號']:
        if k in common_cols:
            merge_key = k
            break
    if merge_key is None:
        print("❌ 無法找到合併 key")
        print(f"   排位表欄位：{racecard_df.columns.tolist()}")
        print(f"   賽果欄位：{results_df.columns.tolist()}")
        exit(1)

print(f"  合併 key：{merge_key}")

# ============================================================
# 5️⃣ 日期處理（強健版）
# ============================================================
print("📅 處理日期...")

def safe_parse_dates(df, col='race_date'):
    if col not in df.columns:
        return df, 0
    original = df[col].copy()
    df[col] = pd.to_datetime(df[col], errors='coerce')
    invalid = df[col].isna().sum()
    if invalid > 0:
        print(f"  ⚠️ 發現 {invalid} 個無效日期，將被刪除")
        df = df.dropna(subset=[col])
    return df, invalid

racecard_df, invalid1 = safe_parse_dates(racecard_df)
results_df, invalid2 = safe_parse_dates(results_df)

print(f"  排位表有效日期：{len(racecard_df)} 筆（刪除 {invalid1} 筆無效）")
print(f"  賽果有效日期：{len(results_df)} 筆（刪除 {invalid2} 筆無效）")

if racecard_df.empty or results_df.empty:
    print("❌ 其中一個數據集為空，無法繼續")
    exit(1)

# ============================================================
# 6️⃣ 合併數據（詳細除錯）
# ============================================================
print("🔗 合併數據...")

# 確保類型一致
racecard_df['race_no'] = racecard_df['race_no'].astype(str)
results_df['race_no'] = results_df['race_no'].astype(str)

# 確保 key 存在
for k in [merge_key, 'race_date', 'race_no']:
    if k not in racecard_df.columns:
        print(f"❌ 排位表缺少 '{k}'")
        exit(1)
    if k not in results_df.columns:
        print(f"❌ 賽果缺少 '{k}'")
        exit(1)

print(f"  排位表數據形狀：{racecard_df.shape}")
print(f"  賽果數據形狀：{results_df.shape}")

# 顯示合併 key 的樣本
print(f"  排位表 {merge_key} 樣本：{racecard_df[merge_key].head(3).tolist()}")
print(f"  賽果 {merge_key} 樣本：{results_df[merge_key].head(3).tolist()}")

# 合併
merged = racecard_df.merge(
    results_df[['race_date', 'race_no', merge_key, 'finish_position']],
    on=['race_date', 'race_no', merge_key],
    how='inner'
)
print(f"  合併後：{len(merged)} 筆記錄")

if merged.empty:
    print("❌ 合併後無數據")
    print("  可能原因：")
    print("  1. 兩個檔案嘅日期範圍冇重疊")
    print("  2. 馬匹名稱/ID 對唔上")
    print("  3. 場次編號格式唔同")
    print(f"  排位表日期範圍：{racecard_df['race_date'].min()} ~ {racecard_df['race_date'].max()}")
    print(f"  賽果日期範圍：{results_df['race_date'].min()} ~ {results_df['race_date'].max()}")
    exit(1)

# 標籤
merged['target'] = (merged['finish_position'] == 1).astype(int)
print(f"  頭馬比例：{merged['target'].mean():.2%}")

# ============================================================
# 7️⃣ 特徵工程
# ============================================================
print("🔧 特徵工程...")

FEATURES_EN = ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']
extra = ['weight', 'jockey', 'trainer', 'going', 'race_course']
for f in extra:
    if f in merged.columns and f not in FEATURES_EN:
        FEATURES_EN.append(f)

# 確保所有特徵存在
for f in FEATURES_EN:
    if f not in merged.columns:
        merged[f] = 0
    else:
        merged[f] = merged[f].fillna(0)

X = merged[FEATURES_EN].copy()
y = merged['target'].copy()

# 類別特徵轉數值
for col in X.columns:
    if X[col].dtype == 'object':
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

print(f"  特徵矩陣：{X.shape}")

# ============================================================
# 8️⃣ 分割訓練/測試集
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  訓練集：{len(X_train)} 筆，測試集：{len(X_test)} 筆")

# ============================================================
# 9️⃣ 訓練 XGBoost
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
# 🔟 訓練 CatBoost
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
# 1️⃣1️⃣ 儲存模型
# ============================================================
print("💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)

cat_model.save_model('hk_catboost_model.cbm')

print("✅ 模型已儲存：")
print("  - hk_racing_model.pkl")
print("  - hk_catboost_model.cbm")

info = {
    "trained_at": datetime.now().isoformat(),
    "xgb_accuracy": xgb_acc,
    "cat_accuracy": cat_acc,
    "train_samples": len(X_train),
    "test_samples": len(X_test),
    "features_used": FEATURES_EN,
    "merge_key": merge_key
}
with open("model_info.json", "w", encoding='utf-8') as f:
    import json
    json.dump(info, f, ensure_ascii=False, indent=2)

print("📝 訓練資訊已儲存到 model_info.json")
print("🎉 自動訓練完成！")
