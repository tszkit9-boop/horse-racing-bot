#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - Streamlit 網頁版（美化主題版）
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier

# ============================================================
# 1. 設定頁面 + 自訂 CSS
# ============================================================
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. 自訂 CSS 主題（賽馬風格）
# ============================================================
st.markdown("""
<style>
    /* 全局字體 */
    body, .stApp {
        font-family: 'Segoe UI', 'PingFang HK', sans-serif;
        background: #f5f0eb;
    }
    
    /* 標題區塊 */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 30px 40px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        color: white;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .main-header h1 {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 2px;
        text-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.85;
        margin-top: 8px;
        letter-spacing: 4px;
    }
    .main-header .horse-icon {
        position: absolute;
        right: 40px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 4.5rem;
        opacity: 0.25;
    }
    
    /* 控制面板 */
    .sidebar-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0f3460;
        border-bottom: 3px solid #e6b800;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }
    .sidebar-label {
        font-weight: 600;
        color: #1a1a2e;
        margin-top: 10px;
    }
    
    /* 卡片風格 */
    .card {
        background: white;
        padding: 25px 30px;
        border-radius: 16px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border-left: 5px solid #e6b800;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 32px rgba(0,0,0,0.12);
    }
    .card-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #0f3460;
        margin-bottom: 8px;
    }
    .card-sub {
        color: #6c757d;
        font-size: 0.95rem;
    }
    
    /* 結果表格 */
    .result-table {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 6px 24px rgba(0,0,0,0.08);
    }
    .result-table th {
        background: #0f3460;
        color: white;
        font-weight: 600;
        padding: 12px 16px;
    }
    .result-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #f0ebe6;
    }
    .result-table tr:last-child td {
        border-bottom: none;
    }
    .result-table tr:hover {
        background: #f8f4f0;
    }
    
    /* 排名徽章 */
    .badge-1 {
        background: #e6b800;
        color: #1a1a2e;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 30px;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-2 {
        background: #c0c0c0;
        color: #1a1a2e;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 30px;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-3 {
        background: #cd7f32;
        color: white;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 30px;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-other {
        background: #e9ecef;
        color: #495057;
        padding: 4px 14px;
        border-radius: 30px;
        font-size: 0.9rem;
        display: inline-block;
    }
    
    /* 彩池推薦 */
    .pool-box {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 20px 25px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 0.9rem;
        border: 1px solid #e9ecef;
        max-height: 450px;
        overflow-y: auto;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    
    /* 底部 */
    .footer {
        text-align: center;
        padding: 20px 0 10px;
        border-top: 1px solid #ddd;
        color: #999;
        font-size: 0.85rem;
        margin-top: 30px;
    }
    
    /* 響應式 */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.8rem;
        }
        .main-header .horse-icon {
            display: none;
        }
        .card {
            padding: 15px 18px;
        }
    }
    
    /* Streamlit 自訂 */
    .stButton > button {
        background: linear-gradient(135deg, #0f3460, #1a1a2e);
        color: white;
        border: none;
        border-radius: 30px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s;
        box-shadow: 0 4px 16px rgba(15, 52, 96, 0.3);
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(15, 52, 96, 0.4);
        background: linear-gradient(135deg, #1a1a2e, #0f3460);
    }
    .stButton > button:active {
        transform: translateY(0px);
    }
    .stSelectbox > div > div {
        border-radius: 30px;
    }
    .stDateInput > div > div {
        border-radius: 30px;
    }
    
    /* 成功訊息 */
    .stAlert {
        border-radius: 16px;
        border-left: 6px solid #28a745;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .stError {
        border-radius: 16px;
        border-left: 6px solid #dc3545;
    }
    
    /* 今日賽程標籤 */
    .schedule-tag {
        background: #e9ecef;
        padding: 6px 14px;
        border-radius: 30px;
        display: inline-block;
        margin: 4px 6px 4px 0;
        font-size: 0.9rem;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. 標題 Header
# ============================================================
st.markdown(f"""
<div class="main-header">
    <div class="horse-icon">🐎</div>
    <h1>🏇 賽馬預測系統</h1>
    <p>AI 驅動 · 即時預測 · 彩池推薦</p>
    <p style="font-size:0.85rem; opacity:0.6; margin-top:10px;">📊 36 個特徵 · 三模型融合 · {datetime.now().strftime('%Y年%m月%d日')}</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 4. 載入模型（cache）
# ============================================================
@st.cache_resource
def load_models():
    try:
        with open('hk_racing_model.pkl', 'rb') as f:
            xgb_obj = pickle.load(f)
            xgb_model = xgb_obj[0] if isinstance(xgb_obj, tuple) else xgb_obj
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        with open('hk_ranking_model.pkl', 'rb') as f:
            rank_obj = pickle.load(f)
            rank_model = rank_obj[0] if isinstance(rank_obj, tuple) else rank_obj
        return xgb_model, cat_model, rank_model
    except Exception as e:
        st.error(f"❌ 模型載入失敗：{e}")
        return None, None, None

# ============================================================
# 5. 完整特徵工程
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

def standardize_columns(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '比賽日期': 'race_date', '場次': 'race_no',
        '馬場': 'race_course', '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        'Position': 'finish_position', 'Rank': 'finish_position',
        'pos': 'finish_position', '排名': 'finish_position',
        '馬名': 'horse_name'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    return df

def ensure_series(df):
    for col in df.columns:
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    return df

def get_finish_column(df):
    candidates = ['finish_position', '名次', 'Position', 'pos', 'Rank', 'rank', '最終名次']
    for col in candidates:
        if col in df.columns:
            return col
    return None

def safe_parse_dates(df, date_col):
    if date_col not in df.columns:
        return pd.Series([pd.NaT] * len(df))
    dates = df[date_col].astype(str).str.strip()
    dates = dates.str.replace('/', '-')
    return pd.to_datetime(dates, errors='coerce')

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
        raise KeyError("歷史數據缺少 finish_position")
    hist['finish_position'] = pd.to_numeric(hist['finish_position'], errors='coerce')
    try:
        jockey_stats = hist.groupby('jockey').apply(lambda g: (g['finish_position']==1).sum()/max(len(g),1)).reset_index(name='jockey_win_rate_50')
        race_df = race_df.merge(jockey_stats, on='jockey', how='left')
        race_df['jockey_win_rate_50'] = race_df['jockey_win_rate_50'].fillna(0)
    except:
        race_df['jockey_win_rate_50'] = 0.0
    try:
        trainer_stats = hist.groupby('trainer').apply(lambda g: (g['finish_position']==1).sum()/max(len(g),1)).reset_index(name='trainer_win_rate_50')
        race_df = race_df.merge(trainer_stats, on='trainer', how='left')
        race_df['trainer_win_rate_50'] = race_df['trainer_win_rate_50'].fillna(0)
    except:
        race_df['trainer_win_rate_50'] = 0.0
    try:
        last3 = hist.groupby('horse_id').apply(lambda g: g.sort_values('race_date').tail(3)['finish_position'].mean()).reset_index(name='avg_rank_last3')
        race_df = race_df.merge(last3, on='horse_id', how='left')
        race_df['avg_rank_last3'] = race_df['avg_rank_last3'].fillna(99)
    except:
        race_df['avg_rank_last3'] = 99.0
    try:
        def dist_win(g, dist):
            sub = g[g['distance']==dist]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['distance_win_rate'] = race_df.apply(lambda r: dist_win(hist[hist['horse_id']==r['horse_id']], r['distance']), axis=1)
    except:
        race_df['distance_win_rate'] = 0.0
    try:
        def jh_win(g, j, h):
            sub = g[(g['jockey']==j) & (g['horse_id']==h)]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['jockey_horse_win_rate'] = race_df.apply(lambda r: jh_win(hist, r['jockey'], r['horse_id']), axis=1)
    except:
        race_df['jockey_horse_win_rate'] = 0.0
    try:
        def going_win(g, go):
            sub = g[g['going']==go]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['going_win_rate'] = race_df.apply(lambda r: going_win(hist[hist['horse_id']==r['horse_id']], r['going']), axis=1)
    except:
        race_df['going_win_rate'] = 0.0
    try:
        def draw_win(g, dr):
            sub = g[g['draw']==dr]
            return 0.0 if len(sub)==0 else (sub['finish_position']==1).sum()/len(sub)
        race_df['draw_win_rate'] = race_df.apply(lambda r: draw_win(hist[hist['horse_id']==r['horse_id']], r['draw']), axis=1)
    except:
        race_df['draw_win_rate'] = 0.0
    try:
        last_run = hist.groupby('horse_id')['race_date'].max().reset_index(name='last_date')
        race_df = race_df.merge(last_run, on='horse_id', how='left')
        race_df['days_since_last_run'] = (race_date - race_df['last_date']).dt.days.fillna(999)
    except:
        race_df['days_since_last_run'] = 999
    try:
        last_rtg = hist.groupby('horse_id').last()['rtg'].reset_index(name='last_rtg')
        race_df = race_df.merge(last_rtg, on='horse_id', how='left')
        race_df['rtg_change'] = (race_df['rtg'] - race_df['last_rtg']).fillna(0)
    except:
        race_df['rtg_change'] = 0
    try:
        race_df['races_last14days'] = race_df.apply(lambda r: len(hist[(hist['horse_id']==r['horse_id']) & (hist['race_date']>=race_date-pd.Timedelta(days=14))]), axis=1)
    except:
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
# 6. 中文馬名對照
# ============================================================
@st.cache_data
def load_horse_name_map():
    try:
        df_map = pd.read_csv('horse_name_mapping.csv', encoding='utf-8-sig')
        if 'horse_id' in df_map.columns and '馬名' in df_map.columns:
            return dict(zip(df_map['horse_id'], df_map['馬名']))
    except:
        pass
    return {}

# ============================================================
# 7. 彩池推薦
# ============================================================
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
# 8. 預測主函數
# ============================================================
def run_prediction(date_str, race_no):
    xgb_model, cat_model, rank_model = load_models()
    if xgb_model is None:
        st.error("模型載入失敗")
        return None, None

    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    except Exception as e:
        st.error(f"讀取排位表失敗：{e}")
        return None, None

    df = standardize_columns(df)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df = ensure_series(df)

    if 'race_date' not in df.columns:
        st.error("找不到日期欄位")
        return None, None
    df['race_date'] = safe_parse_dates(df, 'race_date')
    df = df.dropna(subset=['race_date'])
    if df.empty:
        st.error("無有效日期")
        return None, None

    if 'race_no' not in df.columns:
        st.error("找不到場次欄位")
        return None, None
    df['race_no'] = df['race_no'].astype(str).str.extract(r'(\d+)')[0]
    df['race_no'] = pd.to_numeric(df['race_no'], errors='coerce')
    df = df.dropna(subset=['race_no'])
    if df.empty:
        st.error("無有效場次")
        return None, None

    target = pd.to_datetime(date_str)
    race_sel = df[(df['race_date'].dt.date == target.date()) & (df['race_no'] == race_no)]
    if race_sel.empty:
        st.error(f"日期 {date_str} 第 {race_no} 場無數據")
        return None, None

    try:
        history = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
    except:
        st.error("缺少歷史數據檔案 ALL_DATA_MERGED.csv")
        return None, None

    history = standardize_columns(history)
    history = history.loc[:, ~history.columns.duplicated(keep='first')]
    history = ensure_series(history)
    if 'race_date' not in history.columns:
        if '比賽日期' in history.columns:
            history.rename(columns={'比賽日期': 'race_date'}, inplace=True)
        else:
            st.error("歷史數據缺少日期欄位")
            return None, None
    history['race_date'] = pd.to_datetime(history['race_date'], errors='coerce')
    history = history.dropna(subset=['race_date'])

    finish_col = get_finish_column(history)
    if finish_col is None:
        st.error("歷史數據缺少名次欄位")
        return None, None
    history.rename(columns={finish_col: 'finish_position'}, inplace=True)

    name_map = load_horse_name_map()

    race_sel = get_latest_features(race_sel, history)
    race_sel = compute_stats(race_sel, history, target)
    race_sel['中文名'] = race_sel['horse_id'].map(name_map).fillna(race_sel['horse_id'])

    if 'win_odds' not in race_sel.columns:
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

    prob_xgb = xgb_model.predict_proba(X)[:, 1]
    prob_cat = cat_model.predict_proba(X)[:, 1]
    prob_final = (prob_xgb * 25 + prob_cat) / 26
    rank_score = rank_model.predict(X)

    result = race_sel[['中文名', 'draw', 'win_odds']].copy()
    result.rename(columns={'中文名': '馬匹名稱', 'draw': '檔位', 'win_odds': '賠率'}, inplace=True)
    result['預測勝率'] = prob_final
    result['值博指數'] = result['預測勝率'] / result['賠率']
    result = result.sort_values('值博指數', ascending=False)

    pool_rec = generate_pool_recommendations(result)
    return result, pool_rec

# ============================================================
# 9. 側邊欄
# ============================================================
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎯 控制面板</div>', unsafe_allow_html=True)
    
    date = st.date_input(
        "📅 選擇日期",
        value=pd.to_datetime("2025-04-09"),
        help="選擇你想預測嘅賽馬日期"
    )
    
    race_no = st.selectbox(
        "🏇 選擇場次",
        list(range(1, 12)),
        index=8,
        help="選擇你想預測嘅場次號碼"
    )
    
    predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)

# ============================================================
# 10. 今日賽程
# ============================================================
st.markdown('<div class="card"><div class="card-title">📅 今日賽程</div>', unsafe_allow_html=True)
try:
    df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    df_sched = standardize_columns(df_sched)
    if 'race_date' in df_sched.columns:
        df_sched['race_date'] = safe_parse_dates(df_sched, 'race_date')
        df_sched = df_sched.dropna(subset=['race_date'])
        today = datetime.now().date()
        day_races = df_sched[df_sched['race_date'].dt.date == today]
        if day_races.empty:
            st.info("🏟️ 今日沒有賽事")
        else:
            st.write("🏟️ 今日賽事：")
            for course in day_races['race_course'].unique():
                races = day_races[day_races['race_course'] == course]['race_no'].unique()
                race_tags = ''.join([f'<span class="schedule-tag">第{r}場</span>' for r in sorted(races)])
                st.markdown(f"**{course}** &nbsp; {race_tags}", unsafe_allow_html=True)
    else:
        st.info("🏟️ 今日沒有賽事")
except Exception:
    st.info("🏟️ 今日沒有賽事")
st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# 11. 執行預測
# ============================================================
if predict_btn:
    date_str = date.strftime('%Y-%m-%d')
    with st.spinner(f"⏳ 執行預測 {date_str} 第 {race_no} 場..."):
        try:
            result, pool = run_prediction(date_str, race_no)
            if result is not None:
                st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
                
                # TOP 5 卡片
                st.markdown('<div class="card"><div class="card-title">🏇 預測 TOP 5</div>', unsafe_allow_html=True)
                
                display_df = result.head(5)[['馬匹名稱', '檔位', '預測勝率', '值博指數']].copy()
                display_df['預測勝率'] = display_df['預測勝率'].apply(lambda x: f"{x:.2%}")
                display_df['值博指數'] = display_df['值博指數'].apply(lambda x: f"{x:.4f}")
                
                # 重新命名為中文
                display_df.columns = ['馬匹名稱', '檔位', '預測勝率', '值博指數']
                
                # 加入排名徽章
                def format_rank(idx):
                    if idx == 0:
                        return '<span class="badge-1">🏆 1</span>'
                    elif idx == 1:
                        return '<span class="badge-2">🥈 2</span>'
                    elif idx == 2:
                        return '<span class="badge-3">🥉 3</span>'
                    else:
                        return f'<span class="badge-other">{idx+1}</span>'
                
                # 顯示美化表格
                for idx, row in display_df.iterrows():
                    rank_badge = format_rank(idx)
                    col1, col2, col3, col4, col5 = st.columns([1, 3, 1.5, 2, 2])
                    with col1:
                        st.markdown(rank_badge, unsafe_allow_html=True)
                    with col2:
                        st.write(f"**{row['馬匹名稱']}**")
                    with col3:
                        st.write(f"檔位 {row['檔位']}")
                    with col4:
                        st.write(f"勝率 {row['預測勝率']}")
                    with col5:
                        st.write(f"值博指數 {row['值博指數']}")
                    st.divider()
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 彩池推薦卡片
                st.markdown('<div class="card"><div class="card-title">🎯 彩池推薦</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pool-box">{pool}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"❌ 預測過程中發生錯誤")
            st.code(f"錯誤類型：{type(e).__name__}\n錯誤訊息：{str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ============================================================
# 12. 底部
# ============================================================
st.markdown("""
<div class="footer">
    🕐 最後更新：""" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """ &nbsp;|&nbsp; 
    🔐 數據來源：HKJC &nbsp;|&nbsp; 
    ⚡ 系統版本：v5.0-美化版
</div>
""", unsafe_allow_html=True)
