#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_models.py - 用 36 特徵（與 app 一致），危險特徵設 0
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
# 1️⃣ 讀取
# ============================================================
print("📊 讀取數據...")
df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
print(f"  原始數據：{len(df)} 筆")

# ============================================================
# 2️⃣ 欄位標準化
# ============================================================
print("🔧 標準化欄位...")

for col in ['Pla.', 'finish_position', '名次']:
    if col in df.columns:
        cleaned = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        if cleaned.notna().sum() > 100:
            df['real_pos'] = cleaned
            print(f"  ✅ 名次：'{col}'")
            break

df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
df = df.dropna(subset=['race_date'])
df['race_date_str'] = df['race_date'].dt.strftime('%Y%m%d')

df['race_no'] = pd.to_numeric(df['race_no'].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
df['horse_id'] = df['horse_id'].astype(str).str.strip()

df = df.dropna(subset=['real_pos'])
df = df[df['horse_id'].str.len() > 0]
df = df[df['race_no'] > 0]
df = df[df['horse_id'].str.match(r'^[A-Z]\d{3}$', na=False)]

df['finish_position'] = df['real_pos']
df['target'] = (df['finish_position'] == 1).astype(int)

print(f"  清洗後：{len(df)} 筆，頭馬：{df['target'].mean():.2%}")

# ============================================================
# 3️⃣ 特徵（與 app 一致：36 個）
# ============================================================
def safe_num(s, default=0):
    return pd.to_numeric(s, errors='coerce').fillna(default)

# 基本
df['draw'] = safe_num(df.get('draw', 0))
df['Rtg.'] = safe_num(df.get('Rtg.', 0))
df['win_odds'] = safe_num(df.get('Win Odds', df.get('win_odds', 0)))
df['weight'] = safe_num(df.get('Act.Wt.', 0))
df['distance'] = safe_num(df.get('Dist.', 0))
df['finish_speed'] = safe_num(df.get('FSpeed', 0))
df['lbw'] = safe_num(df.get('LBW', 0))
df['age'] = safe_num(df.get('Age', 0))

rc = df.get('RC/Track/Course', pd.Series(dtype=str)).astype(str)
df['is_turf'] = rc.str.contains('Turf', case=False, na=False).astype(int)
df['is_st'] = rc.str.contains('ST', case=False, na=False).astype(int)
df['is_hv'] = rc.str.contains('HV', case=False, na=False).astype(int)

for c in ['race_course', 'going', 'jockey', 'trainer']:
    df[c] = df.get(c, pd.Series(dtype=str)).astype(str).str.strip()

df['odds_rank_in_race'] = df.groupby(['race_date_str', 'race_no'])['win_odds'].rank(method='min', ascending=True).fillna(0)

# ============================================================
# 4️⃣ 分組拆分
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
# 5️⃣ 勝率特徵
# ============================================================
print("🔧 計算勝率特徵...")

jockey_rate = df_train.groupby('jockey')['target'].mean().to_dict()
trainer_rate = df_train.groupby('trainer')['target'].mean().to_dict()
jt_rate = df_train.groupby(['jockey', 'trainer'])['target'].mean().to_dict()
jh_rate = df_train.groupby(['jockey', 'horse_id'])['target'].mean().to_dict()

dist_stats = df_train.groupby(['horse_id', 'distance'])['target'].agg(['mean', 'count']).reset_index()
dist_rate = dist_stats.set_index(['horse_id', 'distance'])['mean'].to_dict()
dist_rank = df_train.groupby(['horse_id', 'distance'])['finish_position'].mean().to_dict()

course_rate = df_train.groupby(['horse_id', 'race_course'])['target'].mean().to_dict()
course_rank = df_train.groupby(['horse_id', 'race_course'])['finish_position'].mean().to_dict()

going_rate = df_train.groupby(['horse_id', 'going'])['target'].mean().to_dict()

draw_rate = df_train.groupby('draw')['target'].mean().to_dict()

# ============================================================
# 6️⃣ 歷史特徵
# ============================================================
print("🔧 計算歷史特徵...")

for d in [df_train, df_test]:
    d.sort_values(['horse_id', 'race_date'], inplace=True)
    d['avg_rank_last3'] = d.groupby('horse_id')['finish_position'].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(99)

    d['weight_change'] = d.groupby('horse_id')['weight'].diff().fillna(0)
    d['rtg_change'] = d.groupby('horse_id')['Rtg.'].diff().fillna(0)

    d['race_date_numeric'] = d['race_date'].astype(np.int64) // 10**9
    d['days_since_last_run'] = (d.groupby('horse_id')['race_date_numeric'].diff() / 86400).fillna(999).clip(0, 999)

    d['races_last14days'] = d.groupby('horse_id')['race_date'].transform(
        lambda x: x.expanding().count() - 1
    ).fillna(0).clip(0, 10)

df_train_sorted = df_train.sort_values('race_date').copy()
df_train_sorted['jockey_win_rate_5'] = df_train_sorted.groupby('jockey')['target'].transform(
    lambda x: x.shift(1).rolling(5, min_periods=1).mean()
).fillna(0)
df_train_sorted['jockey_win_rate_10'] = df_train_sorted.groupby('jockey')['target'].transform(
    lambda x: x.shift(1).rolling(10, min_periods=1).mean()
).fillna(0)

jockey_avg5 = df_train_sorted.groupby('jockey')['jockey_win_rate_5'].mean().to_dict()
jockey_avg10 = df_train_sorted.groupby('jockey')['jockey_win_rate_10'].mean().to_dict()

df_train['jockey_win_rate_5'] = df_train['jockey'].map(jockey_avg5).fillna(0)
df_train['jockey_win_rate_10'] = df_train['jockey'].map(jockey_avg10).fillna(0)
df_test['jockey_win_rate_5'] = df_test['jockey'].map(jockey_avg5).fillna(0)
df_test['jockey_win_rate_10'] = df_test['jockey'].map(jockey_avg10).fillna(0)

# ============================================================
# 7️⃣ Map 勝率
# ============================================================
print("🔧 Map 勝率特徵...")

for d in [df_train, df_test]:
    d['jockey_win_rate_50'] = d['jockey'].map(jockey_rate).fillna(0)
    d['trainer_win_rate_50'] = d['trainer'].map(trainer_rate).fillna(0)
    d['jockey_trainer_win_rate'] = d.apply(lambda r: jt_rate.get((r['jockey'], r['trainer']), 0), axis=1)
    d['jockey_horse_win_rate'] = d.apply(lambda r: jh_rate.get((r['jockey'], r['horse_id']), 0), axis=1)
    d['distance_win_rate'] = d.apply(lambda r: dist_rate.get((r['horse_id'], r['distance']), 0), axis=1)
    d['distance_avg_rank'] = d.apply(lambda r: dist_rank.get((r['horse_id'], r['distance']), 99), axis=1)
    d['course_win_rate'] = d.apply(lambda r: course_rate.get((r['horse_id'], r['race_course']), 0), axis=1)
    d['course_avg_rank'] = d.apply(lambda r: course_rank.get((r['horse_id'], r['race_course']), 99), axis=1)
    d['going_win_rate'] = d.apply(lambda r: going_rate.get((r['horse_id'], r['going']), 0), axis=1)
    d['draw_win_rate'] = d['draw'].map(draw_rate).fillna(0)

# ============================================================
# 8️⃣ 最終特徵（36 個，與 app 一致）
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

# 冇嘅特徵設 0（包括危險特徵）
for d in [df_train, df_test]:
    for f in features_all:
        if f not in d.columns:
            d[f] = 0
        d[f] = pd.to_numeric(d[f], errors='coerce').fillna(0)

# 🛡️ 危險特徵強制歸 0（避免洩漏）
dangerous = ['early_pace', 'finish_speed', 'last_trial_rank', 'last_trial_time',
             'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
             'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
             'total_injuries', 'injury_severity']
for d in [df_train, df_test]:
    for f in dangerous:
        d[f] = 0

X_train = df_train[features_all].astype(np.float32)
y_train = df_train['target'].astype(int)
X_test = df_test[features_all].astype(np.float32)
y_test = df_test['target'].astype(int)
test_groups = df_test['_group'].values

non_zero = [f for f in features_all if df_train[f].abs().sum() > 0]
print(f"  ✅ 有效特徵：{len(non_zero)} / {len(features_all)}")
print(f"  🛡️ 危險特徵已歸 0：{len(dangerous)} 個")

# ============================================================
# 9️⃣ 評估
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
    n_estimators=300, learning_rate=0.05, max_depth=5,
    scale_pos_weight=spw, random_state=42,
    use_label_encoder=False, eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)
xgb_auc, xgb_ll, xgb_top1, xgb_top3, xgb_races = evaluate_topk(
    xgb_model, X_test, y_test, test_groups, "XGBoost"
)

print("\n🚀 訓練 CatBoost...")
cat_model = CatBoostClassifier(
    iterations=300, learning_rate=0.05, depth=5,
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
            n_estimators=300, learning_rate=0.05, max_depth=5,
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
    "non_zero_features": len(non_zero)
}
with open("model_info.json", "w", encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print(f"\n🎯 最終結果：")
print(f"   XGBoost  - AUC: {xgb_auc:.4f}, Top-1: {xgb_top1:.2%}, Top-3: {xgb_top3:.2%}")
print(f"   CatBoost - AUC: {cat_auc:.4f}, Top-1: {cat_top1:.2%}, Top-3: {cat_top3:.2%}")
print("🎉 完成！")
