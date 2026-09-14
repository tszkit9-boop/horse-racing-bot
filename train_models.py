#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 完整版 (加入智能清洗，修復合併失敗問題)
用法: python train_models.py
"""

import pandas as pd
import numpy as np
import pickle
import warnings
import json
warnings.filterwarnings('ignore')
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from xgboost import XGBRanker
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
# 2️⃣ 智能清洗數據（修復合併失敗的核心）
# ============================================================
print("🧹 智能清洗數據...")

def clean_data(df, is_racecard=False):
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    # 統一日期格式
    if 'race_date' in df.columns:
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # 統一場次格式（移除 "Race " 前綴）
    if 'race_no' in df.columns:
        df['race_no'] = df['race_no'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce').fillna(0).astype(int)
    
    # 統一馬匹編號格式（去空格、去特殊符號）
    for id_col in ['horse_id', '馬號']:
        if id_col in df.columns:
            df[id_col] = df[id_col].astype(str).str.strip().str.replace(r'[^0-9a-zA-Z]', '', regex=True)
    
    # 如果係排位表，將 `比賽日期` 轉做 `race_date`
    if is_racecard and '比賽日期' in df.columns and 'race_date' not in df.columns:
        df['race_date'] = pd.to_datetime(df['比賽日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    return df

results_df = clean_data(results_df, is_racecard=False)
racecard_df = clean_data(racecard_df, is_racecard=True)

# 檢查清洗後嘅數據
print(f"  清洗後賽果記錄：{len(results_df)} 筆")
print(f"  清洗後排位表記錄：{len(racecard_df)} 筆")

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
    df = df.loc[:, ~df.columns.duplicated()]
    return df

racecard_df = standardize_columns(racecard_df)
results_df = standardize_columns(results_df)

# ============================================================
# 4️⃣ 合併數據（終極防衝突版）
# ============================================================
print("🔗 合併數據...")

def standardize_date_for_merge(df):
    if 'race_date' in df.columns:
        df['race_date_str'] = pd.to_datetime(df['race_date'], errors='coerce').dt.strftime('%Y%m%d')
    return df

racecard_df = standardize_date_for_merge(racecard_df)
results_df = standardize_date_for_merge(results_df)

# 🛡️ 智能尋找有效嘅名次欄位
pos_candidates = ['finish_position', 'Pla.', '名次', '最終名次', 'result_position', 'Finish_Rank']
found_pos = False
for col in pos_candidates:
    if col in results_df.columns:
        cleaned = pd.to_numeric(results_df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        if cleaned.notna().any():
            results_df['real_pos'] = cleaned
            found_pos = True
            print(f"  ✅ 成功使用 '{col}' 作名次來源，樣本：{cleaned.dropna().head(5).tolist()}")
            break

if not found_pos:
    print("❌ 嚴重錯誤：賽果數據中找不到任何有效嘅名次欄位！")
    exit(1)

# 🛡️ 關鍵修正 1：清空左表（排位表）中任何可能干擾嘅殘留欄位
for col in ['finish_position', 'real_finish_position', 'real_pos', '__REAL_POS_TEMP__']:
    if col in racecard_df.columns:
        racecard_df = racecard_df.drop(columns=[col])

# 🛡️ 關鍵修正 2：去重之前，先刪除冇名次嘅行，確保真實數據唔會被空值蓋過！
results_df = results_df.dropna(subset=['real_pos']).copy()

# 🛡️ 關鍵修正 3：對右表（賽果）進行去重
results_df_unique = results_df.drop_duplicates(subset=['race_date_str', 'race_no', 'horse_id'], keep='first')

merged = pd.DataFrame()

# 嘗試用完整 Key 合併
if all(c in racecard_df.columns for c in ['race_date_str', 'race_no', 'horse_id']) and \
   all(c in results_df_unique.columns for c in ['race_date_str', 'race_no', 'horse_id', 'real_pos']):
    merged = racecard_df.merge(
        results_df_unique[['race_date_str', 'race_no', 'horse_id', 'real_pos']],
        on=['race_date_str', 'race_no', 'horse_id'],
        how='inner'
    )
    print(f"  第一層合併（完整 Key）：{len(merged)} 筆")

# 如果失敗，降級只用 horse_id 合併
if merged.empty:
    print("  ⚠️ 完整 Key 對唔上，降級嘗試只用 horse_id 合併...")
    if 'horse_id' in racecard_df.columns and 'horse_id' in results_df_unique.columns and 'real_pos' in results_df_unique.columns:
        merged = racecard_df.merge(
            results_df_unique[['horse_id', 'real_pos']],
            on='horse_id',
            how='inner'
        )
        print(f"  第二層合併（僅 horse_id）：{len(merged)} 筆")

if merged.empty:
    print("❌ 嚴重錯誤：無法合併任何數據！")
    exit(1)

# 建立標準嘅 finish_position
merged['finish_position'] = merged['real_pos'].fillna(99)

# 🔍 診斷：睇下 finish_position 係咪真係有數
print(f"  🔍 診斷 - 合併後名次樣本：{merged['finish_position'].head(10).tolist()}")

merged['target'] = (merged['finish_position'] == 1).astype(int)

if merged['target'].nunique() < 2:
    print("❌ 嚴重錯誤：頭馬比例只有一個值，無法訓練！")
    exit(1)

print(f"  最終合併數據：{len(merged)} 筆")
print(f"  頭馬比例：{merged['target'].mean():.2%}")

# ============================================================
# 5️⃣ 特徵工程（36 特徵）
# ============================================================
print("🔧 特徵工程（36 特徵）...")

features_36 = [
    'draw', 'weight', 'distance', 'Rtg.', 'avg_rank_last3',
    'jockey_win_rate_50', 'trainer_win_rate_50',
    'distance_win_rate', 'distance_avg_rank', 'win_odds',
    'weight_change', 'jockey_trainer_win_rate',
    'course_win_rate', 'course_avg_rank',
    'days_since_last_run', 'odds_rank_in_race',
    'rtg_change', 'jockey_horse_win_rate',
    'races_last14days', 'going_win_rate',
    'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
    'early_pace', 'finish_speed', 'last_trial_rank',
    'last_trial_time', 'jockey_win_rate_5', 'jockey_win_rate_10',
    'draw_win_rate', 'days_since_injury', 'injury_30d',
    'injury_60d', 'injury_90d', 'total_injuries', 'injury_severity'
]

for f in features_36:
    if f not in merged.columns:
        merged[f] = 0
    else:
        merged[f] = merged[f].fillna(0)

X = merged[features_36].copy()
y = merged['target'].copy()

for col in X.columns:
    if X[col].dtype == 'object':
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

X = X.astype(np.float32)
y = y.astype(int)

print(f"  特徵矩陣：{X.shape}")

# ============================================================
# 6️⃣ 分割訓練/測試集
# ============================================================
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
except ValueError:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

print(f"  訓練集：{len(X_train)} 筆，測試集：{len(X_test)} 筆")

# ============================================================
# 7️⃣ 訓練 XGBoost
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
# 8️⃣ 訓練 CatBoost
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
# 9️⃣ 訓練 Ranking 模型
# ============================================================
print("🚀 訓練 Ranking 模型...")
rank_model = None
try:
    merged_sorted = merged.sort_values(by=['race_date', 'race_no']).reset_index(drop=True)
    group_sizes = merged_sorted.groupby(['race_date', 'race_no']).size().tolist()
    
    X_rank_df = merged_sorted[features_36].replace('-', 0).apply(pd.to_numeric, errors='coerce').fillna(0)
    X_rank = X_rank_df.values.astype(np.float32)
    y_rank = merged_sorted['target'].values.astype(int)

    if sum(group_sizes) == len(X_rank):
        rank_model = XGBRanker(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            objective='rank:pairwise',
            random_state=42
        )
        rank_model.fit(X_rank, y_rank, group=group_sizes)
        print("  Ranking 模型訓練完成！")
    else:
        print("  ⚠️ 分組大小與數據長度不符，跳過 Ranking 訓練。")
except Exception as e:
    print(f"  ⚠️ Ranking 模型訓練失敗：{e}")

# ============================================================
# 🔟 儲存模型
# ============================================================
print("💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)

cat_model.save_model('hk_catboost_model.cbm')

if rank_model is not None:
    with open('hk_ranking_model.pkl', 'wb') as f:
        pickle.dump(rank_model, f)
    print("  ✅ 已儲存 hk_ranking_model.pkl")

info = {
    "trained_at": datetime.now().isoformat(),
    "xgb_accuracy": xgb_acc,
    "cat_accuracy": cat_acc,
    "rank_trained": rank_model is not None,
    "train_samples": len(X_train),
    "test_samples": len(X_test),
    "features_used": features_36,
    "merge_key": "horse_id"
}
with open("model_info.json", "w", encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print("📝 訓練資訊已儲存到 model_info.json")
print("🎉 自動訓練完成！")
