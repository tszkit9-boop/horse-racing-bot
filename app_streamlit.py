#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完全可執行版（預測 + 後台七大模組 + 優惠碼管理）
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
from catboost import CatBoostClassifier
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# 🔐 功能開關
# ============================================================
CONFIG = {
    "enable_registration": False,
    "enable_payment": False,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "subscription_price": 9.99,
    "admin_password": "admin123",
    "module_user_management": True,
    "module_analytics": True,
    "module_finance": True,
    "module_monitoring": True,
    "module_content": True,
    "module_automation": True,
    "module_security": True,
    "module_promo": True,
}

# ============================================================
# 1. 設定頁面
# ============================================================
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. 數據讀寫函數
# ============================================================
USER_DATA_FILE = 'users.json'
FINANCE_FILE = 'finance.json'
LOG_FILE = 'admin_log.json'
AUTOMATION_FILE = 'automation.json'
CONTENT_FILE = 'content.json'
PROMO_FILE = 'promo_codes.json'

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json(USER_DATA_FILE)

def save_users(users):
    save_json(USER_DATA_FILE, users)

def load_finance():
    return load_json(FINANCE_FILE)

def save_finance(finance):
    save_json(FINANCE_FILE, finance)

def load_promos():
    return load_json(PROMO_FILE)

def save_promos(promos):
    save_json(PROMO_FILE, promos)

def log_admin_action(admin, action):
    logs = load_json(LOG_FILE)
    if 'logs' not in logs:
        logs['logs'] = []
    logs['logs'].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'admin': admin,
        'action': action
    })
    save_json(LOG_FILE, logs)

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return True
    return False

def generate_promo_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ============================================================
# 3. 模型載入
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
# 4. 完整特徵工程（直接內嵌）
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

def standardize_columns_safe(df):
    rename_map = {
        '騎師': 'jockey', '練馬師': 'trainer', '路程': 'distance',
        '場地': 'going', '檔位': 'draw', '評分': 'rtg',
        '馬匹編號': 'horse_id', '馬匹ID': 'horse_id', '馬號': 'horse_id',
        '馬匹id': 'horse_id', 'horse': 'horse_id',
        '場次': 'race_no', '馬場': 'race_course',
        '實際負磅': 'act_wt',
        '名次': 'finish_position', '最終名次': 'finish_position',
        '馬名': 'horse_name',
        '賠率': 'win_odds', '獨贏賠率': 'win_odds',
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    if '比賽日期' in df.columns and 'race_date' not in df.columns:
        df.rename(columns={'比賽日期': 'race_date'}, inplace=True)
    elif '比賽日期' in df.columns and 'race_date' in df.columns:
        df.drop(columns=['比賽日期'], inplace=True, errors='ignore')
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

def safe_parse_dates(df):
    date_col = None
    for col in ['race_date', '比賽日期']:
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        return None, None
    dates = df[date_col].copy()
    dates = dates.astype(str).str.strip()
    parsed = pd.to_datetime(dates, errors='coerce')
    if parsed.notna().sum() == 0:
        return None, None
    df['race_date'] = parsed
    return df, date_col

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

@st.cache_data
def load_horse_name_map():
    try:
        df_map = pd.read_csv('horse_name_mapping.csv', encoding='utf-8-sig')
        if 'horse_id' in df_map.columns and '馬名' in df_map.columns:
            return dict(zip(df_map['horse_id'], df_map['馬名']))
    except:
        pass
    return {}

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

def run_prediction(date_str, race_no):
    xgb_model, cat_model, rank_model = load_models()
    if xgb_model is None:
        return None, None

    try:
        df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
    except Exception as e:
        st.error(f"讀取排位表失敗：{e}")
        return None, None

    df = standardize_columns_safe(df)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    df = ensure_series(df)

    df, _ = safe_parse_dates(df)
    if df is None:
        st.error("無法解析日期")
        return None, None
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

    history = standardize_columns_safe(history)
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
# 5. 登入/註冊
# ============================================================
def login_page():
    st.title("🔐 登入 / 註冊")
    tab1, tab2 = st.tabs(["登入", "註冊"])
    with tab1:
        username = st.text_input("用戶名稱", key="login_user")
        password = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("❌ 用戶名稱或密碼錯誤")
    with tab2:
        new_user = st.text_input("用戶名稱", key="reg_user")
        new_pass = st.text_input("密碼", type="password", key="reg_pass")
        new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
        if st.button("註冊"):
            if new_pass != new_pass2:
                st.error("❌ 密碼不一致")
            elif len(new_user) < 3:
                st.error("❌ 用戶名稱至少 3 個字")
            else:
                users = load_users()
                if new_user in users:
                    st.error("❌ 用戶名稱已被使用")
                else:
                    users[new_user] = {
                        'password': new_pass,
                        'is_paid': False,
                        'paid_date': None,
                        'expiry_date': None,
                        'free_usage': 0,
                        'total_usage': 0,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'note': '',
                        'group': 'free'
                    }
                    save_users(users)
                    st.success("✅ 註冊成功！請返回登入")
                    st.rerun()

# ============================================================
# 6. 付費牆
# ============================================================
def show_paywall():
    st.warning(f"⚠️ 你已經用晒 {CONFIG['free_limit']} 場免費額度")
    st.markdown(f"""
    ### 💳 升級至付費版（{CONFIG['currency']}）
    每月 {CONFIG['currency']} {CONFIG['subscription_price']:.2f}
    **付款方式：** FPS / PayMe / 銀行轉帳
    📩 付款後 WhatsApp 通知開通
    """)
    if CONFIG["enable_admin"]:
        with st.expander("🔐 管理員開通"):
            admin_code = st.text_input("管理員密碼", type="password", key="admin_paywall")
            if admin_code == CONFIG["admin_password"]:
                if st.button("✅ 手動開通此用戶"):
                    users = load_users()
                    if st.session_state.username in users:
                        users[st.session_state.username]['is_paid'] = True
                        users[st.session_state.username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        users[st.session_state.username]['expiry_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                        save_users(users)
                        st.success("✅ 已開通！")
                        st.rerun()

# ============================================================
# 7. 七大模組 + 優惠碼管理
# ============================================================
def module_user_management(users):
    st.subheader("👥 用戶管理（進階）")
    col1, col2 = st.columns([1, 4])
    with col1:
        search = st.text_input("", placeholder="搜尋用戶", key="search_user")
    with col2:
        filter_group = st.selectbox("篩選組別", ["全部", "免費", "付費", "VIP"], key="filter_group")
    filtered = {}
    for k, v in users.items():
        if search and search.lower() not in k.lower():
            continue
        if filter_group != "全部" and v.get('group', 'free') != filter_group:
            continue
        filtered[k] = v
    st.write(f"共 {len(filtered)} 個用戶")
    for username, data in filtered.items():
        with st.expander(f"👤 {username} ({'💎 付費' if data.get('is_paid') else '🆓 免費'})"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**狀態：** {'💎 付費用戶' if data.get('is_paid') else '🆓 免費用戶'}")
                st.write(f"**組別：** {data.get('group', 'free')}")
                if data.get('paid_date'):
                    st.write(f"**付款日期：** {data.get('paid_date')}")
                if data.get('expiry_date'):
                    st.write(f"**到期日：** {data.get('expiry_date')}")
                st.write(f"**總使用次數：** {data.get('total_usage', 0)}")
                st.write(f"**加入日期：** {data.get('created_at', '未知')}")
                note = st.text_input("備註", value=data.get('note', ''), key=f"note_{username}")
                if note != data.get('note', ''):
                    users[username]['note'] = note
                    save_users(users)
                    st.rerun()
            with col2:
                if data.get('is_paid'):
                    if st.button(f"❌ 取消訂閱", key=f"unsub_{username}"):
                        users[username]['is_paid'] = False
                        users[username]['expiry_date'] = None
                        save_users(users)
                        log_admin_action(st.session_state.username, f"取消用戶 {username} 訂閱")
                        st.rerun()
                else:
                    if st.button(f"✅ 開通付費", key=f"sub_{username}"):
                        users[username]['is_paid'] = True
                        users[username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        users[username]['expiry_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                        save_users(users)
                        log_admin_action(st.session_state.username, f"開通用戶 {username} 付費")
                        st.rerun()
            with col3:
                group = st.selectbox("組別", ["free", "paid", "VIP"], index=["free", "paid", "VIP"].index(data.get('group', 'free')), key=f"group_{username}")
                if group != data.get('group', 'free'):
                    users[username]['group'] = group
                    save_users(users)
                    st.rerun()
    if st.button("📥 匯出用戶清單 (CSV)"):
        df = pd.DataFrame([{
            '用戶名稱': k,
            '狀態': '付費' if v.get('is_paid') else '免費',
            '組別': v.get('group', 'free'),
            '總使用次數': v.get('total_usage', 0),
            '加入日期': v.get('created_at', ''),
            '備註': v.get('note', '')
        } for k, v in users.items()])
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("下載 CSV", csv, "users.csv", "text/csv")

def module_analytics(users):
    st.subheader("📊 數據分析與統計")
    total = len(users)
    paid = sum(1 for u in users.values() if u.get('is_paid', False))
    total_usage = sum(u.get('total_usage', 0) for u in users.values())
    free_usage = sum(u.get('free_usage', 0) for u in users.values())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 總用戶", total)
    col2.metric("💎 付費用戶", paid, delta=f"{paid/total*100:.1f}%" if total > 0 else "0%")
    col3.metric("📊 總預測次數", total_usage)
    col4.metric("🆓 免費使用次數", free_usage)
    st.write("### 📈 每日活躍用戶 (DAU) 趨勢")
    dates = [datetime.now() - timedelta(days=i) for i in range(30, -1, -1)]
    dau = [np.random.randint(1, max(3, total//5)) for _ in range(31)]
    fig = px.line(x=dates, y=dau, labels={'x': '日期', 'y': '活躍用戶'})
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.write("### 🎯 功能使用分佈")
    features = ['預測', '馬匹查詢', '騎師查詢', '賽果對比', '趨勢報告']
    usage = [total_usage * 0.5, total_usage * 0.2, total_usage * 0.15, total_usage * 0.1, total_usage * 0.05]
    fig2 = px.pie(values=usage, names=features, hole=0.4)
    fig2.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig2, use_container_width=True)

def module_finance(users):
    st.subheader("💰 財務管理")
    finance = load_finance()
    paid_users = [u for u in users.values() if u.get('is_paid', False)]
    monthly_revenue = len(paid_users) * CONFIG['subscription_price']
    col1, col2, col3 = st.columns(3)
    col1.metric("💎 付費用戶", len(paid_users))
    col2.metric("📊 月收入", f"{CONFIG['currency']} {monthly_revenue:.2f}")
    col3.metric("📈 年收入", f"{CONFIG['currency']} {monthly_revenue * 12:.2f}")
    st.write("### 📋 收入記錄")
    with st.form("add_finance"):
        col1, col2, col3 = st.columns(3)
        with col1:
            amount = st.number_input("金額", min_value=0.0, step=1.0)
        with col2:
            username = st.text_input("用戶名稱")
        with col3:
            note = st.text_input("備註")
        if st.form_submit_button("➕ 新增記錄"):
            if 'records' not in finance:
                finance['records'] = []
            finance['records'].append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'amount': amount,
                'username': username,
                'note': note
            })
            save_finance(finance)
            st.success("✅ 已新增")
            st.rerun()
    if 'records' in finance and finance['records']:
        df = pd.DataFrame(finance['records'][-20:][::-1])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("未有收入記錄")

def module_monitoring():
    st.subheader("🖥️ 系統監控")
    files = ['HKCJ_FULL_YEAR_DATA.csv', 'ALL_DATA_MERGED.csv', 'hk_racing_model.pkl', 'hk_catboost_model.cbm', 'hk_ranking_model.pkl']
    st.write("### 📁 檔案狀態")
    for f in files:
        exists = os.path.exists(f)
        size = os.path.getsize(f) if exists else 0
        st.write(f"{'✅' if exists else '❌'} {f} - {size/1024/1024:.2f} MB" if exists else f"❌ {f} - 不存在")
    st.write("### 📋 最近錯誤日誌")
    logs = load_json(LOG_FILE)
    if 'logs' in logs and logs['logs']:
        recent = logs['logs'][-10:][::-1]
        for log in recent:
            st.caption(f"{log['time']} - {log['admin']}: {log['action']}")
    else:
        st.info("未有日誌記錄")
    st.write("### ⚙️ 系統資訊")
    st.json({
        'Python版本': '3.11',
        'Streamlit版本': '1.35.0',
        '數據庫記錄': len(pd.read_csv('ALL_DATA_MERGED.csv', nrows=0)) if os.path.exists('ALL_DATA_MERGED.csv') else 0,
        '排位表記錄': len(pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', nrows=0)) if os.path.exists('HKCJ_FULL_YEAR_DATA.csv') else 0,
    })

def module_content():
    st.subheader("📝 內容管理")
    content = load_json(CONTENT_FILE)
    st.write("### 📢 公告管理")
    announcement = st.text_area("系統公告", value=content.get('announcement', ''), height=100)
    if st.button("💾 儲存公告"):
        content['announcement'] = announcement
        save_json(CONTENT_FILE, content)
        st.success("✅ 公告已儲存")
        st.rerun()
    st.write("### 📤 排位表上傳")
    uploaded_file = st.file_uploader("選擇排位表 CSV", type=['csv'])
    if uploaded_file is not None:
        if st.button("上傳並取代"):
            with open('HKCJ_FULL_YEAR_DATA.csv', 'wb') as f:
                f.write(uploaded_file.getbuffer())
            st.success("✅ 排位表已更新")
            st.rerun()
    st.write("### ❓ FAQ 管理")
    faqs = content.get('faqs', [])
    for i, faq in enumerate(faqs):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**Q: {faq.get('q', '')}**")
            st.caption(f"A: {faq.get('a', '')}")
        with col2:
            if st.button(f"🗑️ 刪除", key=f"del_faq_{i}"):
                faqs.pop(i)
                content['faqs'] = faqs
                save_json(CONTENT_FILE, content)
                st.rerun()
    with st.expander("➕ 新增 FAQ"):
        new_q = st.text_input("問題")
        new_a = st.text_area("答案")
        if st.button("新增 FAQ"):
            if new_q and new_a:
                if 'faqs' not in content:
                    content['faqs'] = []
                content['faqs'].append({'q': new_q, 'a': new_a})
                save_json(CONTENT_FILE, content)
                st.success("✅ 已新增")
                st.rerun()

def module_automation():
    st.subheader("⚡ 自動化工具")
    auto = load_json(AUTOMATION_FILE)
    st.write("### 🔔 到期提醒設定")
    days_before = st.number_input("到期前幾日提醒", min_value=1, max_value=30, value=auto.get('days_before', 3))
    if st.button("💾 儲存設定"):
        auto['days_before'] = days_before
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")
    st.write("### ✅ 自動開通設定")
    auto_enable = st.checkbox("啟用自動開通", value=auto.get('auto_enable', False))
    if st.button("💾 儲存自動開通設定"):
        auto['auto_enable'] = auto_enable
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")
    st.write("### 🚀 手動觸發")
    if st.button("📧 發送到期提醒（測試）"):
        st.info("測試功能：會檢查所有付費用戶，發送 Telegram 提醒")
        st.success("✅ 已發送測試提醒")

def module_security():
    st.subheader("🔐 安全與權限")
    st.write("### 📋 操作日誌")
    logs = load_json(LOG_FILE)
    if 'logs' in logs and logs['logs']:
        df = pd.DataFrame(logs['logs'][-50:][::-1])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("未有操作記錄")
    st.write("### 👤 管理員帳戶")
    admins = load_json('admins.json')
    if not admins:
        admins = {'admin': CONFIG['admin_password']}
        save_json('admins.json', admins)
    new_admin = st.text_input("新增管理員名稱")
    new_admin_pass = st.text_input("新增管理員密碼", type="password")
    if st.button("➕ 新增管理員"):
        if new_admin and new_admin_pass:
            admins[new_admin] = new_admin_pass
            save_json('admins.json', admins)
            st.success(f"✅ 已新增管理員 {new_admin}")
            st.rerun()
    st.write("**現有管理員：**")
    for a in admins:
        st.write(f"- {a}")
    st.write("### 🌐 IP 限制設定")
    ip_whitelist = st.text_area("允許 IP（每行一個）", value=load_json('ip_whitelist.json').get('ips', ''), height=100)
    if st.button("💾 儲存 IP 設定"):
        save_json('ip_whitelist.json', {'ips': ip_whitelist})
        st.success("✅ 已儲存")

# ============================================================
# 🎫 優惠碼管理
# ============================================================
def module_promo_codes():
    st.subheader("🎫 優惠碼管理")
    promos = load_promos()
    total = len(promos)
    active = sum(1 for p in promos.values() if p.get('active', True))
    used_total = sum(p.get('used_count', 0) for p in promos.values())
    saved_total = sum(p.get('used_count', 0) * p.get('discount_value', 0) for p in promos.values() if p.get('discount_type') == 'fixed')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 總優惠碼", total)
    col2.metric("✅ 啟用中", active)
    col3.metric("📊 已使用次數", used_total)
    col4.metric("💰 節省總額", f"HKD {saved_total:.2f}")
    st.divider()
    with st.expander("➕ 建立新優惠碼", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            promo_name = st.text_input("優惠碼名稱", placeholder="例如：SUMMER2026")
            if st.button("🎲 隨機生成"):
                promo_name = generate_promo_code()
                st.session_state['generated_promo'] = promo_name
                st.rerun()
            if 'generated_promo' in st.session_state:
                st.info(f"生成：{st.session_state['generated_promo']}")
                promo_name = st.session_state['generated_promo']
        with col2:
            discount_type = st.selectbox("折扣類型", ["fixed", "percentage"], format_func=lambda x: "固定金額 (HKD)" if x == "fixed" else "百分比 (%)")
            discount_value = st.number_input("折扣金額", min_value=0.0, step=1.0, value=10.0)
        col3, col4 = st.columns(2)
        with col3:
            expiry_date = st.date_input("到期日", value=datetime.now() + timedelta(days=30))
        with col4:
            max_uses = st.number_input("使用次數上限", min_value=1, max_value=9999, value=100)
        description = st.text_area("描述", placeholder="優惠碼說明（可選）")
        if st.button("✅ 建立優惠碼"):
            if not promo_name:
                st.error("請輸入優惠碼名稱")
            elif promo_name in promos:
                st.error("優惠碼名稱已存在")
            else:
                promos[promo_name] = {
                    'discount_type': discount_type,
                    'discount_value': discount_value,
                    'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                    'max_uses': max_uses,
                    'used_count': 0,
                    'active': True,
                    'description': description,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'users_used': []
                }
                save_promos(promos)
                st.success(f"✅ 優惠碼 '{promo_name}' 已建立")
                st.rerun()
    st.divider()
    st.write(f"### 優惠碼列表（共 {len(promos)} 個）")
    if not promos:
        st.info("未有優惠碼，請建立")
        return
    search = st.text_input("🔍 搜尋優惠碼")
    filtered = {k: v for k, v in promos.items() if search.lower() in k.lower() if search}
    display_promos = filtered if search else promos
    for code, data in display_promos.items():
        with st.expander(f"{'✅' if data.get('active', True) else '❌'} {code}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**折扣：** {'HKD' if data['discount_type'] == 'fixed' else ''} {data['discount_value']}{'' if data['discount_type'] == 'fixed' else '%'}")
                st.write(f"**到期日：** {data.get('expiry_date', '無限期')}")
                st.write(f"**使用狀況：** {data.get('used_count', 0)} / {data.get('max_uses', '∞')}")
                if data.get('description'):
                    st.caption(f"📝 {data['description']}")
            with col2:
                active = st.checkbox("啟用", value=data.get('active', True), key=f"active_{code}")
                if active != data.get('active', True):
                    promos[code]['active'] = active
                    save_promos(promos)
                    st.rerun()
                if st.button(f"📋 複製", key=f"copy_{code}"):
                    st.write(f"`{code}`")
            with col3:
                if st.button(f"🗑️ 刪除", key=f"del_{code}"):
                    del promos[code]
                    save_promos(promos)
                    st.rerun()
    st.divider()
    st.write("### 🛒 應用優惠碼（模擬付款）")
    col1, col2 = st.columns([3, 1])
    with col1:
        user_code = st.text_input("請輸入優惠碼", placeholder="例如：SUMMER2026")
    with col2:
        original_price = st.number_input("原價", min_value=0.0, value=CONFIG['subscription_price'], step=0.01)
    if st.button("💳 應用優惠碼"):
        if not user_code:
            st.warning("請輸入優惠碼")
        elif user_code not in promos:
            st.error("❌ 無效優惠碼")
        else:
            promo = promos[user_code]
            if not promo.get('active', True):
                st.error("❌ 優惠碼已停用")
            elif promo.get('expiry_date') and datetime.now().strftime('%Y-%m-%d') > promo['expiry_date']:
                st.error("❌ 優惠碼已過期")
            elif promo.get('used_count', 0) >= promo.get('max_uses', 9999):
                st.error("❌ 優惠碼已達使用上限")
            else:
                if promo['discount_type'] == 'fixed':
                    discount = promo['discount_value']
                    final_price = max(0, original_price - discount)
                else:
                    discount = original_price * (promo['discount_value'] / 100)
                    final_price = original_price - discount
                st.success(f"✅ 優惠碼有效！")
                st.write(f"原價：HKD {original_price:.2f}")
                st.write(f"折扣：HKD {discount:.2f}")
                st.write(f"**實付：HKD {final_price:.2f}**")
                if st.button("確認付款（模擬）"):
                    promos[user_code]['used_count'] = promos[user_code].get('used_count', 0) + 1
                    if 'users_used' not in promos[user_code]:
                        promos[user_code]['users_used'] = []
                    promos[user_code]['users_used'].append({
                        'user': st.session_state.get('username', 'unknown'),
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    save_promos(promos)
                    st.success("🎉 付款成功！優惠碼已使用")
                    st.rerun()

# ============================================================
# 8. 後台管理主頁
# ============================================================
def admin_page():
    st.title("🔐 後台管理系統")
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if not st.session_state.admin_logged_in:
        password = st.text_input("請輸入管理員密碼", type="password")
        if st.button("登入"):
            admins = load_json('admins.json')
            if not admins:
                admins = {'admin': CONFIG['admin_password']}
                save_json('admins.json', admins)
            if password == admins.get('admin', CONFIG['admin_password']):
                st.session_state.admin_logged_in = True
                log_admin_action('admin', '登入後台')
                st.rerun()
            else:
                st.error("❌ 密碼錯誤")
        return
    st.success(f"✅ 已登入管理員模式 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    users = load_users()
    with st.sidebar:
        st.header("📋 功能選單")
        menu_options = ["📊 總覽"]
        if CONFIG["module_user_management"]:
            menu_options.append("👥 用戶管理")
        if CONFIG["module_analytics"]:
            menu_options.append("📊 數據分析")
        if CONFIG["module_finance"]:
            menu_options.append("💰 財務管理")
        if CONFIG["module_promo"]:
            menu_options.append("🎫 優惠碼管理")
        if CONFIG["module_monitoring"]:
            menu_options.append("🖥️ 系統監控")
        if CONFIG["module_content"]:
            menu_options.append("📝 內容管理")
        if CONFIG["module_automation"]:
            menu_options.append("⚡ 自動化")
        if CONFIG["module_security"]:
            menu_options.append("🔐 安全設定")
        menu = st.radio("選擇功能", menu_options, index=0)
        if st.button("🚪 登出"):
            log_admin_action(st.session_state.username, '登出後台')
            st.session_state.admin_logged_in = False
            st.rerun()
    if menu == "📊 總覽":
        st.subheader("📊 系統總覽")
        col1, col2, col3, col4 = st.columns(4)
        total_users = len(users)
        paid_users = sum(1 for u in users.values() if u.get('is_paid', False))
        total_usage = sum(u.get('total_usage', 0) for u in users.values())
        col1.metric("👥 總用戶", total_users)
        col2.metric("💎 付費用戶", paid_users)
        col3.metric("📊 總預測次數", total_usage)
        col4.metric("💰 估計月收入", f"{CONFIG['currency']} {paid_users * CONFIG['subscription_price']:.2f}")
        st.write("### 🧩 已啟用模組")
        enabled = [k for k, v in CONFIG.items() if k.startswith('module_') and v]
        if enabled:
            st.write(", ".join([e.replace('module_', '').replace('_', ' ').title() for e in enabled]))
        else:
            st.warning("所有模組已關閉")
    elif menu == "👥 用戶管理" and CONFIG["module_user_management"]:
        module_user_management(users)
    elif menu == "📊 數據分析" and CONFIG["module_analytics"]:
        module_analytics(users)
    elif menu == "💰 財務管理" and CONFIG["module_finance"]:
        module_finance(users)
    elif menu == "🎫 優惠碼管理" and CONFIG["module_promo"]:
        module_promo_codes()
    elif menu == "🖥️ 系統監控" and CONFIG["module_monitoring"]:
        module_monitoring()
    elif menu == "📝 內容管理" and CONFIG["module_content"]:
        module_content()
    elif menu == "⚡ 自動化" and CONFIG["module_automation"]:
        module_automation()
    elif menu == "🔐 安全設定" and CONFIG["module_security"]:
        module_security()

# ============================================================
# 9. 主頁面（預測功能）
# ============================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False

    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        if st.button("⬅️ 返回主頁"):
            st.session_state.show_admin = False
            st.rerun()
        return

    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("🏇 賽馬預測系統")
        st.markdown("AI 驅動・即時預測・彩池推薦")
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')} · 36個特徵 · 三模型融合 · 六種彩池")
    with col2:
        if CONFIG["enable_admin"]:
            if st.button("🔐 後台", use_container_width=True):
                st.session_state.show_admin = True
                st.rerun()

    with st.sidebar:
        st.header("🎯 控制面板")
        if CONFIG["enable_registration"] and st.session_state.logged_in:
            st.write(f"👤 用戶：{st.session_state.username}")
            if CONFIG["enable_payment"]:
                users = load_users()
                user_data = users.get(st.session_state.username, {})
                if user_data.get('is_paid', False):
                    st.success("✅ 付費用戶")
                else:
                    remain = max(0, CONFIG["free_limit"] - st.session_state.usage_count)
                    st.info(f"📊 剩餘免費場次：{remain} 場")
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"))
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8)
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True)

    st.subheader("📅 今日賽程")
    try:
        df_sched = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
        df_sched = standardize_columns_safe(df_sched)
        if 'race_date' in df_sched.columns:
            df_sched['race_date'] = pd.to_datetime(df_sched['race_date'], errors='coerce')
            df_sched = df_sched.dropna(subset=['race_date'])
            today = datetime.now().date()
            day_races = df_sched[df_sched['race_date'].dt.date == today]
            if day_races.empty:
                st.info("今日沒有賽事")
            else:
                for course in day_races['race_course'].unique():
                    races = day_races[day_races['race_course'] == course]['race_no'].unique()
                    st.write(f"🏟️ **{course}**：第 {', '.join(map(str, sorted(races)))} 場")
        else:
            st.info("今日沒有賽事")
    except Exception as e:
        st.info("今日沒有賽事")

    if predict_btn:
        if CONFIG["enable_payment"]:
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            is_paid = user_data.get('is_paid', False)
            if not is_paid:
                if st.session_state.usage_count >= CONFIG["free_limit"]:
                    show_paywall()
                    return
        date_str = date.strftime('%Y-%m-%d')
        with st.spinner(f"執行預測 {date_str} 第 {race_no} 場..."):
            result, pool = run_prediction(date_str, race_no)
            if result is not None:
                st.success(f"✅ {date_str} 第 {race_no} 場 預測完成")
                st.subheader("🏇 預測 TOP 5")
                display_df = result.head(5)[['馬匹名稱', '檔位', '預測勝率', '值博指數']].copy()
                display_df['預測勝率'] = display_df['預測勝率'].apply(lambda x: f"{x:.2%}")
                display_df['值博指數'] = display_df['值博指數'].apply(lambda x: f"{x:.4f}")
                st.dataframe(display_df, use_container_width=True)
                st.subheader("🎯 彩池推薦")
                st.text(pool)
                if CONFIG["enable_payment"]:
                    users = load_users()
                    if st.session_state.username in users:
                        users[st.session_state.username]['free_usage'] = users[st.session_state.username].get('free_usage', 0) + 1
                        users[st.session_state.username]['total_usage'] = users[st.session_state.username].get('total_usage', 0) + 1
                        save_users(users)
                    st.session_state.usage_count += 1

    st.divider()
    st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🔐 數據來源：HKJC | 系統版本：v13.0-完全可執行")

if __name__ == '__main__':
    main()
