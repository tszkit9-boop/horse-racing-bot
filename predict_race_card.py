#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
predict_race_card.py - 終極完成版（已修正賠率處理）
"""

import pandas as pd
import numpy as np
import pickle
import re
import warnings
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier

# ============================================================
# 1. 定義 36 個特徵（訓練時使用嘅英文變量名，用於生成）
# ============================================================
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

# ============================================================
# 2. 模型期望嘅特徵名稱（中文）及對應順序
# ============================================================
EXPECTED_FEATURES = [
    'draw', 'weight', 'distance', 'Rtg.', '近3場平均名次',
    '騎師近50場勝率', '練馬師近50場勝率', '同路程歷史勝率',
    '同路程歷史平均名次', 'win_odds', '體重變化', '騎練組合勝率',
    '詳細賽道歷史勝率', '詳細賽道歷史平均名次', '出賽相隔日數',
    '賠率場次排名', '評分變化', '騎馬合作勝率', '近14日出賽次數',
    '場地狀況勝率', '試閘歷史勝率', '父系歷史勝率', '父系同程勝率',
    '前速指標', '後勁指標', '最近試閘名次', '最近試閘時間',
    '騎師近5場勝率', '騎師近10場勝率', '檔位勝率', '最近傷患日數',
    '過去30日內有傷患', '過去60日內有傷患', '過去90日內有傷患',
    '傷患總次數', '傷患嚴重程度'
]

# ============================================================
# 3. 建立英文 → 中文/模型名稱 映射
# ============================================================
NAME_MAPPING = {
    'act_wt': 'weight',
    'rtg': 'Rtg.',
    'avg_rank_last3': '近3場平均名次',
    'jockey_win_rate_50': '騎師近50場勝率',
    'trainer_win_rate_50': '練馬師近50場勝率',
    'distance_win_rate': '同路程歷史勝率',
    'distance_avg_rank': '同路程歷史平均名次',
    'weight_change': '體重變化',
    'jockey_trainer_win_rate': '騎練組合勝率',
    'course_win_rate': '詳細賽道歷史勝率',
    'course_avg_rank': '詳細賽道歷史平均名次',
    'days_since_last_run': '出賽相隔日數',
    'odds_rank_in_race': '賠率場次排名',
    'rtg_change': '評分變化',
    'jockey_horse_win_rate': '騎馬合作勝率',
    'races_last14days': '近14日出賽次數',
    'going_win_rate': '場地狀況勝率',
    'trial_win_rate': '試閘歷史勝率',
    'sire_win_rate': '父系歷史勝率',
    'sire_course_win_rate': '父系同程勝率',
    'early_pace': '前速指標',
    'finish_speed': '後勁指標',
    'last_trial_rank': '最近試閘名次',
    'last_trial_time': '最近試閘時間',
    'jockey_win_rate_5': '騎師近5場勝率',
    'jockey_win_rate_10': '騎師近10場勝率',
    'draw_win_rate': '檔位勝率',
    'days_since_injury': '最近傷患日數',
    'injury_30d': '過去30日內有傷患',
    'injury_60d': '過去60日內有傷患',
    'injury_90d': '過去90日內有傷患',
    'total_injuries': '傷患總次數',
    'injury_severity': '傷患嚴重程度'
}
# draw, distance, win_odds 保持不變

# ============================================================
# 4. 其他輔助函數
# ============================================================
def standardize_columns(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '比賽日期': 'race_date', '場次': 'race_no',
        '馬場': 'race_course', '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        'Position': 'finish_position', 'Rank': 'finish_position',
        'pos': 'finish_position', '排名': 'finish_position'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    return df

def ensure_series(df):
    for col in df.columns:
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    return df

def ensure_finish_position(df, df_name):
    if 'finish_position' in df.columns:
        return df
    candidates = ['名次', '最終名次', 'Position', 'Rank', 'pos', 'finish', '排名', '名']
    for col in candidates:
        if col in df.columns:
            df.rename(columns={col: 'finish_position'}, inplace=True)
            print(f"✅ {df_name}: 將欄位 '{col}' 重新命名為 'finish_position'")
            return df
    for col in df.columns:
        if '名' in col or '次' in col or 'rank' in col.lower():
            df.rename(columns={col: 'finish_position'}, inplace=True)
            print(f"✅ {df_name}: 將欄位 '{col}' 重新命名為 'finish_position'")
            return df
    raise KeyError(f"在 {df_name} 中找不到名次欄位，可用欄位: {df.columns.tolist()}")

def get_latest_features(race_df, history_df):
    history_df['race_date'] = pd.to_datetime(history_df['race_date'], errors='coerce')
    latest = history_df.sort_values('race_date').groupby('horse_id').last().reset_index()
    merged = race_df.merge(latest, on='horse_id', how='left', suffixes=('', '_hist'))
    for col in FEATURES_EN:
        if col in merged.columns and col not in race_df.columns:
            hist_col = col + '_hist'
            if hist_col in merged.columns:
                merged[col] = merged[hist_col]
            else:
                merged[col] = 0
        elif col not in merged.columns:
            merged[col] = 0
        merged[col] = merged[col].fillna(0)
    for col in ['draw', 'act_wt', 'distance', 'rtg', 'win_odds']:
        if col in race_df.columns:
            merged[col] = race_df[col].values
    return merged

def compute_stats(race_df, history_df, race_date):
    history_df = ensure_series(history_df)
    if history_df.columns.duplicated().any():
        history_df = history_df.loc[:, ~history_df.columns.duplicated(keep='first')]
    
    for col in ['jockey', 'trainer', 'horse_id']:
        if col not in race_df.columns:
            race_df[col] = 0
    
    hist = history_df[history_df['race_date'] < race_date].copy()
    
    if hist.empty:
        for col in ['jockey_win_rate_50', 'trainer_win_rate_50', 'avg_rank_last3',
                    'distance_win_rate', 'jockey_horse_win_rate', 'going_win_rate',
                    'draw_win_rate', 'jockey_win_rate_5', 'jockey_win_rate_10']:
            race_df[col] = 0.0
        return race_df
    
    if 'finish_position' not in hist.columns:
        raise KeyError(f"歷史數據缺少 finish_position，可用欄位: {hist.columns.tolist()}")
    hist['finish_position'] = pd.to_numeric(hist['finish_position'], errors='coerce')
    
    # 騎師勝率
    try:
        jockey_stats = hist.groupby('jockey').apply(lambda g: (g['finish_position']==1).sum()/max(len(g),1)).reset_index(name='jockey_win_rate_50')
        race_df = race_df.merge(jockey_stats, on='jockey', how='left')
        if 'jockey_win_rate_50' not in race_df.columns:
            race_df['jockey_win_rate_50'] = 0.0
        race_df['jockey_win_rate_50'] = race_df['jockey_win_rate_50'].fillna(0)
    except Exception as e:
        print(f"⚠️ 騎師勝率計算失敗: {e}，設為 0")
        race_df['jockey_win_rate_50'] = 0.0
    
    # 練馬師勝率
    try:
        trainer_stats = hist.groupby('trainer').apply(lambda g: (g['finish_position']==1).sum()/max(len(g),1)).reset_index(name='trainer_win_rate_50')
        race_df = race_df.merge(trainer_stats, on='trainer', how='left')
        if 'trainer_win_rate_50' not in race_df.columns:
            race_df['trainer_win_rate_50'] = 0.0
        race_df['trainer_win_rate_50'] = race_df['trainer_win_rate_50'].fillna(0)
    except Exception as e:
        print(f"⚠️ 練馬師勝率計算失敗: {e}，設為 0")
        race_df['trainer_win_rate_50'] = 0.0
    
    # 近3場平均名次
    try:
        last3 = hist.groupby('horse_id').apply(lambda g: g.sort_values('race_date').tail(3)['finish_position'].mean()).reset_index(name='avg_rank_last3')
        race_df = race_df.merge(last3, on='horse_id', how='left')
        if 'avg_rank_last3' not in race_df.columns:
            race_df['avg_rank_last3'] = 99.0
        race_df['avg_rank_last3'] = race_df['avg_rank_last3'].fillna(99)
    except Exception as e:
        print(f"⚠️ 近3場平均名次計算失敗: {e}，設為 99")
        race_df['avg_rank_last3'] = 99.0
    
    # 同路程勝率
    try:
        def dist_win(g, dist):
            sub = g[g['distance']==dist]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['distance_win_rate'] = race_df.apply(lambda r: dist_win(hist[hist['horse_id']==r['horse_id']], r['distance']), axis=1)
    except Exception as e:
        print(f"⚠️ 同路程勝率計算失敗: {e}，設為 0")
        race_df['distance_win_rate'] = 0.0
    
    # 騎師+馬合作勝率
    try:
        def jh_win(g, j, h):
            sub = g[(g['jockey']==j) & (g['horse_id']==h)]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['jockey_horse_win_rate'] = race_df.apply(lambda r: jh_win(hist, r['jockey'], r['horse_id']), axis=1)
    except Exception as e:
        print(f"⚠️ 騎師+馬合作勝率計算失敗: {e}，設為 0")
        race_df['jockey_horse_win_rate'] = 0.0
    
    # 場地勝率
    try:
        def going_win(g, go):
            sub = g[g['going']==go]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['going_win_rate'] = race_df.apply(lambda r: going_win(hist[hist['horse_id']==r['horse_id']], r['going']), axis=1)
    except Exception as e:
        print(f"⚠️ 場地勝率計算失敗: {e}，設為 0")
        race_df['going_win_rate'] = 0.0
    
    # 檔位勝率
    try:
        def draw_win(g, dr):
            sub = g[g['draw']==dr]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['draw_win_rate'] = race_df.apply(lambda r: draw_win(hist[hist['horse_id']==r['horse_id']], r['draw']), axis=1)
    except Exception as e:
        print(f"⚠️ 檔位勝率計算失敗: {e}，設為 0")
        race_df['draw_win_rate'] = 0.0
    
    # 其他
    try:
        last_run = hist.groupby('horse_id')['race_date'].max().reset_index(name='last_date')
        race_df = race_df.merge(last_run, on='horse_id', how='left')
        race_df['days_since_last_run'] = (race_date - race_df['last_date']).dt.days.fillna(999)
    except Exception as e:
        print(f"⚠️ 出賽相隔日數計算失敗: {e}，設為 999")
        race_df['days_since_last_run'] = 999
    
    try:
        last_rtg = hist.groupby('horse_id').last()['rtg'].reset_index(name='last_rtg')
        race_df = race_df.merge(last_rtg, on='horse_id', how='left')
        race_df['rtg_change'] = (race_df['rtg'] - race_df['last_rtg']).fillna(0)
    except Exception as e:
        print(f"⚠️ 評分變化計算失敗: {e}，設為 0")
        race_df['rtg_change'] = 0
    
    try:
        race_df['races_last14days'] = race_df.apply(lambda r: len(hist[(hist['horse_id']==r['horse_id']) & (hist['race_date']>=race_date-pd.Timedelta(days=14))]), axis=1)
    except Exception as e:
        print(f"⚠️ 近14日出賽次數計算失敗: {e}，設為 0")
        race_df['races_last14days'] = 0
    
    for col in ['course_win_rate', 'course_avg_rank', 'weight_change', 'jockey_trainer_win_rate',
                'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
                'early_pace', 'finish_speed', 'last_trial_rank', 'last_trial_time',
                'jockey_win_rate_5', 'jockey_win_rate_10',
                'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
                'total_injuries', 'injury_severity']:
        if col not in race_df.columns:
            race_df[col] = 0
        else:
            race_df[col] = race_df[col].fillna(0)
    
    return race_df

# ============================================================
# 5. 主程式
# ============================================================
def main():
    print("📂 載入模型...")
    try:
        with open('hk_racing_model.pkl', 'rb') as f:
            xgb_obj = pickle.load(f)
            xgb_model = xgb_obj[0] if isinstance(xgb_obj, tuple) else xgb_obj
            print("⚠️ XGBoost 模型為 tuple，提取第一個元素" if isinstance(xgb_obj, tuple) else "")
        
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        
        with open('hk_ranking_model.pkl', 'rb') as f:
            rank_obj = pickle.load(f)
            rank_model = rank_obj[0] if isinstance(rank_obj, tuple) else rank_obj
            print("⚠️ 排名模型為 tuple，提取第一個元素" if isinstance(rank_obj, tuple) else "")
        
        print("✅ 所有模型載入成功")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return

    # ---- 讀取排位表 ----
    print("📂 讀取排位表...")
    df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv')
    print(f"📊 共 {len(df)} 筆記錄")

    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df = standardize_columns(df)
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df = ensure_series(df)

    # ---- 日期處理 ----
    if 'race_date' not in df.columns:
        print("❌ 找不到日期欄位")
        return
    df['race_date'] = df['race_date'].astype(str).str.extract(r'(\d{8})')[0]
    df['race_date'] = pd.to_datetime(df['race_date'], format='%Y%m%d', errors='coerce')
    df = df.dropna(subset=['race_date'])
    if df.empty:
        print("❌ 無有效日期")
        return

    # ---- 場次處理 ----
    if 'race_no' not in df.columns:
        print("❌ 缺少 'race_no' 欄位")
        return
    df['race_no'] = df['race_no'].astype(str).str.extract(r'(\d+)')[0]
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce')
    df = df.dropna(subset=['race_no'])
    if df.empty:
        print("❌ 無有效場次")
        return

    # ---- 選取最近一場第9場，若無則最後一場 ----
    latest_date = df['race_date'].max()
    if pd.isna(latest_date):
        print("❌ 無法找到有效日期")
        return
    race_sel = df[(df['race_date'] == latest_date) & (df['race_no'] == 9)]
    if race_sel.empty:
        max_race = df[df['race_date'] == latest_date]['race_no'].max()
        race_sel = df[(df['race_date'] == latest_date) & (df['race_no'] == max_race)]
    if race_sel.empty:
        print("❌ 無法選取場次")
        return
    print(f"✅ 選取 {latest_date.strftime('%Y-%m-%d')} 第 {race_sel['race_no'].iloc[0]} 場，共 {len(race_sel)} 匹")

    # ---- 載入歷史數據 ----
    print("📂 載入歷史數據...")
    history = pd.read_csv('ALL_DATA_MERGED.csv')
    print(f"✅ 歷史數據 {len(history)} 筆")
    if history.columns.duplicated().any():
        history = history.loc[:, ~history.columns.duplicated(keep='first')]
    history = standardize_columns(history)
    if history.columns.duplicated().any():
        history = history.loc[:, ~history.columns.duplicated(keep='first')]
    history = ensure_series(history)
    history = ensure_finish_position(history, "歷史數據")
    history['race_date'] = pd.to_datetime(history['race_date'], errors='coerce')
    history = history.dropna(subset=['race_date'])

    # ---- 生成特徵 ----
    print("🧮 生成特徵...")
    race_sel = get_latest_features(race_sel, history)
    race_sel = compute_stats(race_sel, history, latest_date)

    # ---- 賠率處理（已修正） ----
    if 'win_odds' not in race_sel.columns:
        race_sel['win_odds'] = 4.0
    else:
        # 將 0 或 NaN 都換成 4.0
        race_sel['win_odds'] = race_sel['win_odds'].replace(0, 4.0)
        race_sel['win_odds'] = race_sel['win_odds'].fillna(4.0)
    # 確保 win_odds 係數值型
    race_sel['win_odds'] = pd.to_numeric(race_sel['win_odds'], errors='coerce').fillna(4.0)

    race_sel['odds_rank_in_race'] = race_sel['win_odds'].rank(ascending=True)

    # ---- 確保所有特徵存在 ----
    for f in FEATURES_EN:
        if f not in race_sel.columns:
            race_sel[f] = 0
        else:
            race_sel[f] = race_sel[f].fillna(0)

    # 提取特徵矩陣（英文名）
    X = race_sel[FEATURES_EN].copy()
    print(f"✅ X 形狀: {X.shape}")

    # 強制轉數值
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

    # ---------- 關鍵：將 X 嘅欄位名轉為模型期望嘅名稱 ----------
    X.rename(columns=NAME_MAPPING, inplace=True)
    for col in EXPECTED_FEATURES:
        if col not in X.columns:
            X[col] = 0
    X = X[EXPECTED_FEATURES]
    print("✅ 特徵名稱已映射為模型期望格式")
    # ---------------------------------------------------------

    # ---- 預測 ----
    prob_xgb = xgb_model.predict_proba(X)[:, 1]
    prob_cat = cat_model.predict_proba(X)[:, 1]
    ensemble_weight = 25
    prob_final = (prob_xgb * ensemble_weight + prob_cat) / (ensemble_weight + 1)
    rank_score = rank_model.predict(X)

    # ---- 輸出 ----
    result = race_sel[['horse_id', 'draw', 'win_odds']].copy()
    result.rename(columns={'horse_id': '馬匹編號'}, inplace=True)
    result['預測勝率'] = prob_final
    result['排名分數'] = rank_score
    result['值博指數'] = result['預測勝率'] / result['win_odds']
    result = result.sort_values('值博指數', ascending=False)

    print("\n" + "="*60)
    print(f"🏇 {latest_date.strftime('%Y-%m-%d')} 第 {race_sel['race_no'].iloc[0]} 場 預測 TOP 5")
    print("="*60)
    for i, row in result.head(5).iterrows():
        print(f"{row['馬匹編號']} (檔位 {row['draw']})  勝率 {row['預測勝率']:.2%}  值博指數 {row['值博指數']:.3f}")
    print("="*60)

    result.to_csv('prediction_result.csv', index=False)
    print("💾 結果已儲存至 prediction_result.csv")

if __name__ == '__main__':
    main()