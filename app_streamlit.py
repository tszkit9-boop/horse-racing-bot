#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 完整版（所有功能齊全）
包含：自動升級、自動終止、付款審核、用戶管理、數據分析、財務、優惠碼、預測監控、訂閱管理、系統監控、內容管理、自動化、安全
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
import random
from PIL import Image

# ============================================================
# 🔐 功能開關
# ============================================================
CONFIG = {
    "enable_registration": True,
    "enable_payment": False,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "admin_password": "z54060437K",
    "price_day": 18,
    "price_month": 128,
    "price_quarter": 328,
    "verification_expiry": 5,
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
# 2. 數據讀寫函數（加強錯誤處理）
# ============================================================
USER_DATA_FILE = 'users.json'
FINANCE_FILE = 'finance.json'
LOG_FILE = 'admin_log.json'
AUTOMATION_FILE = 'automation.json'
CONTENT_FILE = 'content.json'
PROMO_FILE = 'promo_codes.json'
ACCURACY_FILE = 'accuracy.json'
PAYMENT_PROOFS_FILE = 'payment_proofs.json'
PAYMENT_PROOFS_DIR = 'payment_proofs'

if not os.path.exists(PAYMENT_PROOFS_DIR):
    os.makedirs(PAYMENT_PROOFS_DIR)

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"讀取 {file} 失敗：{e}")
            return {}
    return {}

def save_json(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"寫入 {file} 失敗：{e}")
        return False

def load_users():
    users = load_json(USER_DATA_FILE)
    if not users or "admin" not in users:
        users = {
            "admin": {
                "username": "admin",
                "password": CONFIG["admin_password"],
                "is_paid": False,
                "paid_date": None,
                "expiry_date": None,
                "free_usage": 0,
                "total_usage": 0,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "note": "系統超級管理員",
                "group": "super_admin",
                "phone": "",
                "plan": None,
                "predictions_limit": -1,
                "history": []
            }
        }
        save_users(users)
    else:
        if "admin" in users:
            users["admin"]["group"] = "super_admin"
            users["admin"]["predictions_limit"] = -1
            if users["admin"].get("note") != "系統超級管理員":
                users["admin"]["note"] = "系統超級管理員（已自動修復）"
            save_users(users)
        for uid, u in users.items():
            if 'plan' not in u: u['plan'] = None
            if 'paid_date' not in u: u['paid_date'] = None
            if 'expiry_date' not in u: u['expiry_date'] = None
            if 'phone' not in u: u['phone'] = ''
            if 'note' not in u: u['note'] = ''
            if 'history' not in u: u['history'] = []
            if 'free_usage' not in u: u['free_usage'] = 0
            if 'total_usage' not in u: u['total_usage'] = 0
            if 'predictions_limit' not in u:
                u['predictions_limit'] = CONFIG["free_limit"]
        save_users(users)
    return users

def save_users(users):
    return save_json(USER_DATA_FILE, users)

def load_finance():
    return load_json(FINANCE_FILE)

def save_finance(finance):
    return save_json(FINANCE_FILE, finance)

def load_promos():
    return load_json(PROMO_FILE)

def save_promos(promos):
    return save_json(PROMO_FILE, promos)

def load_logs():
    return load_json(LOG_FILE)

def save_logs(logs):
    return save_json(LOG_FILE, logs)

def load_accuracy():
    return load_json(ACCURACY_FILE)

def save_accuracy(acc):
    return save_json(ACCURACY_FILE, acc)

def load_payment_proofs():
    proofs = load_json(PAYMENT_PROOFS_FILE)
    if not proofs:
        proofs = {"proof_records": []}
        save_payment_proofs(proofs)
    elif "proof_records" not in proofs:
        proofs["proof_records"] = []
        save_payment_proofs(proofs)
    return proofs

def save_payment_proofs(proofs):
    return save_json(PAYMENT_PROOFS_FILE, proofs)

def log_admin_action(admin, action):
    logs = load_logs()
    if 'logs' not in logs: logs['logs'] = []
    logs['logs'].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'admin': admin,
        'action': action
    })
    save_logs(logs)

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return True
    return False

def generate_promo_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))

def generate_verification_code():
    return ''.join(random.choices('0123456789', k=6))

def get_plan_days(plan):
    if plan == 'day': return 1
    elif plan == 'month': return 30
    elif plan == 'quarter': return 90
    return 0

def get_plan_name(plan):
    names = {'day': '日費', 'month': '月費', 'quarter': '季費'}
    return names.get(plan, '未知')

def get_plan_price(plan):
    if plan == 'day': return CONFIG['price_day']
    elif plan == 'month': return CONFIG['price_month']
    elif plan == 'quarter': return CONFIG['price_quarter']
    return 0

# ============================================================
# 3. 模型載入（若檔案不存在則跳過）
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
# 4. 完整特徵工程（36 特徵 + 預測核心）
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
# 5. 用戶功能
# ============================================================
def record_prediction(username, date_str, race_no, horse_name, predicted_prob=None):
    users = load_users()
    if username in users:
        if 'history' not in users[username]:
            users[username]['history'] = []
        users[username]['history'].append({
            'date': date_str,
            'race': race_no,
            'horse': horse_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_prob': predicted_prob
        })
        save_users(users)
        acc = load_accuracy()
        if 'records' not in acc:
            acc['records'] = []
        acc['records'].append({
            'username': username,
            'date': date_str,
            'race': race_no,
            'horse': horse_name,
            'predicted_at': datetime.now().isoformat(),
            'actual_result': None,
            'is_hit': None
        })
        save_accuracy(acc)

def get_user_stats(username):
    users = load_users()
    if username not in users:
        return {'total_predictions': 0, 'free_used': 0, 'is_paid': False, 'group': 'free', 'plan': None}
    user = users[username]
    history = user.get('history', [])
    total = len(history)
    free_used = user.get('free_usage', 0)
    return {
        'total_predictions': total,
        'free_used': free_used,
        'is_paid': user.get('is_paid', False),
        'group': user.get('group', 'free'),
        'plan': user.get('plan', None)
    }

def show_user_dashboard(username):
    if not username:
        return
    stats = get_user_stats(username)
    users = load_users()
    user_data = users.get(username, {})
    group = user_data.get('group', 'free')
    is_paid = user_data.get('is_paid', False)
    plan = user_data.get('plan', None)
    expiry = user_data.get('expiry_date', None)
    
    if group == 'super_admin':
        level = "👑 超級管理員"
    elif group == 'VIP':
        level = "👑 VIP"
    elif is_paid:
        level = "💎 付費用戶"
    else:
        level = "🆓 免費用戶"
    
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👤 用戶", username)
    col2.metric("🏷️ 級別", level)
    col3.metric("📊 總預測次數", stats['total_predictions'])
    limit = user_data.get('predictions_limit', CONFIG['free_limit'])
    if limit == -1:
        col4.metric("📊 剩餘場次", "♾️ 無限")
    else:
        used = user_data.get('free_usage', 0)
        remain = max(0, limit - used)
        col4.metric("📊 剩餘場次", remain)
    st.markdown("---")
    if plan:
        st.caption(f"📌 當前方案：{get_plan_name(plan)}")

def show_prediction_history(username):
    if not username:
        st.info("請先登入以查看歷史記錄")
        return
    users = load_users()
    if username not in users:
        st.info("未有歷史記錄")
        return
    history = users[username].get('history', [])
    if not history:
        st.info("你仲未有任何預測記錄")
        return
    df = pd.DataFrame(history[-20:][::-1])
    st.dataframe(df, use_container_width=True)

# ============================================================
# 6. 登入/註冊
# ============================================================
def login_page():
    st.title("🔐 登入 / 註冊")
    tab1, tab2 = st.tabs(["登入", "註冊"])
    
    with tab1:
        username = st.text_input("用戶名稱", key="login_user")
        password = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入", key="login_button"):
            users = load_users()
            if username in users and users[username].get('password') == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = users[username].get('group', 'free')
                st.session_state.usage_count = users[username].get('free_usage', 0)
                st.rerun()
            else:
                st.error("❌ 用戶名稱或密碼錯誤")
    
    with tab2:
        st.subheader("📝 註冊新帳號")
        with st.form("register_form"):
            new_user = st.text_input("用戶名稱（最少 3 個字）", key="reg_user")
            phone = st.text_input("手機號碼（可選）", key="reg_phone")
            new_pass = st.text_input("密碼", type="password", key="reg_pass")
            new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                verify_code_input = st.text_input("驗證碼", key="reg_verify", placeholder="輸入 6 位數字", max_chars=6)
            with col2:
                if st.form_submit_button("📨 獲取驗證碼", type="secondary"):
                    code = generate_verification_code()
                    st.session_state['reg_verify_code'] = code
                    st.session_state['reg_verify_expiry'] = datetime.now() + timedelta(minutes=CONFIG.get('verification_expiry', 5))
                    st.info(f"📧 你嘅驗證碼係：**{code}**（有效期 5 分鐘）")
            
            submitted = st.form_submit_button("註冊")
            if submitted:
                if len(new_user) < 3:
                    st.error("❌ 用戶名稱至少 3 個字")
                elif new_pass != new_pass2:
                    st.error("❌ 密碼不一致")
                elif len(new_pass) < 4:
                    st.error("❌ 密碼至少 4 個字")
                else:
                    if 'reg_verify_code' not in st.session_state or \
                       verify_code_input != st.session_state['reg_verify_code'] or \
                       datetime.now() > st.session_state.get('reg_verify_expiry', datetime.now()):
                        st.error("❌ 驗證碼無效或已過期，請重新獲取")
                    else:
                        users = load_users()
                        if new_user in users:
                            st.error("❌ 用戶名稱已被使用")
                        else:
                            users[new_user] = {
                                'password': new_pass,
                                'phone': phone,
                                'is_paid': False,
                                'paid_date': None,
                                'expiry_date': None,
                                'free_usage': 0,
                                'total_usage': 0,
                                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'note': '',
                                'group': 'free',
                                'plan': None,
                                'predictions_limit': CONFIG["free_limit"],
                                'history': []
                            }
                            save_users(users)
                            st.success("✅ 註冊成功！請用你嘅帳號登入。")
                            st.rerun()

# ============================================================
# 🔧 付款牆（極簡穩定版 - 唔使圖片都提交到）
# ============================================================
def show_paywall():
    st.warning(f"⚠️ 你已經用晒 {CONFIG['free_limit']} 場免費額度")
    st.subheader("💳 選擇你嘅方案")

    plan_options = {
        "day": f"☀️ 日費  ${CONFIG['price_day']}   (1天)",
        "month": f"📆 月費  ${CONFIG['price_month']}  (30天)",
        "quarter": f"📅 季費  ${CONFIG['price_quarter']} (90天)"
    }

    if st.session_state.get('payment_just_submitted', False):
        st.success("✅ 付款申請已成功提交！管理員將盡快審核。")
        st.info("📩 請同時 WhatsApp 通知管理員（可加快審核）")
        if 'payment_detail' in st.session_state:
            st.write(st.session_state['payment_detail'])
        if st.button("返回主頁"):
            for key in ['payment_just_submitted', 'payment_detail']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.stop()

    with st.form(key="payment_form"):
        plan_choice = st.radio(
            "請選擇付費方案：",
            options=[""] + list(plan_options.keys()),
            format_func=lambda x: plan_options.get(x, "請選擇方案"),
            index=0,
            key="plan_radio_in_form"
        )

        if plan_choice:
            plan_name = get_plan_name(plan_choice)
            plan_days = get_plan_days(plan_choice)
            original_price = get_plan_price(plan_choice)
            st.info(f"📌 你已選擇 **{plan_name}**（原價 ${original_price}，有效期 {plan_days} 天）")
        else:
            st.info("請選擇一個方案以繼續")

        promo_input = st.text_input("優惠碼（如有）", key="promo_input_form", placeholder="例如 A7K3X9P2")
        uploaded_file = st.file_uploader(
            "上傳過數證明（FPS / PayMe / 銀行轉帳截圖）",
            type=['png', 'jpg', 'jpeg'],
            key="proof_upload_form"
        )
        if uploaded_file is not None:
            st.image(uploaded_file, caption="你上傳嘅證明", width=300)

        submitted = st.form_submit_button("📩 提交付款申請，等待管理員審核")

        if submitted:
            st.info("⏳ 正在處理你嘅申請...")
            
            if not plan_choice:
                st.error("❌ 請先選擇一個付費方案")
                st.stop()
            elif not st.session_state.get('logged_in', False):
                st.error("❌ 請先登入")
                st.stop()
            
            original_price = get_plan_price(plan_choice)
            final_price = original_price
            discount_applied = False
            discount_desc = ""
            promo_code_used = None
            
            if promo_input:
                promos = load_promos()
                promo_data = promos.get(promo_input)
                if promo_data and not promo_data.get('used', False):
                    expiry = promo_data.get('expiry')
                    if expiry:
                        try:
                            expiry_date = datetime.fromisoformat(expiry)
                            if expiry_date >= datetime.now():
                                discount_type = promo_data.get('discount_type', 'percentage')
                                discount_value = promo_data.get('discount_value', 0)
                                if discount_type == 'percentage':
                                    final_price = original_price * (1 - discount_value / 100)
                                    discount_desc = f"{discount_value}% 折扣"
                                elif discount_type == 'fixed':
                                    final_price = max(0, original_price - discount_value)
                                    discount_desc = f"減 ${discount_value}"
                                elif discount_type == 'free':
                                    final_price = 0
                                    discount_desc = "全免！"
                                final_price = round(final_price, 2)
                                discount_applied = True
                                promo_code_used = promo_input
                        except:
                            pass

            os.makedirs(PAYMENT_PROOFS_DIR, exist_ok=True)
            
            filename = None
            if uploaded_file is not None:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_extension = uploaded_file.type.split('/')[1] if '/' in uploaded_file.type else 'png'
                    filename = f"{st.session_state.username}_{timestamp}.{file_extension}"
                    filepath = os.path.join(PAYMENT_PROOFS_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ 圖片已儲存：{filename}")
                except Exception as e:
                    st.error(f"⚠️ 圖片儲存失敗（但會繼續提交）：{e}")
                    filename = None
            else:
                st.warning("⚠️ 你未上傳圖片，但仍可提交")

            try:
                proofs = load_payment_proofs()
                new_proof = {
                    "id": len(proofs['proof_records']) + 1,
                    "username": st.session_state.username,
                    "plan": plan_choice,
                    "plan_name": get_plan_name(plan_choice),
                    "original_price": original_price,
                    "final_price": final_price,
                    "discount_applied": discount_applied,
                    "discount_desc": discount_desc,
                    "promo_code": promo_code_used,
                    "filename": filename if filename else "無圖片",
                    "uploaded_at": datetime.now().isoformat(),
                    "status": "pending"
                }
                proofs['proof_records'].append(new_proof)
                
                if save_payment_proofs(proofs):
                    st.session_state['payment_just_submitted'] = True
                    st.session_state['payment_detail'] = f"方案：{get_plan_name(plan_choice)}，金額：${final_price}"
                    st.success("✅ 提交成功！管理員將盡快審核。")
                    st.rerun()
                else:
                    st.error("❌ 寫入付款記錄失敗，請檢查檔案權限")
                    st.stop()
            except Exception as e:
                st.error(f"❌ 提交過程中發生錯誤：{e}")
                st.stop()

# ============================================================
# 8. 後台所有模組（全部完整實作）
# ============================================================

# ---------- 8.1 用戶管理 ----------
def admin_user_management():
    st.subheader("👥 用戶管理")
    with st.expander("➕ 新增用戶", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("新用戶名", key="new_user_name")
            new_password = st.text_input("密碼", type="password", key="new_user_pw")
        with col2:
            new_group = st.selectbox("群組", ["free", "paid", "VIP", "super_admin"], key="new_user_group")
            new_is_paid = st.checkbox("付費狀態", value=False, key="new_user_paid")
        if st.button("建立用戶", key="create_user_btn"):
            if not new_username or not new_password:
                st.warning("請填寫用戶名同密碼")
            else:
                users = load_users()
                if new_username in users:
                    st.error("❌ 用戶名已被使用")
                else:
                    users[new_username] = {
                        "password": new_password,
                        "is_paid": new_is_paid,
                        "paid_date": None,
                        "expiry_date": None,
                        "free_usage": 0,
                        "total_usage": 0,
                        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "note": "手動新增",
                        "group": new_group,
                        "phone": "",
                        "plan": None,
                        "predictions_limit": -1 if new_group in ['super_admin', 'VIP'] else CONFIG["free_limit"],
                        "history": []
                    }
                    save_users(users)
                    log_admin_action(st.session_state.username, f"新增用戶 {new_username}")
                    st.success(f"✅ 用戶 {new_username} 已建立！")
                    st.rerun()
    
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return
    
    st.write("現有用戶列表：")
    df = pd.DataFrame.from_dict(users, orient='index')
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    st.subheader("🗑️ 刪除用戶")
    del_user = st.selectbox("選擇要刪除嘅用戶", list(users.keys()), key="del_user_select")
    if del_user:
        if del_user == "admin":
            st.warning("⚠️ 唔可以刪除 admin 帳號")
        else:
            confirm = st.checkbox(f"確認刪除 {del_user}？", key="confirm_del")
            if confirm and st.button("🗑️ 確認刪除", key="del_user_btn"):
                users.pop(del_user)
                save_users(users)
                log_admin_action(st.session_state.username, f"刪除用戶 {del_user}")
                st.success(f"✅ 用戶 {del_user} 已刪除")
                st.rerun()
    
    st.divider()
    st.subheader("👁️ 查看用戶視角")
    selected_user = st.selectbox("選擇要查看的用戶", list(users.keys()), key="view_user_select")
    if selected_user:
        user_data = users[selected_user]
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👤 用戶", selected_user)
        col2.metric("🏷️ 級別", user_data.get('group', 'free').upper())
        col3.metric("📊 總預測次數", len(user_data.get('history', [])))
        limit = user_data.get('predictions_limit', CONFIG['free_limit'])
        if limit == -1:
            col4.metric("📊 剩餘場次", "♾️ 無限")
        else:
            used = user_data.get('free_usage', 0)
            remain = max(0, limit - used)
            col4.metric("📊 剩餘場次", remain)
        st.markdown("---")
        st.subheader(f"📋 {selected_user} 嘅預測記錄")
        history = user_data.get('history', [])
        if history:
            df_hist = pd.DataFrame(history[-20:][::-1])
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("呢個用戶暫時冇任何預測記錄")
        if history:
            st.subheader(f"🎯 {selected_user} 嘅準確度統計")
            acc = load_accuracy()
            records = acc.get('records', [])
            user_records = [r for r in records if r.get('username') == selected_user]
            if user_records:
                df_rec = pd.DataFrame(user_records)
                total = len(df_rec)
                hit = df_rec[df_rec['is_hit'] == True].shape[0] if 'is_hit' in df_rec else 0
                hit_rate = hit/total if total>0 else 0
                roi = (hit * 400 - total * 100) / (total * 100) if total>0 else 0
                col1, col2, col3 = st.columns(3)
                col1.metric("總預測", total)
                col2.metric("命中", hit)
                col3.metric("命中率", f"{hit_rate:.2%}")
                st.metric("ROI (模擬)", f"{roi:.2%}")
                if 'date' in df_rec:
                    df_rec['date'] = pd.to_datetime(df_rec['date'])
                    daily = df_rec.groupby(df_rec['date'].dt.date).agg(
                        total=('is_hit', 'count'),
                        hit=('is_hit', lambda x: (x==True).sum())
                    ).reset_index()
                    daily['hit_rate'] = daily['hit'] / daily['total']
                    fig = px.line(daily, x='date', y='hit_rate', title=f'{selected_user} 嘅命中率趨勢')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("呢個用戶未有準確度數據（未對比賽果）")
    
    with st.expander("✏️ 編輯用戶"):
        username = st.selectbox("選擇要編輯的用戶", list(users.keys()), key="edit_user_select")
        if username:
            user = users[username]
            new_group = st.selectbox("群組", ['free', 'paid', 'VIP', 'super_admin'], index=['free','paid','VIP','super_admin'].index(user.get('group','free')), key="edit_group")
            new_is_paid = st.checkbox("付費狀態", value=user.get('is_paid', False), key="edit_is_paid")
            new_password = st.text_input("新密碼（留空 = 不變）", type="password", key="edit_password", placeholder="輸入新密碼")
            note = st.text_area("備註", value=user.get('note', ''), key="edit_note")
            if st.button("儲存變更", key="save_user_changes"):
                users[username]['group'] = new_group
                users[username]['is_paid'] = new_is_paid
                users[username]['note'] = note
                if new_password:
                    users[username]['password'] = new_password
                if new_group in ['super_admin', 'VIP']:
                    users[username]['predictions_limit'] = -1
                else:
                    users[username]['predictions_limit'] = CONFIG["free_limit"]
                save_users(users)
                log_admin_action(st.session_state.username, f"編輯用戶 {username}")
                st.success("✅ 已更新")
                st.rerun()

# ---------- 8.2 數據分析 ----------
def admin_analytics():
    st.subheader("📊 數據分析 & 用戶增長")
    users = load_users()
    total_users = len(users)
    paid_users = sum(1 for u in users.values() if u.get('is_paid', False))
    vip_users = sum(1 for u in users.values() if u.get('group') == 'VIP')
    super_admin_users = sum(1 for u in users.values() if u.get('group') == 'super_admin')
    total_pred = sum(u.get('total_usage', 0) for u in users.values())
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("總用戶", total_users)
    col2.metric("付費用戶", paid_users)
    col3.metric("VIP", vip_users)
    col4.metric("超級管理員", super_admin_users)
    col5.metric("總預測次數", total_pred)
    
    if users:
        df_users = pd.DataFrame.from_dict(users, orient='index')
        if 'created_at' in df_users.columns:
            df_users['created_at'] = pd.to_datetime(df_users['created_at'], errors='coerce')
            df_users = df_users.dropna(subset=['created_at'])
            df_users['date'] = df_users['created_at'].dt.date
            daily = df_users.groupby('date').size().reset_index(name='new_users')
            daily = daily.sort_values('date')
            daily['cumulative'] = daily['new_users'].cumsum()
            fig = px.line(daily, x='date', y=['new_users', 'cumulative'], 
                          title='每日新增用戶 & 累積用戶', 
                          labels={'value':'用戶數', 'date':'日期'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("未有 created_at 數據，無法顯示增長圖")
    else:
        st.info("暫無用戶")

# ---------- 8.3 財務管理 ----------
def admin_finance():
    st.subheader("💰 財務管理")
    finance = load_finance()
    total_income = finance.get('total_income', 0)
    monthly = finance.get('monthly_income', 0)
    yearly = finance.get('yearly_income', 0)
    col1, col2, col3 = st.columns(3)
    col1.metric("總收入 (HKD)", f"${total_income:.2f}")
    col2.metric("本月收入 (HKD)", f"${monthly:.2f}")
    col3.metric("今年收入 (HKD)", f"${yearly:.2f}")
    
    with st.expander("➕ 新增收入記錄"):
        amount = st.number_input("金額", min_value=0.0, step=10.0, key="finance_amount")
        desc = st.text_input("描述", key="finance_desc")
        if st.button("記錄", key="add_finance"):
            finance['total_income'] = finance.get('total_income', 0) + amount
            finance['monthly_income'] = finance.get('monthly_income', 0) + amount
            finance['yearly_income'] = finance.get('yearly_income', 0) + amount
            save_finance(finance)
            log_admin_action(st.session_state.username, f"新增收入 {amount} - {desc}")
            st.success("✅ 已記錄")
            st.rerun()

# ---------- 8.4 優惠碼管理 ----------
def admin_promo_codes():
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()
    col1, col2 = st.columns(2)
    with col1:
        st.write("現有優惠碼")
        if promos:
            df = pd.DataFrame.from_dict(promos, orient='index')
            if 'discount_type' not in df.columns:
                df['discount_type'] = 'percentage'
            if 'discount_value' not in df.columns:
                df['discount_value'] = 0
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暫無優惠碼")
    with col2:
        st.write("產生新優惠碼")
        duration = st.number_input("有效期 (天)", min_value=1, value=30, key="promo_duration")
        discount_type = st.selectbox("折扣類型", ["percentage", "fixed", "free"], key="promo_discount_type",
                                     format_func=lambda x: {"percentage": "百分比（%折扣）", "fixed": "固定金額（減$）", "free": "完全免費"}.get(x, x))
        discount_value = st.number_input("折扣數值", min_value=0, value=20, key="promo_discount_value", 
                                         help="百分比：20 = 8折（減20%）；固定金額：減指定金額；免費：無效")
        if st.button("產生優惠碼", key="gen_promo"):
            code = generate_promo_code()
            expiry = (datetime.now() + timedelta(days=duration)).isoformat()
            promos[code] = {
                "used": False,
                "expiry": expiry,
                "created_at": datetime.now().isoformat(),
                "discount_type": discount_type,
                "discount_value": discount_value
            }
            save_promos(promos)
            st.success(f"✅ 優惠碼已產生：`{code}` 有效期 {duration} 天")
            st.rerun()
        
        st.write("---")
        st.write("套用優惠碼")
        code_input = st.text_input("優惠碼", key="apply_promo_code")
        username_input = st.text_input("用戶名稱", key="apply_promo_user")
        if st.button("套用", key="apply_promo"):
            if code_input not in promos:
                st.error("優惠碼不存在")
            elif promos[code_input].get('used', False):
                st.error("優惠碼已被使用")
            else:
                users = load_users()
                if username_input not in users:
                    st.error("用戶不存在")
                else:
                    users[username_input]['is_paid'] = True
                    users[username_input]['group'] = 'paid'
                    users[username_input]['predictions_limit'] = -1
                    promos[code_input]['used'] = True
                    promos[code_input]['used_by'] = username_input
                    save_users(users)
                    save_promos(promos)
                    log_admin_action(st.session_state.username, f"套用優惠碼 {code_input} 給 {username_input}")
                    st.success("✅ 已升級用戶")
                    st.rerun()

# ---------- 8.5 預測監控 ----------
def admin_accuracy_monitor():
    st.subheader("📈 預測準確率監控")
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        st.info("暫時未有預測記錄，未能進行監控。")
        return

    try:
        results_df = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
        results_df = standardize_columns_safe(results_df)
        if 'race_date' not in results_df.columns or 'race_no' not in results_df.columns or '馬名' not in results_df.columns or 'finish_position' not in results_df.columns:
            if '日期' in results_df.columns:
                results_df.rename(columns={'日期': 'race_date'}, inplace=True)
            if '場次' in results_df.columns:
                results_df.rename(columns={'場次': 'race_no'}, inplace=True)
            if '馬名' not in results_df.columns and 'horse_name' in results_df.columns:
                results_df.rename(columns={'horse_name': '馬名'}, inplace=True)
            if 'finish_position' not in results_df.columns and '名次' in results_df.columns:
                results_df.rename(columns={'名次': 'finish_position'}, inplace=True)
        
        if 'race_date' in results_df.columns and 'race_no' in results_df.columns and '馬名' in results_df.columns and 'finish_position' in results_df.columns:
            results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
            results_df = results_df.dropna(subset=['race_date'])
            for rec in records:
                if rec.get('actual_result') is not None:
                    continue
                date_str = rec['date']
                race_no = rec['race']
                horse = rec['horse']
                matched = results_df[(results_df['race_date'].dt.strftime('%Y-%m-%d') == date_str) & 
                                     (results_df['race_no'] == race_no) & 
                                     (results_df['馬名'] == horse)]
                if not matched.empty:
                    pos = matched.iloc[0]['finish_position']
                    rec['actual_result'] = int(pos) if pd.notna(pos) else None
                    rec['is_hit'] = (rec['actual_result'] == 1) if rec['actual_result'] is not None else None
            save_accuracy(acc)
            st.success("✅ 已自動比對賽果")
        else:
            st.warning("ALL_DATA_MERGED.csv 缺少必要欄位，請確保包含：race_date, race_no, 馬名, finish_position")
    except Exception as e:
        st.error(f"自動比對失敗：{e}")

    df_records = pd.DataFrame(records)
    if df_records.empty:
        return
    total = len(df_records)
    hit = df_records[df_records['is_hit'] == True].shape[0] if 'is_hit' in df_records else 0
    hit_rate = hit/total if total>0 else 0
    roi = (hit * 400 - total * 100) / (total * 100) if total>0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("總預測記錄", total)
    col2.metric("命中次數", hit)
    col3.metric("命中率", f"{hit_rate:.2%}")
    st.metric("ROI (模擬)", f"{roi:.2%}")

    if 'date' in df_records:
        df_records['date'] = pd.to_datetime(df_records['date'])
        daily = df_records.groupby(df_records['date'].dt.date).agg(
            total=('is_hit', 'count'),
            hit=('is_hit', lambda x: (x==True).sum())
        ).reset_index()
        daily['hit_rate'] = daily['hit'] / daily['total']
        fig = px.line(daily, x='date', y='hit_rate', title='每日命中率趨勢')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 查看所有記錄"):
        st.dataframe(df_records, use_container_width=True)

# ---------- 8.6 訂閱管理 ----------
def admin_subscription():
    st.subheader("⏰ 訂閱管理 & 到期提醒")
    users = load_users()
    paid_users = {u: data for u, data in users.items() if data.get('is_paid', False) or data.get('group') in ['VIP', 'super_admin']}
    if not paid_users:
        st.info("暫時沒有付費用戶")
    else:
        df_paid = pd.DataFrame.from_dict(paid_users, orient='index')
        required_cols = ['is_paid', 'group', 'plan', 'paid_date', 'expiry_date']
        for col in required_cols:
            if col not in df_paid.columns:
                df_paid[col] = None
        df_paid['expiry_date'] = pd.to_datetime(df_paid['expiry_date'], errors='coerce')
        today = datetime.now()
        df_paid['days_left'] = (df_paid['expiry_date'] - today).dt.days
        df_paid['status'] = df_paid['days_left'].apply(lambda x: '🟢 有效' if x > 7 else ('🟡 快到期' if x > 0 else '🔴 已過期') if pd.notna(x) else '⚪ 未設定')
        display_cols = ['is_paid', 'group', 'plan', 'paid_date', 'expiry_date', 'days_left', 'status']
        st.dataframe(df_paid[display_cols], use_container_width=True)

    auto = load_json(AUTOMATION_FILE)
    remind_days = auto.get('remind_days', 3)
    new_remind = st.number_input("提前幾天提醒", min_value=1, value=remind_days, key="remind_days_sub")
    if st.button("儲存提醒設定", key="save_remind_sub"):
        auto['remind_days'] = new_remind
        save_json(AUTOMATION_FILE, auto)
        st.success(f"✅ 已設為提前 {new_remind} 天提醒")
        log_admin_action(st.session_state.username, f"設定提醒天數為 {new_remind}")

    # ---------- 自動終止過期會員 ----------
    st.divider()
    st.subheader("⏰ 自動終止過期會員")
    
    if st.button("🔍 檢查並終止過期會員", key="check_expired"):
        users = load_users()
        today = datetime.now()
        expired = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    exp = pd.to_datetime(u['expiry_date'])
                    if exp < today:
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = 2
                        u['plan'] = None
                        u['note'] = (u.get('note', '') + f' [於 {today.strftime("%Y-%m-%d")} 自動降級]').strip()
                        expired.append(uid)
                except Exception as e:
                    st.warning(f"⚠️ 檢查 {uid} 時出錯：{e}")
        if expired:
            save_users(users)
            st.success(f"✅ 已將 {len(expired)} 個過期會員降級：{', '.join(expired)}")
            log_admin_action(st.session_state.username, f"自動終止過期會員：{', '.join(expired)}")
        else:
            st.info("✅ 目前沒有過期會員")

    # ---------- 手動續期 ----------
    st.subheader("✏️ 手動續期")
    username = st.selectbox("選擇用戶", list(users.keys()), key="renew_user_select")
    if username:
        new_expiry = st.date_input("新的到期日", value=pd.to_datetime(datetime.now() + timedelta(days=30)), key="renew_date")
        if st.button("確認續期", key="renew_confirm"):
            users[username]['expiry_date'] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
            save_users(users)
            log_admin_action(st.session_state.username, f"續期用戶 {username} 至 {new_expiry}")
            st.success(f"✅ {username} 已續期至 {new_expiry}")
            st.rerun()

# ---------- 8.7 系統監控 ----------
def admin_monitoring():
    st.subheader("📡 系統監控")
    files = ['ALL_DATA_MERGED.csv', 'HKCJ_FULL_YEAR_DATA.csv', 'horse_name_mapping.csv',
             'hk_racing_model.pkl', 'hk_catboost_model.cbm', 'hk_ranking_model.pkl']
    for f in files:
        if os.path.exists(f):
            size = os.path.getsize(f)/1024
            st.success(f"✅ {f} 存在 ({size:.1f} KB)")
        else:
            st.error(f"❌ {f} 不存在")
    logs = load_logs()
    if logs.get('logs'):
        df_log = pd.DataFrame(logs['logs'][-20:])
        st.dataframe(df_log, use_container_width=True)

# ---------- 8.8 內容管理 ----------
def admin_content():
    st.subheader("📝 內容管理")
    content = load_json(CONTENT_FILE)
    
    with st.expander("📢 發佈新公告", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("公告標題", placeholder="例如：今日沙田日馬", key="ann_title")
            content_text = st.text_area("公告內容", height=80, placeholder="輸入公告詳細內容...", key="ann_content")
        with col2:
            ann_type = st.selectbox("公告類型", ["一般", "重要", "緊急"], key="ann_type")
            target_group = st.selectbox("顯示對象", ["全部用戶", "免費用戶", "付費用戶", "VIP"], key="ann_target")
            start_date = st.date_input("開始日期", value=datetime.now().date(), key="ann_start")
            end_date = st.date_input("結束日期（留空 = 永久）", value=None, key="ann_end")
        if st.button("📤 發佈公告", type="primary", key="publish_ann"):
            if not title or not content_text:
                st.warning("請填寫標題同內容")
            else:
                if 'announcements' not in content:
                    content['announcements'] = []
                new_ann = {
                    "id": len(content['announcements']) + 1,
                    "title": title,
                    "content": content_text,
                    "type": ann_type,
                    "target": target_group,
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d') if end_date else None,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "active"
                }
                content['announcements'].append(new_ann)
                save_json(CONTENT_FILE, content)
                log_admin_action(st.session_state.username, f"發佈公告：{title}")
                st.success("✅ 公告已發佈！")
                st.rerun()
    
    st.subheader("📋 現有公告")
    announcements = content.get('announcements', [])
    today = datetime.now().date()
    for ann in announcements:
        if ann.get('status') == 'active' and ann.get('end_date'):
            end = datetime.strptime(ann['end_date'], '%Y-%m-%d').date()
            if end < today:
                ann['status'] = 'expired'
    save_json(CONTENT_FILE, content)
    content = load_json(CONTENT_FILE)
    active_anns = [a for a in content.get('announcements', []) if a.get('status') == 'active']
    
    if active_anns:
        for ann in active_anns:
            type_icon = {"一般": "💡", "重要": "⚠️", "緊急": "🚨"}.get(ann.get('type', '一般'), "💡")
            target_label = ann.get('target', '全部用戶')
            end_display = "永久" if ann.get('end_date') is None else ann.get('end_date')
            col1, col2, col3 = st.columns([5, 3, 1])
            with col1:
                st.markdown(f"**{type_icon} {ann.get('title', '無標題')}**")
                st.caption(ann.get('content', ''))
            with col2:
                st.write(f"🎯 {target_label}")
                st.write(f"📅 {ann.get('start_date', '')} → {end_display}")
            with col3:
                if st.button("🗑️ 刪除", key=f"del_ann_{ann.get('id')}"):
                    ann['status'] = 'deleted'
                    save_json(CONTENT_FILE, content)
                    st.rerun()
            st.divider()
    else:
        st.info("暫時冇生效中嘅公告")
    
    with st.expander("📋 公告歷史（已過期/已刪除）"):
        inactive = [a for a in content.get('announcements', []) if a.get('status') in ['expired', 'deleted']]
        if inactive:
            df = pd.DataFrame(inactive)
            st.dataframe(df[['id', 'title', 'type', 'target', 'start_date', 'end_date', 'status', 'created_at']], use_container_width=True)
        else:
            st.info("暫無歷史記錄")
    
    st.write("---")
    st.write("上傳排位表")
    uploaded = st.file_uploader("選擇 CSV 排位表", type=['csv'], key="upload_racecard")
    if uploaded:
        with open('HKCJ_FULL_YEAR_DATA.csv', 'wb') as f:
            f.write(uploaded.getbuffer())
        st.success("✅ 排位表已更新")

# ---------- 8.9 自動化工具 ----------
def admin_automation():
    st.subheader("🤖 自動化工具")
    auto = load_json(AUTOMATION_FILE)
    days = st.number_input(
        "提前幾天提醒",
        min_value=1,
        value=auto.get('remind_days', 3),
        key="remind_days_auto"
    )
    if st.button("儲存設定", key="save_remind_auto"):
        auto['remind_days'] = days
        save_json(AUTOMATION_FILE, auto)
        st.success("✅ 已儲存")

# ---------- 8.10 安全與權限 ----------
def admin_security():
    st.subheader("🔐 安全與權限")
    st.write("操作日誌")
    logs = load_logs()
    if logs.get('logs'):
        df_log = pd.DataFrame(logs['logs'][-20:])
        st.dataframe(df_log, use_container_width=True)
    st.write("多管理員管理")
    users = load_users()
    admin_list = [u for u, d in users.items() if d.get('group') == 'super_admin']
    st.write("現有超級管理員：", ", ".join(admin_list) if admin_list else "無")
    new_admin = st.text_input("新增超級管理員用戶名", key="new_admin_name")
    if st.button("設為超級管理員", key="add_admin"):
        if new_admin in users:
            users[new_admin]['group'] = 'super_admin'
            users[new_admin]['is_admin'] = True
            users[new_admin]['predictions_limit'] = -1
            save_users(users)
            log_admin_action(st.session_state.username, f"新增超級管理員 {new_admin}")
            st.success(f"✅ {new_admin} 已設為超級管理員")
            st.rerun()
        else:
            st.error("用戶不存在")

# ============================================================
# ---------- 8.11 付款審核 ----------
# ============================================================
def admin_payment_review():
    st.subheader("📤 付款審核")
    
    proofs_data = load_payment_proofs()
    records = proofs_data.get('proof_records', [])
    
    pending = [r for r in records if r.get('status') == 'pending']
    approved = [r for r in records if r.get('status') == 'approved']
    rejected = [r for r in records if r.get('status') == 'rejected']
    total_income = sum(r.get('final_price', 0) for r in approved)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏳ 待審核", len(pending))
    col2.metric("✅ 已批准", len(approved))
    col3.metric("❌ 已拒絕", len(rejected))
    col4.metric("💰 總收入", f"${total_income:.2f}")
    st.divider()
    
    with st.expander("🔍 篩選與搜尋", expanded=True):
        col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
        with col_s1:
            search_term = st.text_input("搜尋用戶名稱", placeholder="輸入用戶名")
        with col_s2:
            status_filter = st.selectbox(
                "狀態篩選",
                ["全部", "pending", "approved", "rejected"],
                format_func=lambda x: {"pending": "待審核", "approved": "已批准", "rejected": "已拒絕", "全部": "全部"}.get(x, x)
            )
        with col_s3:
            if status_filter in ["pending", "全部"] and len(pending) > 0:
                if st.button("📦 批量批准全部待審"):
                    for rec in pending:
                        _approve_payment(rec, proofs_data)
                    st.success(f"✅ 已批量批准 {len(pending)} 條記錄")
                    st.rerun()
    
    filtered = records.copy()
    if search_term:
        filtered = [r for r in filtered if search_term.lower() in r.get('username', '').lower()]
    if status_filter != "全部":
        filtered = [r for r in filtered if r.get('status') == status_filter]
    
    if not filtered:
        st.info("📭 沒有符合條件的記錄")
        return
    
    st.subheader(f"📋 共 {len(filtered)} 條記錄")
    
    for idx, rec in enumerate(filtered):
        original_idx = records.index(rec)
        status = rec.get('status', 'pending')
        username = rec.get('username', '未知')
        
        with st.container():
            cols = st.columns([2, 2, 1.5, 1.5, 2])
            with cols[0]:
                st.write(f"👤 **{username}**")
                st.caption(f"ID: {rec.get('id', '')}")
            with cols[1]:
                plan_name = rec.get('plan_name', '未知方案')
                price = rec.get('final_price', 0)
                st.write(f"📌 {plan_name}")
                st.write(f"💰 ${price:.2f}")
                if rec.get('discount_applied'):
                    st.caption(f"折扣: {rec.get('discount_desc', '')}")
            with cols[2]:
                uploaded_at = rec.get('uploaded_at', '')
                if uploaded_at:
                    try:
                        dt = datetime.fromisoformat(uploaded_at)
                        st.caption(f"📅 {dt.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        st.caption(uploaded_at)
                filename = rec.get('filename')
                if filename:
                    filepath = os.path.join(PAYMENT_PROOFS_DIR, filename)
                    if os.path.exists(filepath):
                        try:
                            image = Image.open(filepath)
                            st.image(image, width=120)
                        except:
                            st.caption("圖片無法載入")
                    else:
                        st.caption("圖片檔案缺失")
            with cols[3]:
                if status == "pending":
                    st.warning("⏳ 待審核")
                elif status == "approved":
                    st.success("✅ 已批准")
                    users = load_users()
                    user_data = users.get(username, {})
                    expiry = user_data.get('expiry_date')
                    if expiry:
                        try:
                            exp_dt = pd.to_datetime(expiry)
                            days_left = (exp_dt - datetime.now()).days
                            st.caption(f"到期: {exp_dt.strftime('%Y-%m-%d')} ({days_left}天)")
                        except:
                            pass
                elif status == "rejected":
                    st.error("❌ 已拒絕")
                else:
                    st.info(status)
                if rec.get('approved_by'):
                    st.caption(f"操作人: {rec['approved_by']}")
                if rec.get('approved_at'):
                    try:
                        dt = datetime.fromisoformat(rec['approved_at'])
                        st.caption(f"操作時間: {dt.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        pass
            with cols[4]:
                if status == "pending":
                    if st.button("✅ 批准", key=f"approve_{original_idx}"):
                        _approve_payment(rec, proofs_data)
                        st.rerun()
                    if st.button("❌ 拒絕", key=f"reject_{original_idx}"):
                        _reject_payment(rec, proofs_data)
                        st.rerun()
                elif status == "approved":
                    if st.button("↩️ 退款", key=f"refund_{original_idx}"):
                        _refund_payment(rec, proofs_data)
                        st.rerun()
                else:
                    st.write("已處理")
            st.divider()
    
    with st.expander("📜 操作日誌 (最近20條)"):
        logs = load_logs()
        log_entries = logs.get('logs', [])[-20:]
        if log_entries:
            for log in reversed(log_entries):
                st.text(f"[{log['time']}] {log['admin']} - {log['action']}")
        else:
            st.info("暫無日誌")


# ---------- 輔助函數 ----------
def _approve_payment(rec, proofs_data):
    try:
        st.info("⏳ 開始處理批准...")
        rec['status'] = 'approved'
        rec['approved_at'] = datetime.now().isoformat()
        rec['approved_by'] = st.session_state.username
        save_payment_proofs(proofs_data)
        st.success("✅ 付款記錄已更新")
        
        username = rec.get('username')
        if not username:
            st.error("❌ 記錄中缺少 username")
            return
        
        users = load_users()
        if username not in users:
            st.error(f"❌ 用戶 {username} 不存在")
            return
        
        plan = rec.get('plan', 'month')
        days = get_plan_days(plan)
        if days == 0:
            days = 30
        expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        users[username]['is_paid'] = True
        users[username]['group'] = 'VIP'
        users[username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        users[username]['expiry_date'] = expiry
        users[username]['plan'] = plan
        users[username]['predictions_limit'] = -1
        
        if save_users(users):
            st.success(f"✅ {username} 已升級為 VIP！")
            st.success(f"📅 到期日：{expiry}")
            log_admin_action(st.session_state.username, f"批准付款並升級 {username} 為 VIP（{plan}）")
        else:
            st.error("❌ 儲存 users.json 失敗")
    except Exception as e:
        st.error(f"❌ 錯誤：{e}")

def _reject_payment(rec, proofs_data):
    rec['status'] = 'rejected'
    rec['approved_at'] = datetime.now().isoformat()
    rec['approved_by'] = st.session_state.username
    save_payment_proofs(proofs_data)
    st.warning(f"❌ 已拒絕 {rec.get('username')} 的申請")
    log_admin_action(st.session_state.username, f"拒絕付款申請：{rec.get('username')}")

def _refund_payment(rec, proofs_data):
    users = load_users()
    username = rec.get('username')
    if username in users:
        users[username]['is_paid'] = False
        users[username]['group'] = 'free'
        users[username]['expiry_date'] = None
        users[username]['plan'] = None
        users[username]['predictions_limit'] = 2
        save_users(users)
        rec['refunded'] = True
        rec['refunded_at'] = datetime.now().isoformat()
        rec['refunded_by'] = st.session_state.username
        save_payment_proofs(proofs_data)
        st.success(f"✅ 已為 {username} 辦理退款，用戶已降級")
        log_admin_action(st.session_state.username, f"退款：{username}")
    else:
        st.error(f"❌ 用戶 {username} 不存在")

# ============================================================
# 9. 後台頁面
# ============================================================
def admin_page():
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔐 後台管理 - 身份驗證")
        st.markdown("請輸入管理員密碼以進入後台")
        admin_pw = st.text_input("管理員密碼", type="password", key="admin_login_pw")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 解鎖後台", type="primary", key="unlock_admin"):
                if admin_pw == CONFIG["admin_password"]:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_username = "admin"
                    log_admin_action("admin", "登入後台")
                    st.success("✅ 密碼正確！")
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤！")
        with col2:
            if st.button("⬅️ 返回主頁", key="back_home_from_admin"):
                st.session_state.show_admin = False
                st.rerun()
        return
    
    st.title("🔐 後台管理")
    st.info(f"👤 超級管理員：{st.session_state.get('admin_username', 'admin')} | 已通過驗證")
    if st.button("🚪 登出後台", key="logout_admin"):
        st.session_state.admin_authenticated = False
        st.session_state.show_admin = False
        st.rerun()
    st.divider()
    
    tabs = st.tabs([
        "👥 用戶管理", 
        "📊 數據分析", 
        "💰 財務", 
        "🎟️ 優惠碼", 
        "📈 預測監控", 
        "⏰ 訂閱管理", 
        "📤 付款審核", 
        "📡 監控", 
        "📝 內容", 
        "🤖 自動化", 
        "🔐 安全"
    ])
    with tabs[0]:
        admin_user_management() if CONFIG["module_user_management"] else st.info("模組已關閉")
    with tabs[1]:
        admin_analytics() if CONFIG["module_analytics"] else st.info("模組已關閉")
    with tabs[2]:
        admin_finance() if CONFIG["module_finance"] else st.info("模組已關閉")
    with tabs[3]:
        admin_promo_codes() if CONFIG["module_promo"] else st.info("模組已關閉")
    with tabs[4]:
        admin_accuracy_monitor()
    with tabs[5]:
        admin_subscription()
    with tabs[6]:
        admin_payment_review()
    with tabs[7]:
        admin_monitoring() if CONFIG["module_monitoring"] else st.info("模組已關閉")
    with tabs[8]:
        admin_content() if CONFIG["module_content"] else st.info("模組已關閉")
    with tabs[9]:
        admin_automation() if CONFIG["module_automation"] else st.info("模組已關閉")
    with tabs[10]:
        admin_security() if CONFIG["module_security"] else st.info("模組已關閉")

# ============================================================
# 10. 主頁面
# ============================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = 'free'
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False

    # 公告
    content = load_json(CONTENT_FILE)
    announcements = content.get('announcements', [])
    today = datetime.now().date()
    active_anns = []
    for ann in announcements:
        if ann.get('status') != 'active':
            continue
        start = datetime.strptime(ann['start_date'], '%Y-%m-%d').date()
        if start > today:
            continue
        end = ann.get('end_date')
        if end:
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
            if end_date < today:
                continue
        target = ann.get('target', '全部用戶')
        if target != '全部用戶':
            if not st.session_state.get('logged_in', False):
                continue
            user = load_users().get(st.session_state.username, {})
            group = user.get('group', 'free')
            if target == '付費用戶' and group not in ['paid', 'VIP', 'super_admin']:
                continue
            if target == 'VIP' and group not in ['VIP', 'super_admin']:
                continue
            if target == '免費用戶' and group != 'free':
                continue
        active_anns.append(ann)

    for ann in active_anns:
        ann_type = ann.get('type', '一般')
        if ann_type == '緊急':
            st.error(f"🚨 {ann['title']}：{ann['content']}")
        elif ann_type == '重要':
            st.warning(f"⚠️ {ann['title']}：{ann['content']}")
        else:
            st.info(f"💡 {ann['title']}：{ann['content']}")

    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        return

    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("🏇 賽馬預測系統")
        st.markdown("AI 驅動・即時預測・彩池推薦")
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')} · 36個特徵 · 三模型融合 · 六種彩池")
    with col2:
        if CONFIG["enable_admin"] and st.session_state.get("role") == "super_admin":
            if st.button("🔐 後台", use_container_width=True, key="go_to_admin"):
                st.session_state.show_admin = True
                st.session_state.admin_authenticated = False
                st.rerun()

    if CONFIG["enable_registration"] and st.session_state.logged_in:
        show_user_dashboard(st.session_state.username)
    elif not CONFIG["enable_registration"]:
        st.info("🔓 目前為公開模式，任何人皆可使用")

    with st.sidebar:
        st.header("🎯 控制面板")
        if CONFIG["enable_registration"] and st.session_state.logged_in:
            st.write(f"👤 用戶：{st.session_state.username}")
            users = load_users()
            user_data = users.get(st.session_state.username, {})
            limit = user_data.get('predictions_limit', CONFIG['free_limit'])
            if limit == -1:
                st.success("♾️ 無限預測次數")
            else:
                used = user_data.get('free_usage', 0)
                remain = max(0, limit - used)
                st.info(f"📊 剩餘免費場次：{remain} 場")
            if st.button("📋 我的預測記錄", key="show_history_btn"):
                st.session_state.show_history = not st.session_state.show_history
            if st.button("🚪 登出", key="logout_btn"):
                for key in ['logged_in', 'username', 'role', 'usage_count', 'show_history']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        date = st.date_input("📅 選擇日期", value=pd.to_datetime("2025-04-09"), key="predict_date")
        race_no = st.selectbox("🏇 選擇場次", list(range(1, 12)), index=8, key="predict_race")
        predict_btn = st.button("🚀 執行預測", type="primary", use_container_width=True, key="predict_btn")

    if CONFIG["enable_registration"] and st.session_state.logged_in and st.session_state.get('show_history', False):
        st.subheader("📋 我的預測記錄")
        show_prediction_history(st.session_state.username)
        st.divider()

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
    except:
        st.info("今日沒有賽事")

    if predict_btn:
        users = load_users()
        user_data = users.get(st.session_state.username, {})
        limit = user_data.get('predictions_limit', CONFIG['free_limit'])
        used = user_data.get('free_usage', 0)
        
        if limit == -1 or used < limit:
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

                    if CONFIG["enable_registration"] and st.session_state.logged_in:
                        winner_name = result.iloc[0]['馬匹名稱'] if not result.empty else "未知"
                        prob = result.iloc[0]['預測勝率'] if not result.empty else None
                        record_prediction(st.session_state.username, date_str, race_no, winner_name, prob)
                        users = load_users()
                        if st.session_state.username in users:
                            users[st.session_state.username]['free_usage'] = users[st.session_state.username].get('free_usage', 0) + 1
                            users[st.session_state.username]['total_usage'] = users[st.session_state.username].get('total_usage', 0) + 1
                            save_users(users)
                        st.session_state.usage_count += 1
                        st.info("📝 預測已記錄到你的歷史")
        else:
            show_paywall()

    st.divider()
    st.caption(f"🕐 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🔐 數據來源：HKJC | 系統版本：v14.0-用戶體驗版")

if __name__ == '__main__':
    main()
