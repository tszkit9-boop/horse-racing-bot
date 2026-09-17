#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 直接用 ALL_DATA_MERGED.csv 訓練
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

df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
print(f"  原始數據：{len(df)} 筆")

# ============================================================
# 2️⃣ 標準化欄位
# ============================================================
print("🔧 標準化欄位...")

# 尋找名次欄位
pos_candidates = ['Pla.', 'finish_position', '名次', '最終名次', 'Finish_Rank', 'result_position']
pos_col = None
for col in pos_candidates:
    if col in df.columns:
        cleaned = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        if cleaned.notna().sum() > 100:
            df['real_pos'] = cleaned
            pos_col = col
            print(f"  ✅ 名次欄位：'{col}'")
            break

if pos_col is None:
    print("❌ 找不到名次欄位")
    exit(1)

# 確保有 race_date
if 'race_date' not in df.columns:
    print("❌ 冇 race_date 欄位")
    exit(1)

df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
df = df.dropna(subset=['race_date'])
df['race_date_str'] = df['race_date'].dt.strftime('%Y%m%d')

# 確保有 race_no
if 'race_no' in df.columns:
    df['race_no'] = df['race_no'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce').fillna(0).astype(int)

# 確保有 horse_id
if 'horse_id' not in df.columns:
    print("❌ 冇 horse_id 欄位")
    exit(1)
df['horse_id'] = df['horse_id'].astype(str).str.strip()

# 過濾無效行
df = df.dropna(subset=['real_pos'])
df = df[df['horse_id'].str.len() > 0]
df = df[df['race_no'] > 0]

print(f"  清洗後數據：{len(df)} 筆")

# ============================================================
# 3️⃣ 目標標籤
# ============================================================
df['finish_position'] = df['real_pos']
df['target'] = (df['finish_position'] == 1).astype(int)

if df['target'].nunique() < 2:
    print("❌ 只有一個類別")
    exit(1)

print(f"  頭馬比例：{df['target'].mean():.2%}")
print(f"  唯一場次：{df.groupby(['race_date_str', 'race_no']).ngroups}")

# ============================================================
# 4️⃣ 特徵工程
# ============================================================
print("🔧 特徵工程...")

# 基本特徵（從 CSV 直接攞）
def safe_numeric(series):
    return pd.to_numeric(series, errors='coerce').fillna(0)

# 初始化特徵
df['draw'] = safe_numeric(df.get('draw', 0))
df['Rtg.'] = safe_numeric(df.get('Rtg.', 0))
df['win_odds'] = safe_numeric(df.get('win_odds', 0))
df['weight'] = safe_numeric(df.get('act_wt', df.get('weight', 0)))
df['distance'] = safe_numeric(df.get('Dist.', df.get('distance', 0)))

# 賠率排名
df['odds_rank_in_race'] = df.groupby(['race_date_str', 'race_no'])['win_odds'].rank(method='min', ascending=True).fillna(0)

# 馬匹近 3 場平均名次
print("  計算 avg_rank_last3...")
df_sorted = df.sort_values(['horse_id', 'race_date'])
df['avg_rank_last3'] = df_sorted.groupby('horse_id')['finish_position'].transform(
    lambda x: x.shift(1).rolling(window=3, min_periods=1).mean()
).fillna(99)

# 騎師勝率
print("  計算 jockey_win_rate_50...")
if 'jockey' in df.columns:
    jockey_stats = df.groupby('jockey')['target'].agg(['sum', 'count'])
    jockey_win_rate = (jockey_stats['sum'] / jockey_stats['count']).to_dict()
    df['jockey_win_rate_50'] = df['jockey'].map(jockey_win_rate).fillna(0)
else:
    df['jockey_win_rate_50'] = 0

# 練馬師勝率
print("  計算 trainer_win_rate_50...")
if 'trainer' in df.columns:
    trainer_stats = df.groupby('trainer')['target'].agg(['sum', 'count'])
    trainer_win_rate = (trainer_stats['sum'] / trainer_stats['count']).to_dict()
    df['trainer_win_rate_50'] = df['trainer'].map(trainer_win_rate).fillna(0)
else:
    df['trainer_win_rate_50'] = 0

# 出賽相隔日數
print("  計算 days_since_last_run...")
df['race_date_numeric'] = df['race_date'].astype(np.int64) // 10**9  # 轉秒
df['days_since_last_run'] = df.groupby('horse_id')['race_date_numeric'].diff() / 86400
df['days_since_last_run'] = df['days_since_last_run'].fillna(999).clip(0, 999)

# 同路程勝率
print("  計算 distance_win_rate...")
if 'distance' in df.columns:
    dist_stats = df.groupby(['horse_id', 'distance'])['target'].agg(['sum', 'count']).reset_index()
    dist_stats['rate'] = dist_stats['sum'] / dist_stats['count']
    dist_map = dist_stats.set_index(['horse_id', 'distance'])['rate'].to_dict()
    df['distance_win_rate'] = df.apply(
        lambda r: dist_map.get((r['horse_id'], r['distance']), 0), axis=1
    )
else:
    df['distance_win_rate'] = 0

# 填充其餘特徵為 0
features_all = [
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

for f in features_all:
    if f not in df.columns:
        df[f] = 0
    else:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)

# ============================================================
# 5️⃣ 準備 X, y, groups
# ============================================================
print("📂 準備訓練數據...")

df_valid = df[df['race_date_str'].notna()].copy()
df_valid['_group'] = df_valid['race_date_str'] + "_" + df_valid['race_no'].astype(str)

# 過濾有 4 匹馬以上嘅場次
group_counts = df_valid.groupby('_group').size()
valid_groups = group_counts[group_counts >= 4].index
df_valid = df_valid[df_valid['_group'].isin(valid_groups)].copy()

print(f"  有效場次：{df_valid['_group'].nunique()} 場")
print(f"  有效數據：{len(df_valid)} 筆")

if len(df_valid) < 100:
    print("❌ 數據太少")
    exit(1)

X = df_valid[features_all].copy().astype(np.float32)
y = df_valid['target'].astype(int)
groups = df_valid['_group'].values

# ============================================================
# 6️⃣ 按場次分組拆分
# ============================================================
print("📂 按場次分組拆分...")

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=groups))

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]
y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]
test_groups = df_valid.iloc[test_idx]['_group'].values

print(f"  訓練集：{len(X_train)} 筆")
print(f"  測試集：{len(X_test)} 筆")
print(f"  測試場次：{len(set(test_groups))} 場")

# ============================================================
# 7️⃣ 評估函數
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

    print(f"  📊 {model_name}：")
    print(f"     ├─ AUC：{auc:.4f}")
    print(f"     ├─ Log Loss：{ll:.4f}")
    print(f"     ├─ Top-1 命中率：{top1_acc:.2%}（{top1_hit}/{total_races}）")
    print(f"     └─ Top-3 命中率：{top3_acc:.2%}（{top3_hit}/{total_races}）")

    return auc, ll, top1_acc, top3_acc, total_races

# ============================================================
# 8️⃣ XGBoost
# ============================================================
print("\n🚀 訓練 XGBoost...")
neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
spw = neg / pos if pos > 0 else 1
print(f"  scale_pos_weight = {spw:.2f}")

xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    scale_pos_weight=spw,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)
xgb_auc, xgb_ll, xgb_top1, xgb_top3, xgb_races = evaluate_topk(
    xgb_model, X_test, y_test, test_groups, "XGBoost"
)

# ============================================================
# 9️⃣ CatBoost
# ============================================================
print("\n🚀 訓練 CatBoost...")
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
# 🔟 Ranking
# ============================================================
print("\n🚀 訓練 Ranking...")
rank_model = None
try:
    df_rank = df_valid.sort_values(['race_date_str', 'race_no']).reset_index(drop=True)
    group_sizes = df_rank.groupby(['race_date_str', 'race_no']).size().tolist()
    X_rank = df_rank[features_all].values.astype(np.float32)
    y_rank = df_rank['target'].values.astype(int)

    if sum(group_sizes) == len(X_rank):
        rank_model = XGBRanker(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            objective='rank:pairwise',
            random_state=42
        )
        rank_model.fit(X_rank, y_rank, group=group_sizes)
        print("  ✅ Ranking 完成")
    else:
        print("  ⚠️ 分組大小不符，跳過")
except Exception as e:
    print(f"  ⚠️ Ranking 失敗：{e}")

# ============================================================
# 1️⃣1️⃣ 儲存
# ============================================================
print("\n💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)
cat_model.save_model('hk_catboost_model.cbm')
if rank_model is not None:
    with open('hk_ranking_model.pkl', 'wb') as f:
        pickle.dump(rank_model, f)
    print("  ✅ hk_ranking_model.pkl")

info = {
    "trained_at": datetime.now().isoformat(),
    "xgb_auc": float(xgb_auc),
    "xgb_top1": float(xgb_top1),
    "xgb_top3": float(xgb_top3),
    "cat_auc": float(cat_auc),
    "cat_top1": float(cat_top1),
    "cat_top3": float(cat_top3),
    "rank_trained": rank_model is not None,
    "train_samples": len(X_train),
    "test_samples": len(X_test),
    "test_races": xgb_races,
    "features_used": features_all
}
with open("model_info.json", "w", encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print(f"\n🎯 最終結果：")
print(f"   XGBoost  - AUC: {xgb_auc:.4f}, Top-1: {xgb_top1:.2%}, Top-3: {xgb_top3:.2%}")
print(f"   CatBoost - AUC: {cat_auc:.4f}, Top-1: {cat_top1:.2%}, Top-3: {cat_top3:.2%}")
print("🎉 完成！")
