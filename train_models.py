#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 完整特徵版
從 ALL_DATA_MERGED.csv 計算 26+ 特徵
"""

import pandas as pd
import numpy as np
import pickle
import warnings
import json
warnings.filterwarnings('ignore')
from datetime import datetime
from sklearn.model_selection import GroupShuffleSplit
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
# 2️⃣ 欄位標準化
# ============================================================
print("🔧 標準化欄位...")

# 名次
for col in ['Pla.', 'finish_position', '名次']:
    if col in df.columns:
        cleaned = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        if cleaned.notna().sum() > 100:
            df['real_pos'] = cleaned
            print(f"  ✅ 名次：'{col}'")
            break

# 日期
df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
df = df.dropna(subset=['race_date'])
df['race_date_str'] = df['race_date'].dt.strftime('%Y%m%d')

# 場次
if 'race_no' in df.columns:
    df['race_no'] = df['race_no'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce').fillna(0).astype(int)

# horse_id
df['horse_id'] = df['horse_id'].astype(str).str.strip()

# 清洗
df = df.dropna(subset=['real_pos'])
df = df[df['horse_id'].str.len() > 0]
df = df[df['race_no'] > 0]

df['finish_position'] = df['real_pos']
df['target'] = (df['finish_position'] == 1).astype(int)

print(f"  清洗後：{len(df)} 筆，頭馬：{df['target'].mean():.2%}")

# ============================================================
# 3️⃣ 基本特徵（賽前已知）
# ============================================================
def safe_num(s):
    return pd.to_numeric(s, errors='coerce').fillna(0)

df['draw'] = safe_num(df.get('draw', 0))
df['Rtg.'] = safe_num(df.get('Rtg.', 0))
df['win_odds'] = safe_num(df.get('Win Odds', df.get('win_odds', 0)))
df['weight'] = safe_num(df.get('Act.Wt.', df.get('weight', 0)))
df['distance'] = safe_num(df.get('Dist.', df.get('distance', 0)))
df['finish_speed'] = safe_num(df.get('FSpeed', 0))

# 清理 race_course / going / jockey / trainer / Sire
for c in ['race_course', 'going', 'jockey', 'trainer', 'Sire']:
    if c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    else:
        df[c] = ''

# 賠率排名（每場）
df['odds_rank_in_race'] = df.groupby(['race_date_str', 'race_no'])['win_odds'].rank(
    method='min', ascending=True
).fillna(0)

# ============================================================
# 4️⃣ 按場次分組拆分（防 leakage）
# ============================================================
print("📂 按場次分組拆分...")

df['_group'] = df['race_date_str'] + "_" + df['race_no'].astype(str)
group_counts = df.groupby('_group').size()
valid_groups = group_counts[group_counts >= 4].index
df = df[df['_group'].isin(valid_groups)].copy()

group_list = df['_group'].unique()
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
fake_X = np.zeros((len(group_list), 1))
train_g, test_g = next(gss.split(fake_X, groups=group_list))
train_groups = set(group_list[train_g])
test_groups_set = set(group_list[test_g])

df_train = df[df['_group'].isin(train_groups)].copy()
df_test = df[df['_group'].isin(test_groups_set)].copy()

print(f"  訓練：{df_train['_group'].nunique()} 場，{len(df_train)} 筆")
print(f"  測試：{df_test['_group'].nunique()} 場，{len(df_test)} 筆")

# ============================================================
# 5️⃣ 計算勝率特徵（只用訓練集）
# ============================================================
print("🔧 計算勝率特徵...")

# 騎師 / 練馬師勝率
jockey_rate = df_train.groupby('jockey')['target'].mean().to_dict()
trainer_rate = df_train.groupby('trainer')['target'].mean().to_dict()

# 騎練組合勝率
jt_rate = df_train.groupby(['jockey', 'trainer'])['target'].mean().to_dict()

# 馬匹+騎師組合
jh_rate = df_train.groupby(['jockey', 'horse_id'])['target'].mean().to_dict()

# 馬匹+路程勝率
dist_stats = df_train.groupby(['horse_id', 'distance'])['target'].agg(['mean', 'count']).reset_index()
dist_rate = dist_stats.set_index(['horse_id', 'distance'])['mean'].to_dict()

# 馬匹+路程平均名次
dist_rank = df_train.groupby(['horse_id', 'distance'])['finish_position'].mean().to_dict()

# 馬匹+場地勝率
course_rate = df_train.groupby(['horse_id', 'race_course'])['target'].mean().to_dict()
course_rank = df_train.groupby(['horse_id', 'race_course'])['finish_position'].mean().to_dict()

# 馬匹+going勝率
going_rate = df_train.groupby(['horse_id', 'going'])['target'].mean().to_dict()

# Sire 勝率
sire_rate = df_train.groupby('Sire')['target'].mean().to_dict()
sire_course_rate = df_train.groupby(['Sire', 'race_course'])['target'].mean().to_dict()

# 抽檔勝率
draw_rate = df_train.groupby('draw')['target'].mean().to_dict()

# ============================================================
# 6️⃣ 歷史特徵（時序，用 shift 防泄漏）
# ============================================================
print("🔧 計算歷史特徵...")

for d in [df_train, df_test]:
    d.sort_values(['horse_id', 'race_date'], inplace=True)
    d['avg_rank_last3'] = d.groupby('horse_id')['finish_position'].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(99)

    d['weight_change'] = d.groupby('horse_id')['weight'].diff().fillna(0)
    d['rtg_change'] = d.groupby('horse_id')['Rtg.'].diff().fillna(0)

    # 出賽相隔日數
    d['race_date_numeric'] = d['race_date'].astype(np.int64) // 10**9
    d['days_since_last_run'] = (d.groupby('horse_id')['race_date_numeric'].diff() / 86400).fillna(999).clip(0, 999)

    # 近 14 日出賽次數
    d['races_last14days'] = d.groupby('horse_id')['race_date'].transform(
        lambda x: x.expanding().count() - 1
    ).fillna(0).clip(0, 10)

# 騎師近 5 / 10 場勝率（時序）
jockey_recent5 = df_train.sort_values('race_date').groupby('jockey')['target'].transform(
    lambda x: x.shift(1).rolling(5, min_periods=1).mean()
)
jockey_recent10 = df_train.sort_values('race_date').groupby('jockey')['target'].transform(
    lambda x: x.shift(1).rolling(10, min_periods=1).mean()
)
df_train['jockey_win_rate_5'] = jockey_recent5.fillna(0)
df_train['jockey_win_rate_10'] = jockey_recent10.fillna(0)

# 測試集用訓練集嘅平均值
jockey_avg5 = df_train.groupby('jockey')['jockey_win_rate_5'].mean().to_dict()
jockey_avg10 = df_train.groupby('jockey')['jockey_win_rate_10'].mean().to_dict()
df_test['jockey_win_rate_5'] = df_test['jockey'].map(jockey_avg5).fillna(0)
df_test['jockey_win_rate_10'] = df_test['jockey'].map(jockey_avg10).fillna(0)

# ============================================================
# 7️⃣ Map 所有勝率特徵
# ============================================================
print("🔧 Map 勝率特徵...")

for d in [df_train, df_test]:
    d['jockey_win_rate_50'] = d['jockey'].map(jockey_rate).fillna(0)
    d['trainer_win_rate_50'] = d['trainer'].map(trainer_rate).fillna(0)
    d['jockey_trainer_win_rate'] = d.apply(
        lambda r: jt_rate.get((r['jockey'], r['trainer']), 0), axis=1
    )
    d['jockey_horse_win_rate'] = d.apply(
        lambda r: jh_rate.get((r['jockey'], r['horse_id']), 0), axis=1
    )
    d['distance_win_rate'] = d.apply(
        lambda r: dist_rate.get((r['horse_id'], r['distance']), 0), axis=1
    )
    d['distance_avg_rank'] = d.apply(
        lambda r: dist_rank.get((r['horse_id'], r['distance']), 99), axis=1
    )
    d['course_win_rate'] = d.apply(
        lambda r: course_rate.get((r['horse_id'], r['race_course']), 0), axis=1
    )
    d['course_avg_rank'] = d.apply(
        lambda r: course_rank.get((r['horse_id'], r['race_course']), 99), axis=1
    )
    d['going_win_rate'] = d.apply(
        lambda r: going_rate.get((r['horse_id'], r['going']), 0), axis=1
    )
    d['sire_win_rate'] = d['Sire'].map(sire_rate).fillna(0)
    d['sire_course_win_rate'] = d.apply(
        lambda r: sire_course_rate.get((r['Sire'], r['race_course']), 0), axis=1
    )
    d['draw_win_rate'] = d['draw'].map(draw_rate).fillna(0)

# ============================================================
# 8️⃣ 最終特徵列表（36 個）
# ============================================================
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

for d in [df_train, df_test]:
    for f in features_all:
        if f not in d.columns:
            d[f] = 0
        d[f] = pd.to_numeric(d[f], errors='coerce').fillna(0)

X_train = df_train[features_all].astype(np.float32)
y_train = df_train['target'].astype(int)
X_test = df_test[features_all].astype(np.float32)
y_test = df_test['target'].astype(int)
test_groups = df_test['_group'].values

# 檢查有幾多特徵真正有值
non_zero_features = [f for f in features_all if df_train[f].abs().sum() > 0]
print(f"  ✅ 有效特徵數：{len(non_zero_features)} / {len(features_all)}")

# ============================================================
# 9️⃣ 評估函數
# ============================================================
def evaluate_topk(model, X_test, y_test, test_groups, name="Model"):
    try:
        proba = model.predict_proba(X_test)[:, 1]
    except Exception:
        proba = model.predict(X_test)

    df_eval = pd.DataFrame({'group': test_groups, 'y_true': y_test.values, 'proba': proba})
    top1_hit = top3_hit = total = 0

    for g, sub in df_eval.groupby('group'):
        if sub['y_true'].sum() == 0:
            continue
        total += 1
        ranked = sub.sort_values('proba', ascending=False).reset_index(drop=True)
        winner_idx = ranked[ranked['y_true'] == 1].index
        if len(winner_idx) == 0:
            continue
        pos = winner_idx[0] + 1
        if pos == 1:
            top1_hit += 1
        if pos <= 3:
            top3_hit += 1

    if total == 0:
        return 0.0, 0.0, 0.0, 0.0, 0

    top1 = top1_hit / total
    top3 = top3_hit / total

    try:
        auc = roc_auc_score(y_test, proba)
    except Exception:
        auc = 0.0
    try:
        ll = log_loss(y_test, proba)
    except Exception:
        ll = 0.0

    print(f"  📊 {name}：")
    print(f"     ├─ AUC：{auc:.4f}")
    print(f"     ├─ Log Loss：{ll:.4f}")
    print(f"     ├─ Top-1：{top1:.2%}（{top1_hit}/{total}）")
    print(f"     └─ Top-3：{top3:.2%}（{top3_hit}/{total}）")

    return auc, ll, top1, top3, total

# ============================================================
# 🔟 訓練
# ============================================================
print("\n🚀 訓練 XGBoost...")
neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
spw = neg / pos if pos > 0 else 1
print(f"  scale_pos_weight = {spw:.2f}")

xgb_model = xgb.XGBClassifier(
    n_estimators=300, learning_rate=0.05, max_depth=6,
    scale_pos_weight=spw, random_state=42,
    use_label_encoder=False, eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)
xgb_auc, xgb_ll, xgb_top1, xgb_top3, xgb_races = evaluate_topk(
    xgb_model, X_test, y_test, test_groups, "XGBoost"
)

print("\n🚀 訓練 CatBoost...")
cat_model = CatBoostClassifier(
    iterations=300, learning_rate=0.05, depth=6,
    auto_class_weights='Balanced', random_seed=42, verbose=False
)
cat_model.fit(X_train, y_train)
cat_auc, cat_ll, cat_top1, cat_top3, cat_races = evaluate_topk(
    cat_model, X_test, y_test, test_groups, "CatBoost"
)

print("\n🚀 訓練 Ranking...")
rank_model = None
try:
    df_r = df_train.sort_values(['race_date_str', 'race_no']).reset_index(drop=True)
    gs = df_r.groupby(['race_date_str', 'race_no']).size().tolist()
    X_r = df_r[features_all].values.astype(np.float32)
    y_r = df_r['target'].values.astype(int)
    if sum(gs) == len(X_r):
        rank_model = XGBRanker(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            objective='rank:pairwise', random_state=42
        )
        rank_model.fit(X_r, y_r, group=gs)
        print("  ✅ Ranking 完成")
except Exception as e:
    print(f"  ⚠️ Ranking 失敗：{e}")

# ============================================================
# 儲存
# ============================================================
print("\n💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)
cat_model.save_model('hk_catboost_model.cbm')
if rank_model is not None:
    with open('hk_ranking_model.pkl', 'wb') as f:
        pickle.dump(rank_model, f)

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
    "features_used": features_all,
    "non_zero_features": len(non_zero_features)
}
with open("model_info.json", "w", encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print(f"\n🎯 最終結果：")
print(f"   XGBoost  - AUC: {xgb_auc:.4f}, Top-1: {xgb_top1:.2%}, Top-3: {xgb_top3:.2%}")
print(f"   CatBoost - AUC: {cat_auc:.4f}, Top-1: {cat_top1:.2%}, Top-3: {cat_top3:.2%}")
print("🎉 完成！")    if col in df.columns:
        cleaned = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        if cleaned.notna().sum() > 100:
            df['real_pos'] = cleaned
            pos_col = col
            print(f"  ✅ 名次欄位：'{col}'")
            break

df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
df = df.dropna(subset=['race_date'])
df['race_date_str'] = df['race_date'].dt.strftime('%Y%m%d')

if 'race_no' in df.columns:
    df['race_no'] = df['race_no'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce').fillna(0).astype(int)

df['horse_id'] = df['horse_id'].astype(str).str.strip()
df = df.dropna(subset=['real_pos'])
df = df[df['horse_id'].str.len() > 0]
df = df[df['race_no'] > 0]

df['finish_position'] = df['real_pos']
df['target'] = (df['finish_position'] == 1).astype(int)

print(f"  清洗後：{len(df)} 筆，頭馬比例：{df['target'].mean():.2%}")

# 基本特徵（賽前已知，唔會 leakage）
def safe_numeric(s):
    return pd.to_numeric(s, errors='coerce').fillna(0)

df['draw'] = safe_numeric(df.get('draw', 0))
df['Rtg.'] = safe_numeric(df.get('Rtg.', 0))
df['win_odds'] = safe_numeric(df.get('win_odds', 0))
df['weight'] = safe_numeric(df.get('act_wt', df.get('weight', 0)))
df['distance'] = safe_numeric(df.get('Dist.', df.get('distance', 0)))

# ============================================================
# 3️⃣ 先拆分，後計勝率（防 leakage）
# ============================================================
print("📂 按場次分組拆分...")

df['_group'] = df['race_date_str'] + "_" + df['race_no'].astype(str)
group_counts = df.groupby('_group').size()
valid_groups = group_counts[group_counts >= 4].index
df = df[df['_group'].isin(valid_groups)].copy()

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
# 用 group 做 split
group_list = df['_group'].unique()
fake_X = np.zeros((len(group_list), 1))
train_g, test_g = next(gss.split(fake_X, groups=group_list))
train_groups = set(group_list[train_g])
test_groups_set = set(group_list[test_g])

df_train = df[df['_group'].isin(train_groups)].copy()
df_test = df[df['_group'].isin(test_groups_set)].copy()

print(f"  訓練場次：{df_train['_group'].nunique()} 場，{len(df_train)} 筆")
print(f"  測試場次：{df_test['_group'].nunique()} 場，{len(df_test)} 筆")

# ============================================================
# 4️⃣ 勝率特徵（只用訓練集計算）
# ============================================================
print("🔧 計算勝率特徵（只用訓練集）...")

# 騎師勝率
if 'jockey' in df_train.columns:
    jockey_stats = df_train.groupby('jockey')['target'].agg(['sum', 'count'])
    jockey_rate = (jockey_stats['sum'] / jockey_stats['count']).to_dict()
else:
    jockey_rate = {}

# 練馬師勝率
if 'trainer' in df_train.columns:
    trainer_stats = df_train.groupby('trainer')['target'].agg(['sum', 'count'])
    trainer_rate = (trainer_stats['sum'] / trainer_stats['count']).to_dict()
else:
    trainer_rate = {}

# 馬匹 + 路程勝率
if 'distance' in df_train.columns:
    dist_stats = df_train.groupby(['horse_id', 'distance'])['target'].agg(['sum', 'count']).reset_index()
    dist_stats['rate'] = dist_stats['sum'] / dist_stats['count']
    dist_rate = dist_stats.set_index(['horse_id', 'distance'])['rate'].to_dict()
else:
    dist_rate = {}

# 賠率排名（按場次，冇 leakage）
for d in [df_train, df_test]:
    d['odds_rank_in_race'] = d.groupby('_group')['win_odds'].rank(method='min', ascending=True).fillna(0)

# avg_rank_last3（時間序列，只用過去）
for d in [df_train, df_test]:
    d_sorted = d.sort_values(['horse_id', 'race_date'])
    d['avg_rank_last3'] = d_sorted.groupby('horse_id')['finish_position'].transform(
        lambda x: x.shift(1).rolling(window=3, min_periods=1).mean()
    ).fillna(99)
    d['days_since_last_run'] = d_sorted.groupby('horse_id')['race_date'].diff().dt.days.fillna(999).clip(0, 999)

# Map 勝率特徵
for d in [df_train, df_test]:
    d['jockey_win_rate_50'] = d['jockey'].map(jockey_rate).fillna(0) if 'jockey' in d.columns else 0
    d['trainer_win_rate_50'] = d['trainer'].map(trainer_rate).fillna(0) if 'trainer' in d.columns else 0
    d['distance_win_rate'] = d.apply(
        lambda r: dist_rate.get((r['horse_id'], r['distance']), 0), axis=1
    ) if 'distance' in d.columns else 0

# ============================================================
# 5️⃣ 最終特徵列表
# ============================================================
features_all = [
    'draw', 'weight', 'distance', 'Rtg.', 'avg_rank_last3',
    'jockey_win_rate_50', 'trainer_win_rate_50',
    'distance_win_rate', 'win_odds', 'days_since_last_run',
    'odds_rank_in_race'
]

# 加其他特徵為 0
all_features_36 = [
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

for d in [df_train, df_test]:
    for f in all_features_36:
        if f not in d.columns:
            d[f] = 0
        d[f] = pd.to_numeric(d[f], errors='coerce').fillna(0)

X_train = df_train[all_features_36].astype(np.float32)
y_train = df_train['target'].astype(int)
X_test = df_test[all_features_36].astype(np.float32)
y_test = df_test['target'].astype(int)
test_groups = df_test['_group'].values

print(f"  特徵數：{len(all_features_36)}")

# ============================================================
# 6️⃣ 評估函數
# ============================================================
def evaluate_topk(model, X_test, y_test, test_groups, model_name="Model"):
    try:
        proba = model.predict_proba(X_test)[:, 1]
    except Exception:
        proba = model.predict(X_test)

    df_eval = pd.DataFrame({'group': test_groups, 'y_true': y_test.values, 'proba': proba})
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
# 7️⃣ 訓練
# ============================================================
print("\n🚀 訓練 XGBoost...")
neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
spw = neg / pos if pos > 0 else 1
print(f"  scale_pos_weight = {spw:.2f}")

xgb_model = xgb.XGBClassifier(
    n_estimators=200, learning_rate=0.05, max_depth=5,
    scale_pos_weight=spw, random_state=42,
    use_label_encoder=False, eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)
xgb_auc, xgb_ll, xgb_top1, xgb_top3, xgb_races = evaluate_topk(
    xgb_model, X_test, y_test, test_groups, "XGBoost"
)

print("\n🚀 訓練 CatBoost...")
cat_model = CatBoostClassifier(
    iterations=200, learning_rate=0.05, depth=5,
    auto_class_weights='Balanced', random_seed=42, verbose=False
)
cat_model.fit(X_train, y_train)
cat_auc, cat_ll, cat_top1, cat_top3, cat_races = evaluate_topk(
    cat_model, X_test, y_test, test_groups, "CatBoost"
)

print("\n🚀 訓練 Ranking...")
rank_model = None
try:
    df_r = df_train.sort_values(['race_date_str', 'race_no']).reset_index(drop=True)
    gs = df_r.groupby(['race_date_str', 'race_no']).size().tolist()
    X_r = df_r[all_features_36].values.astype(np.float32)
    y_r = df_r['target'].values.astype(int)
    if sum(gs) == len(X_r):
        rank_model = XGBRanker(
            n_estimators=200, learning_rate=0.05, max_depth=5,
            objective='rank:pairwise', random_state=42
        )
        rank_model.fit(X_r, y_r, group=gs)
        print("  ✅ Ranking 完成")
except Exception as e:
    print(f"  ⚠️ Ranking 失敗：{e}")

# ============================================================
# 8️⃣ 儲存
# ============================================================
print("\n💾 儲存模型...")
with open('hk_racing_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)
cat_model.save_model('hk_catboost_model.cbm')
if rank_model is not None:
    with open('hk_ranking_model.pkl', 'wb') as f:
        pickle.dump(rank_model, f)

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
    "features_used": all_features_36
}
with open("model_info.json", "w", encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print(f"\n🎯 最終結果：")
print(f"   XGBoost  - AUC: {xgb_auc:.4f}, Top-1: {xgb_top1:.2%}, Top-3: {xgb_top3:.2%}")
print(f"   CatBoost - AUC: {cat_auc:.4f}, Top-1: {cat_top1:.2%}, Top-3: {cat_top3:.2%}")
print("🎉 完成！")
