#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
predict_race_card.py - 完整版（中文輸出 + 彩池推薦 + 歷史記錄）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
import pandas as pd
import numpy as np
import pickle
import os
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier

# ============================================================
# 參數
# ============================================================
parser = argparse.ArgumentParser()
parser.add_argument('--date', type=str, help='日期 YYYY-MM-DD')
parser.add_argument('--race', type=int, default=9, help='場次，預設 9')
args = parser.parse_args()

target_date = args.date
target_race_no = args.race

if target_date:
    print(f"[INFO] 指定日期：{target_date}")
else:
    print("[INFO] 自動選取最新日期")
print(f"[INFO] 指定場次：第 {target_race_no} 場")

# ============================================================
# 特徵定義
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

NAME_MAPPING = {
    'act_wt': 'weight', 'rtg': 'Rtg.',
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

# ============================================================
# 輔助函數
# ============================================================
def standardize_columns_light(df, is_history=False):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id', 'Horse': 'horse_id',
        '場次': 'race_no',
        '馬場': 'race_course', '實際負磅': 'act_wt',
        '名次': 'finish_position',
        '馬名': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    if '比賽日期' in df.columns and 'race_date' not in df.columns:
        df['race_date'] = df['比賽日期']
    return df

def ensure_series(df):
    for col in df.columns:
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    return df

def get_latest_features(race_df, history_df):
    # 確保 history 有 horse_id
    if 'horse_id' not in history_df.columns:
        for col in history_df.columns:
            col_low = col.lower()
            if 'horse' in col_low or '馬匹' in col or '馬號' in col or 'id' in col_low:
                history_df.rename(columns={col: 'horse_id'}, inplace=True)
                break
    if 'horse_id' not in history_df.columns:
        raise KeyError("歷史數據缺少 horse_id 欄位")

    # 確保 history 有 race_date
    if 'race_date' not in history_df.columns:
        for col in history_df.columns:
            if 'date' in col.lower() or '日期' in col:
                history_df.rename(columns={col: 'race_date'}, inplace=True)
                break
    if 'race_date' not in history_df.columns:
        raise KeyError("歷史數據缺少 race_date 欄位")

    # 確保 history 有 finish_position
    if 'finish_position' not in history_df.columns:
        for col in history_df.columns:
            if '名次' in col or 'position' in col.lower() or 'rank' in col.lower():
                history_df.rename(columns={col: 'finish_position'}, inplace=True)
                break

    history_df['race_date'] = pd.to_datetime(history_df['race_date'], errors='coerce')
    history_df = history_df.dropna(subset=['race_date'])

    # 統一 horse_id 類型為字串，避免 merge 錯誤
    history_df['horse_id'] = history_df['horse_id'].astype(str)
    race_df['horse_id'] = race_df['horse_id'].astype(str)

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
    if 'finish_position' not in history_df.columns:
        for col in history_df.columns:
            if '名次' in col or 'position' in col.lower() or 'rank' in col.lower():
                history_df.rename(columns={col: 'finish_position'}, inplace=True)
                break
    if 'finish_position' not in history_df.columns:
        print("[WARN] 歷史數據無名次欄位，用0填充")
        for col in ['jockey_win_rate_50', 'trainer_win_rate_50', 'avg_rank_last3']:
            race_df[col] = 0.0
        return race_df

    history_df['race_date'] = pd.to_datetime(history_df['race_date'], errors='coerce')
    hist = history_df[history_df['race_date'] < race_date].copy()
    if hist.empty:
        for col in ['jockey_win_rate_50', 'trainer_win_rate_50', 'avg_rank_last3']:
            race_df[col] = 0.0
        return race_df

    hist['finish_position'] = pd.to_numeric(hist['finish_position'], errors='coerce')

    try:
        jockey_stats = hist.groupby('jockey').apply(
            lambda g: (g['finish_position'] == 1).sum() / max(len(g), 1)
        ).reset_index(name='jockey_win_rate_50')
        race_df = race_df.merge(jockey_stats, on='jockey', how='left')
        race_df['jockey_win_rate_50'] = race_df['jockey_win_rate_50'].fillna(0)
    except:
        race_df['jockey_win_rate_50'] = 0.0

    try:
        trainer_stats = hist.groupby('trainer').apply(
            lambda g: (g['finish_position'] == 1).sum() / max(len(g), 1)
        ).reset_index(name='trainer_win_rate_50')
        race_df = race_df.merge(trainer_stats, on='trainer', how='left')
        race_df['trainer_win_rate_50'] = race_df['trainer_win_rate_50'].fillna(0)
    except:
        race_df['trainer_win_rate_50'] = 0.0

    try:
        last3 = hist.groupby('horse_id').apply(
            lambda g: g.sort_values('race_date').tail(3)['finish_position'].mean()
        ).reset_index(name='avg_rank_last3')
        race_df = race_df.merge(last3, on='horse_id', how='left')
        race_df['avg_rank_last3'] = race_df['avg_rank_last3'].fillna(99)
    except:
        race_df['avg_rank_last3'] = 99.0

    for col in ['distance_win_rate', 'jockey_horse_win_rate', 'going_win_rate', 'draw_win_rate']:
        race_df[col] = 0.0

    for col in ['course_win_rate', 'course_avg_rank', 'weight_change', 'jockey_trainer_win_rate',
                'trial_win_rate', 'sire_win_rate', 'sire_course_win_rate',
                'early_pace', 'finish_speed', 'last_trial_rank', 'last_trial_time',
                'jockey_win_rate_5', 'jockey_win_rate_10',
                'days_since_injury', 'injury_30d', 'injury_60d', 'injury_90d',
                'total_injuries', 'injury_severity']:
        race_df[col] = 0

    return race_df

def build_horse_name_map():
    name_map = {}
    try:
        df_map = pd.read_csv('horse_name_mapping.csv', encoding='utf-8-sig')
        if 'horse_id' in df_map.columns and '馬名' in df_map.columns:
            name_map = dict(zip(df_map['horse_id'], df_map['馬名']))
            print(f"[INFO] 載入 {len(name_map)} 個中文馬名")
    except:
        print("[WARN] 無中文名對照")
    return name_map

def generate_pool_recommendations(df, top_n=6):
    top_horses = df.head(top_n)
    horse_names = top_horses['馬匹名稱'].tolist()
    probs = top_horses['預測勝率'].tolist()

    def combo_score(indices):
        score = 1.0
        for i in indices:
            score *= probs[i]
        return score / len(indices)

    rec = "【獨贏】\n"
    for i, row in top_horses.head(3).iterrows():
        rec += f"  {row['馬匹名稱']} (勝率 {row['預測勝率']:.2%})\n"

    rec += "\n【位置】\n"
    for i, row in top_horses.head(4).iterrows():
        rec += f"  {row['馬匹名稱']} (勝率 {row['預測勝率']:.2%})\n"

    rec += "\n【連贏】\n"
    pairs = []
    for i in range(min(len(horse_names), 5)):
        for j in range(i+1, min(len(horse_names), 6)):
            pairs.append((combo_score([i, j]), i, j))
    pairs.sort(reverse=True)
    for _, i, j in pairs[:5]:
        rec += f"  {horse_names[i]} + {horse_names[j]}\n"

    rec += "\n【位置Q】\n"
    q_pairs = []
    for i in range(min(len(horse_names), 6)):
        for j in range(i+1, min(len(horse_names), 8)):
            if j < len(horse_names):
                q_pairs.append((combo_score([i, j]), i, j))
    q_pairs.sort(reverse=True)
    for _, i, j in q_pairs[:6]:
        rec += f"  {horse_names[i]} + {horse_names[j]}\n"

    rec += "\n【三重彩】\n"
    tierce = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                if i != j and i != k and j != k:
                    tierce.append((combo_score([i, j, k]), i, j, k))
    tierce.sort(reverse=True)
    for _, i, j, k in tierce[:5]:
        rec += f"  {horse_names[i]} > {horse_names[j]} > {horse_names[k]}\n"

    rec += "\n【四重彩】\n"
    quartet = []
    for i in range(min(len(horse_names), 4)):
        for j in range(min(len(horse_names), 5)):
            for k in range(min(len(horse_names), 6)):
                for l in range(min(len(horse_names), 7)):
                    if len(set([i, j, k, l])) == 4:
                        quartet.append((combo_score([i, j, k, l]), i, j, k, l))
    quartet.sort(reverse=True)
    for _, i, j, k, l in quartet[:3]:
        rec += f"  {horse_names[i]} > {horse_names[j]} > {horse_names[k]} > {horse_names[l]}\n"

    return rec

# ============================================================
# 主程式
# ============================================================
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 建立歷史記錄資料夾
    history_folder = 'prediction_history'
    os.makedirs(history_folder, exist_ok=True)

    print("[INFO] 載入模型中...")
    try:
        with open('hk_racing_model.pkl', 'rb') as f:
            xgb_obj = pickle.load(f)
            xgb_model = xgb_obj[0] if isinstance(xgb_obj, tuple) else xgb_obj
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        with open('hk_ranking_model.pkl', 'rb') as f:
            rank_obj = pickle.load(f)
            rank_model = rank_obj[0] if isinstance(rank_obj, tuple) else rank_obj
        print("[OK] 所有模型載入成功")
    except Exception as e:
        print(f"[ERROR] 模型載入失敗: {e}")
        sys.exit(1)

    print("[INFO] 讀取排位表...")
    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        print(f"[DATA] 共 {len(df)} 筆記錄")
    except Exception as e:
        print(f"[ERROR] 讀取失敗: {e}")
        sys.exit(1)

    df = standardize_columns_light(df, is_history=False)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df = ensure_series(df)

    required = ['horse_id', 'race_no', 'draw', 'act_wt']
    for col in required:
        if col not in df.columns:
            print(f"[ERROR] 缺少欄位：{col}")
            print(f"[DEBUG] 現有欄位：{df.columns.tolist()}")
            sys.exit(1)

    if 'race_date' in df.columns:
        date_col = 'race_date'
    elif '比賽日期' in df.columns:
        date_col = '比賽日期'
    else:
        print("[ERROR] 找不到日期欄位")
        sys.exit(1)
    print(f"[INFO] 使用日期欄位：'{date_col}'")

    print("[INFO] 處理日期...")
    df[date_col] = df[date_col].astype(str).str.strip()
    if date_col == '比賽日期':
        df[date_col] = df[date_col].str.extract(r'(\d{8})')[0]
        df[date_col] = pd.to_datetime(df[date_col], format='%Y%m%d', errors='coerce')
    else:
        df[date_col] = df[date_col].str.replace('/', '-')
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    valid_dates = df[date_col].notna().sum()
    if valid_dates == 0:
        print("[ERROR] 無法解析任何日期")
        sys.exit(1)
    df = df.dropna(subset=[date_col])
    print(f"[OK] {valid_dates} 個有效日期")

    print("[INFO] 處理場次...")
    df['race_no'] = df['race_no'].astype(str).str.extract(r'(\d+)')[0]
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce')
    df = df.dropna(subset=['race_no'])

    if target_date:
        selected = pd.to_datetime(target_date)
        if selected not in df[date_col].values:
            print(f"[ERROR] 日期 {target_date} 無數據")
            print("[DEBUG] 可用日期：", sorted(df[date_col].unique()))
            sys.exit(1)
        latest_date = selected
    else:
        latest_date = df[date_col].max()
    if pd.isna(latest_date):
        print("[ERROR] 無有效日期")
        sys.exit(1)

    race_sel = df[(df[date_col] == latest_date) & (df['race_no'] == target_race_no)]
    if race_sel.empty:
        print(f"[ERROR] 日期 {latest_date.strftime('%Y-%m-%d')} 第 {target_race_no} 場無數據")
        print("[DEBUG] 該日可用場次：", sorted(df[df[date_col] == latest_date]['race_no'].unique()))
        sys.exit(1)

    display_date = latest_date.strftime('%Y-%m-%d')
    display_race = int(race_sel['race_no'].iloc[0])
    print(f"[OK] 選取 {display_date} 第 {display_race} 場，共 {len(race_sel)} 匹")

    print("[INFO] 載入歷史數據...")
    try:
        history = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
        print(f"[DATA] 歷史數據 {len(history)} 筆")
    except Exception as e:
        print(f"[ERROR] 載入歷史數據失敗: {e}")
        sys.exit(1)

    history = standardize_columns_light(history, is_history=True)
    history = history.loc[:, ~history.columns.duplicated(keep='first')]
    history = ensure_series(history)

    if '比賽日期' in history.columns and 'race_date' not in history.columns:
        history['race_date'] = history['比賽日期']

    horse_name_map = build_horse_name_map()

    print("[INFO] 生成特徵...")
    race_sel = get_latest_features(race_sel, history)
    race_sel = compute_stats(race_sel, history, latest_date)
    race_sel['中文名'] = race_sel['horse_id'].map(horse_name_map).fillna(race_sel['horse_id'])

    if 'win_odds' not in race_sel.columns:
        print("[WARN] 無賠率，使用預設 4.0")
        race_sel['win_odds'] = 4.0
    else:
        race_sel['win_odds'] = race_sel['win_odds'].replace(0, 4.0).fillna(4.0)
    race_sel['win_odds'] = pd.to_numeric(race_sel['win_odds'], errors='coerce').fillna(4.0)
    race_sel['odds_rank_in_race'] = race_sel['win_odds'].rank(ascending=True)

    for f in FEATURES_EN:
        if f not in race_sel.columns:
            race_sel[f] = 0
        else:
            race_sel[f] = race_sel[f].fillna(0)

    X = race_sel[FEATURES_EN].copy()
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

    X.rename(columns=NAME_MAPPING, inplace=True)
    for col in EXPECTED_FEATURES:
        if col not in X.columns:
            X[col] = 0
    X = X[EXPECTED_FEATURES]

    print("[INFO] 執行預測...")
    prob_xgb = xgb_model.predict_proba(X)[:, 1]
    prob_cat = cat_model.predict_proba(X)[:, 1]
    prob_final = (prob_xgb * 25 + prob_cat) / 26
    rank_score = rank_model.predict(X)

    # ===== 輸出結果 =====
    result = race_sel[['中文名', 'draw', 'win_odds']].copy()
    result.rename(columns={'中文名': '馬匹名稱', 'draw': '檔位', 'win_odds': '賠率'}, inplace=True)
    result['比賽日期'] = display_date
    result['場次'] = display_race
    result['預測勝率'] = prob_final
    result['排名分數'] = rank_score
    result['值博指數'] = result['預測勝率'] / result['賠率']
    result = result.sort_values('值博指數', ascending=False)

    # ✅ 儲存最新結果（覆蓋）
    result.to_csv('prediction_result.csv', index=False)
    print("[OK] 預測完成，結果已儲存至 prediction_result.csv")

    # ✅ 儲存歷史記錄（連日期時間）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    history_file = os.path.join(history_folder, f'prediction_{display_date}_場次{display_race}_{timestamp}.csv')
    result.to_csv(history_file, index=False)
    print(f"[OK] 歷史記錄已儲存至 {history_file}")

    # ===== 顯示結果 =====
    print("\n" + "="*50)
    print(f"🏇 {display_date} 第 {display_race} 場 預測 TOP 5")
    print("="*50)
    for _, row in result.head(5).iterrows():
        print(f"{row['馬匹名稱']} (檔位 {row['檔位']})  勝率 {row['預測勝率']:.2%}  值博指數 {row['值博指數']:.3f}")
    print("="*50)

    # ===== 彩池推薦 =====
    print("\n" + "="*50)
    print("🎯 彩池推薦")
    print("="*50)
    pool_rec = generate_pool_recommendations(result)
    print(pool_rec)
    print("="*50)

    with open('pool_recommendations.txt', 'w', encoding='utf-8') as f:
        f.write(f"🏇 {display_date} 第 {display_race} 場\n")
        f.write(pool_rec)
    print("[OK] 彩池推薦已儲存至 pool_recommendations.txt")

if __name__ == '__main__':
    main()