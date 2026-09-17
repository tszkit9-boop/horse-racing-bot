#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 完整修復版
- 加 DEBUG 診斷
- 按 horse_id 分組拆分
- 正確評估（AUC + Top-1 + Top-3）
用法: python train_models.py
"""

import pandas as pd
import numpy as np
import pickle
import warnings
import json
warnings.filterwarnings('ignore')
from datetime import datetime
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, log_loss
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
# 2️⃣ 智能清洗數據
# ============================================================
print("🧹 智能清洗數據...")

def clean_data(df, is_racecard=False):
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    if 'race_date' in df.columns:
        df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    if 'race_no' in df.columns:
        df['race_no'] = df['race_no'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce').fillna(0).astype(int)
    for id_col in ['horse_id', '馬號']:
        if id_col in df.columns:
            df[id_col] = df[id_col].astype(str).str.strip().str.replace(r'[^0-9a-zA-Z]', '', regex=True)
    if is_racecard and '比賽日期' in df.columns and 'race_date' not in df.columns:
        df['race_date'] = pd.to_datetime(df['比賽日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    return df

results_df = clean_data(results_df, is_racecard=False)
racecard_df = clean_data(racecard_df, is_racecard=True)

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
# 4️⃣ 合併數據（含 DEBUG）
# ============================================================
print("🔗 合併數據...")

def standardize_date_for_merge(df):
    if 'race_date' in df.columns:
        df['race_date_str'] = pd.to_datetime(df['race_date'], errors='coerce').dt.strftime('%Y%m%d')
    return df

racecard_df = standardize_date_for_merge(racecard_df)
results_df = standardize_date_for_merge(results_df)

pos_candidates = ['finish_position', 'Pla.', '名次', '最終名次', 'result_position', 'Finish_Rank']
found_pos = False
for col in pos_candidates:
    if col in results_df.columns:
        cleaned = pd.to_numeric(results_df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        if cleaned.notna().any():
            results_df['real_pos'] = cleaned
            found_pos = True
            print(f"  ✅ 成功使用 '{col}' 作名次來源")
            break

if not found_pos:
    print("❌ 嚴重錯誤：找不到有效名次欄位")
    exit(1)

for col in ['finish_position', 'real_finish_position', 'real_pos', '__REAL_POS_TEMP__']:
    if col in racecard_df.columns:
        racecard_df = racecard_df.drop(columns=[col])

results_df = results_df.dropna(subset=['real_pos']).copy()
results_df_unique = results_df.drop_duplicates(subset=['race_date_str', 'race_no', 'horse_id'], keep='first')

# ============================================================
# 🔍 DEBUG 數據診斷
# ============================================================
print("\n" + "=" * 60)
print("🔍 DEBUG 數據診斷")
print("=" * 60)

print(f"\n📋 racecard_df 欄位 ({len(racecard_df.columns)} 個)：")
print(f"  {list(racecard_df.columns)}")

print(f"\n📋 results_df_unique 欄位 ({len(results_df_unique.columns)} 個)：")
print(f"  {list(results_df_unique.columns)}")

print(f"\n📊 racecard_df 樣本（前 3 行）：")
for col in ['race_date_str', 'race_no', 'horse_id', '馬號']:
    if col in racecard_df.columns:
        vals = racecard_df[col].head(3).tolist()
        print(f"  {col} = {vals}")
    else:
        print(f"  {col} = ❌ 欄位唔存在")

print(f"\n📊 results_df_unique 樣本（前 3 行）：")
for col in ['race_date_str', 'race_no', 'horse_id', 'real_pos']:
    if col in results_df_unique.columns:
        vals = results_df_unique[col].head(3).tolist()
        print(f"  {col} = {vals}")
    else:
        print(f"  {col} = ❌ 欄位唔存在")

print(f"\n🔍 唯一值比較：")
if 'race_date_str' in racecard_df.columns and 'race_date_str' in results_df_unique.columns:
    rc_dates = set(racecard_df['race_date_str'].dropna().unique())
    rs_dates = set(results_df_unique['race_date_str'].dropna().unique())
    overlap = rc_dates & rs_dates
    print(f"  race_date_str：racecard {len(rc_dates)} 個，results {len(rs_dates)} 個，重疊 {len(overlap)} 個")
    print(f"    racecard 樣本：{list(rc_dates)[:3]}")
    print(f"    results 樣本：{list(rs_dates)[:3]}")

if 'horse_id' in racecard_df.columns and 'horse_id' in results_df_unique.columns:
    rc_hid = set(racecard_df['horse_id'].dropna().unique())
    rs_hid = set(results_df_unique['horse_id'].dropna().unique())
    overlap = rc_hid & rs_hid
    print(f"  horse_id：racecard {len(rc_hid)} 個，results {len(rs_hid)} 個，重疊 {len(overlap)} 個")
    print(f"    racecard 樣本：{list(rc_hid)[:5]}")
    print(f"    results 樣本：{list(rs_hid)[:5]}")

if 'race_no' in racecard_df.columns and 'race_no' in results_df_unique.columns:
    rc_rn = set(racecard_df['race_no'].dropna().unique())
    rs_rn = set(results_df_unique['race_no'].dropna().unique())
    overlap = rc_rn & rs_rn
    print(f"  race_no：racecard {len(rc_rn)} 個，results {len(rs_rn)} 個，重疊 {len(overlap)} 個")

print("=" * 60 + "\n")

# ============================================================
# 合併
# ============================================================
merged = pd.DataFrame()

if all(c in racecard_df.columns for c in ['race_date_str', 'race_no', 'horse_id']) and \
   all(c in results_df_unique.columns for c in ['race_date_str', 'race_no', 'horse_id', 'real_pos']):
    merged = racecard_df.merge(
        results_df_unique[['race_date_str', 'race_no', 'horse_id', 'real_pos']],
        on=['race_date_str', 'race_no', 'horse_id'],
        how='inner'
    )
    print(f"  第一層合併（完整 Key）：{len(merged)} 筆")

if merged.empty:
    print("  ⚠️ 降級只用 horse_id 合併...")
    if 'horse_id' in racecard_df.columns and 'horse_id' in results_df_unique.columns:
        merged = racecard_df.merge(
            results_df_unique[['horse_id', 'real_pos']],
            on='horse_id',
            how='inner'
        )
        print(f"  第二層合併（僅 horse_id）：{len(merged)} 筆")

if merged.empty:
    print("❌ 無法合併數據")
    exit(1)

merged['finish_position'] = merged['real_pos'].fillna(99)
merged['target'] = (merged['finish_position'] == 1).astype(int)

if merged['target'].nunique() < 2:
    print("❌ 頭馬比例只有一個值")
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

# ============================================================
# 6️⃣ 按 horse_id 分組拆分
# ============================================================
print("📂 按 horse_id 分組拆分...")

merged_valid = merged[merged['horse_id'].notna()].copy()
merged_valid = merged_valid[merged_valid['horse_id'].astype(str).str.strip() != ''].copy()

print(f"  有效數據：{len(merged_valid)} 筆")

if len(merged_valid) < 100:
    print("❌ 數據太少，無法訓練")
    exit(1)

X_valid = merged_valid[features_36].copy()
for col in X_valid.columns:
    if X_valid[col].dtype == 'object':
        le = LabelEncoder()
        X_valid[col] = le.fit_transform(X_valid[col].astype(str))
    X_valid[col] = pd.to_numeric(X_valid[col], errors='coerce').fillna(0)
X_valid = X_valid.astype(np.float32)
y_valid = merged_valid['target'].astype(int)
groups = merged_valid['horse_id'].astype(str).values

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X_valid, y_valid, groups=groups))

X_train = X_valid.iloc[train_idx]
X_test = X_valid.iloc[test_idx]
y_train = y_valid.iloc[train_idx]
y_test = y_valid.iloc[test_idx]

test_df = merged_valid.iloc[test_idx].copy()
try:
    race_key = test_df['race_date_str'].astype(str) + "_" + test_df['race_no'].astype(str)
    if race_key.nunique() >= 2 and (race_key != 'nan_nan').sum() > 10:
        test_groups = race_key.values
        print(f"  ✅ 評估用 race_date + race_no 分組（{race_key.nunique()} 場）")
    else:
        test_groups = test_df['horse_id'].astype(str).values
        print(f"  ⚠️ race_date/race_no 無效，評估用 horse_id 分組")
except Exception:
    test_groups = test_df['horse_id'].astype(str).values
    print(f"  ⚠️ 評估 fallback 到 horse_id 分組")

print(f"  訓練集：{len(X_train)} 筆，測試集：{len(X_test)} 筆")
print(f"  測試集組數：{len(set(test_groups))}")

# ============================================================
# 7️⃣ 評估函數（Top-1 / Top-3 命中率）
# ============================================================
def evaluate_topk(model, X_test, y_test, test_groups, model_name="Model"):
    try:
        proba = model.predict_proba(X_test)[:, 1]
    except Exception:
        proba = model.predict(X_test)

    df_eval = pd.DataFrame({
        'group': test_groups,
        'y_true': y_test.values,
        'proba': proba
    })

    top1_hit = 0
    top3_hit = 0
    total_races = 0

    for g, sub in df_eval.groupby('group'):
        if sub['y_true'].sum() == 0:
            continue
        total_races += 1
        ranked = sub.sort_values('proba', ascending=False).reset_index(drop=True)
        winner_idx = ranked[ranked['y_true'] == 1].index
        if len(winner_idx) == 0:
            continue
        winner_pos = winner_idx[0] + 1
        if winner_pos == 1:
            top1_hit += 1
        if winner_pos <= 3:
            top3_hit += 1

    if total_races == 0:
        return 0.0, 0.0, 0.0, 0.0, 0

    top1_acc = top1_hit / total_races
    top3_acc = top3_hit / total_races

    try:
        auc = roc_auc_score(y_test, proba)
    except Exception:
        auc = 0.0

    try:
        ll = log_loss(y_test, proba)
    except Exception:
        ll = 0.0

    print(f"  📊 {model_name} 評估結果：")
    print(f"     ├─ AUC：{auc:.4f}（0.5 = 隨機，1.0 = 完美）")
    print(f"     ├─ Log Loss：{ll:.4f}（越低越好）")
    print(f"     ├─ Top-1 命中率：{top1_acc:.2%}（{top1_hit}/{total_races} 場）")
    print(f"     └─ Top-3 命中率：{top3_acc:.2%}（{top3_hit}/{total_races} 場）")

    return auc, ll, top1_acc, top3_acc, total_races

# ============================================================
# 8️⃣ 訓練 XGBoost
# ============================================================
print("\n🚀 訓練 XGBoost 模型...")

neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos = neg_count / pos_count if pos_count > 0 else 1
print(f"  scale_pos_weight = {scale_pos:.2f}")

xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    scale_pos_weight=scale_pos,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)

xgb_auc, xgb_ll, xgb_top1, xgb_top3, xgb_races = evaluate_topk(
    xgb_model, X_test, y_test, test_groups, "XGBoost"
)

# ============================================================
# 9️⃣ 訓練 CatBoost
# ============================================================
print("\n🚀 訓練 CatBoost 模型...")
cat_model = CatBoostClassifier(
    iterations=200,
    learning_rate=0.05,
    depth=5,
    auto_class_weights='Balanced',
    random_seed=42,
    verbose=False
)
cat_model.fit(X_train, y_train)

cat_auc, cat_ll, cat_top1, cat_top3, cat_races = evaluate_topk(
    cat_model, X_test, y_test, test_groups, "CatBoost"
)

# ============================================================
# 🔟 訓練 Ranking 模型
# ============================================================
print("\n🚀 訓練 Ranking 模型...")
rank_model = None
try:
    merged_sorted = merged_valid.sort_values(by=['race_date_str', 'race_no']).reset_index(drop=True)
    group_sizes = merged_sorted.groupby(['race_date_str', 'race_no']).size().tolist()

    X_rank_df = merged_sorted[features_36].copy()
    for col in X_rank_df.columns:
        if X_rank_df[col].dtype == 'object':
            le = LabelEncoder()
            X_rank_df[col] = le.fit_transform(X_rank_df[col].astype(str))
        X_rank_df[col] = pd.to_numeric(X_rank_df[col], errors='coerce').fillna(0)
    X_rank = X_rank_df.values.astype(np.float32)
    y_rank = merged_sorted['target'].values.astype(int)

    if sum(group_sizes) == len(X_rank):
        rank_model = XGBRanker(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            objective='rank:pairwise',
            random_state=42
        )
        rank_model.fit(X_rank, y_rank, group=group_sizes)
        print("  ✅ Ranking 模型訓練完成！")
    else:
        print("  ⚠️ 分組大小不符，跳過 Ranking")
except Exception as e:
    print(f"  ⚠️ Ranking 訓練失敗：{e}")

# ============================================================
# 1️⃣1️⃣ 儲存模型
# ============================================================
print("\n💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)

cat_model.save_model('hk_catboost_model.cbm')

if rank_model is not None:
    with open('hk_ranking_model.pkl', 'wb') as f:
        pickle.dump(rank_model, f)
    print("  ✅ 已儲存 hk_ranking_model.pkl")

info = {
    "trained_at": datetime.now().isoformat(),
    "xgb_auc": float(xgb_auc),
    "xgb_logloss": float(xgb_ll),
    "xgb_top1": float(xgb_top1),
    "xgb_top3": float(xgb_top3),
    "cat_auc": float(cat_auc),
    "cat_logloss": float(cat_ll),
    "cat_top1": float(cat_top1),
    "cat_top3": float(cat_top3),
    "rank_trained": rank_model is not None,
    "train_samples": len(X_train),
    "test_samples": len(X_test),
    "test_races": xgb_races,
    "features_used": features_36
}
with open("model_info.json", "w", encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print("\n📝 訓練資訊已儲存到 model_info.json")
print(f"\n🎯 最終結果：")
print(f"   XGBoost  - AUC: {xgb_auc:.4f}, Top-1: {xgb_top1:.2%}, Top-3: {xgb_top3:.2%}")
print(f"   CatBoost - AUC: {cat_auc:.4f}, Top-1: {cat_top1:.2%}, Top-3: {cat_top3:.2%}")
print("🎉 自動訓練完成！")
