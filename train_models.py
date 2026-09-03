#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 自動訓練 XGBoost + CatBoost 模型（終極防崩潰版）
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

racecard_df = pd.read_csv("HKCJ_FULL_YEAR_DATA.csv", encoding='utf-8-sig')
print(f"  排位表：{len(racecard_df)} 筆")

# ============================================================
# 2️⃣ 處理重複欄位
# ============================================================
print("🔧 處理重複欄位...")

def dedup_columns(df, name="df"):
    if df.columns.duplicated().any():
        dup_cols = df.columns[df.columns.duplicated()].tolist()
        print(f"  {name} 發現重複欄位：{dup_cols[:5]}...")
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
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
    
    # 改名後再強制去重
    df = df.loc[:, ~df.columns.duplicated()]
    
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
        exit(1)

print(f"  合併 key：{merge_key}")

# ============================================================
# 5️⃣ 日期處理（終極防崩潰版）
# ============================================================
print("📅 處理日期...")

def safe_parse_dates(df, col='race_date'):
    if col not in df.columns:
        return df, 0
    
    # 先清理重複欄位
    df = df.loc[:, ~df.columns.duplicated()]
    
    # 強制轉成字串再解析，兼容多種格式（包括純數字）
    try:
        # pandas 2.0 以上支援 format='mixed'
        df[col] = pd.to_datetime(df[col].astype(str), errors='coerce', format='mixed')
    except TypeError:
        # 舊版本 pandas 不支援，用默認方式
        df[col] = pd.to_datetime(df[col].astype(str), errors='coerce')
    
    invalid = df[col].isna().sum()
    if invalid > 0:
        print(f"  ⚠️ 發現 {invalid} 個無效日期")
        # 🛡️ 終極保底：如果全部日期都無效，就保留原數據，避免數據集變空！
        if len(df) > invalid:
            df = df.dropna(subset=[col])
        else:
            print(f"  🛡️ 警告：{col} 欄位全部無效，保留原數據以免數據集為空")
            
    return df, invalid

racecard_df, invalid1 = safe_parse_dates(racecard_df)
results_df, invalid2 = safe_parse_dates(results_df)

print(f"  排位表有效日期：{len(racecard_df)} 筆")
print(f"  賽果有效日期：{len(results_df)} 筆")

if racecard_df.empty or results_df.empty:
    print("❌ 其中一個數據集為空，無法繼續")
    exit(1)

# ============================================================
# 6️⃣ 合併數據
# ============================================================
print("🔗 合併數據...")

racecard_df['race_no'] = racecard_df['race_no'].astype(str)
results_df['race_no'] = results_df['race_no'].astype(str)

for k in [merge_key, 'race_date', 'race_no']:
    if k not in racecard_df.columns or k not in results_df.columns:
        print(f"❌ 缺少合併欄位 '{k}'")
        exit(1)

merged = racecard_df.merge(
    results_df[['race_date', 'race_no', merge_key, 'finish_position']],
    on=['race_date', 'race_no', merge_key],
    how='inner'
)
print(f"  合併後：{len(merged)} 筆記錄")

if merged.empty:
    print("❌ 合併後無數據，請檢查兩個檔案的日期範圍及馬匹ID是否有重疊")
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

for f in FEATURES_EN:
    if f not in merged.columns:
        merged[f] = 0
    else:
        merged[f] = merged[f].fillna(0)

X = merged[FEATURES_EN].copy()
y = merged['target'].copy()

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
