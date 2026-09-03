#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 自動訓練模型（修正重複欄位問題）
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
# 2️⃣ 刪除重複欄位（保留第一個）
# ============================================================
print("🧹 刪除重複欄位...")
racecard_df = racecard_df.loc[:, ~racecard_df.columns.duplicated(keep='first')]
results_df = results_df.loc[:, ~results_df.columns.duplicated(keep='first')]

print(f"  排位表去重後欄位：{racecard_df.columns.tolist()}")
print(f"  賽果去重後欄位：{results_df.columns.tolist()}")

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
        '實際負磅': 'act_wt', '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name', '馬匹名稱': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
        '比賽日期': 'race_date', '日期': 'race_date',
        'RaceDate': 'race_date', 'RaceNo': 'race_no', 'Pla': 'finish_position',
        'Name': 'horse_name', 'Dr.': 'draw', 'Trainer': 'trainer',
        'Jockey': 'jockey', 'Declar.Horse wt.': 'act_wt',
        'Win Odds': 'win_odds', 'Act.Wt.': 'act_wt', 'Dist.': 'distance'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    return df

racecard_df = standardize_columns(racecard_df)
results_df = standardize_columns(results_df)

print(f"  排位表標準化後欄位：{racecard_df.columns.tolist()}")
print(f"  賽果標準化後欄位：{results_df.columns.tolist()}")

# ============================================================
# 4️⃣ 確認必要欄位
# ============================================================
# 排位表必須有：race_date, race_no, horse_id 或 horse_name
if 'horse_name' in racecard_df.columns:
    race_key = 'horse_name'
elif 'horse_id' in racecard_df.columns:
    race_key = 'horse_id'
else:
    print("❌ 排位表缺少 horse_name 或 horse_id")
    exit(1)

if 'horse_name' in results_df.columns:
    result_key = 'horse_name'
elif 'horse_id' in results_df.columns:
    result_key = 'horse_id'
else:
    print("❌ 賽果表缺少 horse_name 或 horse_id")
    exit(1)

print(f"  排位表使用 key：{race_key}")
print(f"  賽果表使用 key：{result_key}")

# 統一 key 名
if race_key != result_key:
    # 嘗試將兩者統一為 horse_id（如果兩者都有 horse_id）
    if 'horse_id' in racecard_df.columns and 'horse_id' in results_df.columns:
        race_key = 'horse_id'
        result_key = 'horse_id'
    elif 'horse_name' in racecard_df.columns and 'horse_name' in results_df.columns:
        race_key = 'horse_name'
        result_key = 'horse_name'
    else:
        # 強行將兩者改為相同名稱（選擇存在嘅一個）
        if race_key == 'horse_id' and result_key == 'horse_name':
            # 如果賽果表有 horse_name，嘗試將 racecard 嘅 horse_id 映射到 horse_name
            # 但冇 mapping，直接將 racecard 嘅 horse_id rename 為 horse_name（但可能唔啱）
            # 最穩陣：要求兩者都有 horse_id 或 horse_name
            print("❌ 排位表同賽果表嘅 key 唔一致，無法合併")
            exit(1)
        elif race_key == 'horse_name' and result_key == 'horse_id':
            # 同上
            print("❌ 排位表同賽果表嘅 key 唔一致，無法合併")
            exit(1)

# 確保兩邊用同一個 key
if race_key != result_key:
    print("❌ 無法統一合併 key，請確認檔案欄位")
    exit(1)

print(f"  使用合併 key：{race_key}")

# 檢查日期欄位
if 'race_date' not in racecard_df.columns or 'race_date' not in results_df.columns:
    print("❌ 缺少日期欄位")
    exit(1)

# 檢查場次欄位
if 'race_no' not in racecard_df.columns or 'race_no' not in results_df.columns:
    print("❌ 缺少場次欄位")
    exit(1)

# 賽果必須有 finish_position
if 'finish_position' not in results_df.columns:
    print("❌ 賽果缺少 finish_position 欄位")
    exit(1)

# ============================================================
# 5️⃣ 日期處理
# ============================================================
racecard_df['race_date'] = pd.to_datetime(racecard_df['race_date'], errors='coerce')
results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')

racecard_df = racecard_df.dropna(subset=['race_date'])
results_df = results_df.dropna(subset=['race_date'])

print(f"  排位表有效日期：{len(racecard_df)} 筆")
print(f"  賽果有效日期：{len(results_df)} 筆")

# ============================================================
# 6️⃣ 合併數據（用指定 key）
# ============================================================
print("🔗 合併數據...")

# 確保合併 key 嘅類型一致
racecard_df['race_no'] = racecard_df['race_no'].astype(str)
results_df['race_no'] = results_df['race_no'].astype(str)
racecard_df[race_key] = racecard_df[race_key].astype(str)
results_df[race_key] = results_df[race_key].astype(str)

merge_keys = ['race_date', 'race_no', race_key]
results_keep = ['race_date', 'race_no', race_key, 'finish_position']

# 合併前檢查重複
print(f"  排位表合併前重複 count：{racecard_df.duplicated(subset=merge_keys).sum()}")
print(f"  賽果合併前重複 count：{results_df.duplicated(subset=results_keep).sum()}")

# 移除重複（保留最後一個）
racecard_df = racecard_df.drop_duplicates(subset=merge_keys, keep='last')
results_df = results_df.drop_duplicates(subset=results_keep, keep='last')

print(f"  排位表去重後：{len(racecard_df)} 筆")
print(f"  賽果去重後：{len(results_df)} 筆")

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
# 7️⃣ 特徵工程（選取現有欄位）
# ============================================================
print("🔧 特徵工程...")

# 定義想要用嘅特徵（根據現有欄位盡量填）
FEATURES = ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']
# 補上其他可能存在嘅特徵
extra = ['jockey', 'trainer', 'going', 'race_course']
for f in extra:
    if f in merged.columns and f not in FEATURES:
        FEATURES.append(f)

# 確保所有特徵欄位存在
for f in FEATURES:
    if f not in merged.columns:
        merged[f] = 0
    else:
        merged[f] = merged[f].fillna(0)

X = merged[FEATURES].copy()
y = merged['target'].copy()

# 將類別特徵轉為數值
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
