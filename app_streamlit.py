#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
賽馬預測系統 - 預測控制置中版
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
# 🔒 隱藏 Streamlit 平台 UI（加強版，連 Manage app 都遮）
# ============================================================
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None,
    }
)

st.markdown("""
<style>
    div[data-testid="stToolbar"] { display: none !important; }
    .stAppDeployButton { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    button[kind="share"] { display: none !important; }
    a[href*="streamlit.io"] { display: none !important; }
    .st-emotion-cache-1r6slb0 { display: none !important; }
    .st-emotion-cache-1v3caq0 { display: none !important; }
    .st-emotion-cache-1v0mbdj { display: none !important; }
    .st-emotion-cache-1dp5vir { display: none !important; }
    .st-emotion-cache-1q8dd3e { display: none !important; }
    .st-emotion-cache-1v3fvcr { display: none !important; }
    .st-emotion-cache-1wmy9hl { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    .stApp > header { display: none !important; }
    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 280px !important;
    }
    section[data-testid="stSidebar"] * {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    .stApp > header + div {
        padding-top: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔐 系統設定（動態載入）
# ============================================================
CONFIG_FILE = 'system_config.json'

DEFAULT_CONFIG = {
    "enable_registration": True,
    "enable_payment": True,
    "enable_admin": True,
    "currency": "HKD",
    "free_limit": 2,
    "admin_password": "z54060437K",
    "price_day": 18,
    "price_month": 128,
    "price_quarter": 328,
    "verification_expiry": 5,
    "enable_vip_content": True,
    "enable_daily_free_tip": True,
    "enable_invite_reward": True,
    "invite_reward_inviter": 1,
    "invite_reward_invitee": 1,
    "module_user_management": True,
    "module_analytics": True,
    "module_finance": True,
    "module_monitoring": True,
    "module_content": True,
    "module_automation": True,
    "module_security": True,
    "module_promo": True,
}

def load_system_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except:
            return DEFAULT_CONFIG.copy()
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_CONFIG.copy()

def save_system_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

CONFIG = load_system_config()

# ============================================================
# 2. 數據讀寫函數
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
        except:
            return {}
    return {}

def save_json(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
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
                "history": [],
                "terms_agreed": datetime.now().isoformat(),
                "invite_code": "ADMIN001",
                "invited_by": None,
                "invite_rewards": 0,
                "invite_count": 0
            }
        }
        save_users(users)
    else:
        if "admin" in users:
            users["admin"]["group"] = "super_admin"
            users["admin"]["predictions_limit"] = -1
            if users["admin"].get("note") != "系統超級管理員":
                users["admin"]["note"] = "系統超級管理員（已自動修復）"
        for uid, u in users.items():
            if 'plan' not in u: u['plan'] = None
            if 'paid_date' not in u: u['paid_date'] = None
            if 'expiry_date' not in u: u['expiry_date'] = None
            if 'phone' not in u: u['phone'] = ''
            if 'note' not in u: u['note'] = ''
            if 'history' not in u: u['history'] = []
            if 'free_usage' not in u: u['free_usage'] = 0
            if 'total_usage' not in u: u['total_usage'] = 0
            if 'terms_agreed' not in u: u['terms_agreed'] = None
            if 'invite_code' not in u:
                u['invite_code'] = uid.upper() + str(random.randint(100, 999))
            if 'invited_by' not in u: u['invited_by'] = None
            if 'invite_rewards' not in u: u['invite_rewards'] = 0
            if 'invite_count' not in u: u['invite_count'] = 0
            if 'predictions_limit' not in u:
                if u.get('group') in ['super_admin', 'VIP', 'paid']:
                    u['predictions_limit'] = -1
                else:
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
    except:
        st.error("❌ 模型載入失敗")
        return None, None, None

# ============================================================
# 4. 特徵工程（36 特徵）
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
    except:
        st.error("讀取排位表失敗")
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
    invite_code = user_data.get('invite_code', '')
    invite_count = user_data.get('invite_count', 0)
    invite_rewards = user_data.get('invite_rewards', 0)
    
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
    
    if CONFIG.get("enable_invite_reward", True):
        st.markdown("---")
        st.subheader("🎁 邀請獎勵")
        col_inv1, col_inv2, col_inv3 = st.columns(3)
        with col_inv1:
            st.caption(f"你的邀請碼：**{invite_code}**")
        with col_inv2:
            st.caption(f"已成功邀請 **{invite_count}** 位朋友")
        with col_inv3:
            st.caption(f"已獲得獎勵次數：**{invite_rewards}** 次（已自動加到你的預測額度）")
    
    st.markdown("---")
    st.subheader("📊 預測統計")
    today = datetime.now().strftime('%Y-%m-%d')
    history = user_data.get('history', [])
    today_count = sum(1 for h in history if h.get('date') == today)
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        st.metric("📈 總預測", stats['total_predictions'])
    with col_p2:
        st.metric("📅 今日已用", today_count)
    with col_p3:
        if limit == -1:
            st.metric("🔮 剩餘次數", "♾️ 無限")
        else:
            remain = max(0, limit - user_data.get('free_usage', 0))
            st.metric("🔮 剩餘次數", remain)
    with col_p4:
        if st.button("🚀 去預測", use_container_width=True, key="quick_predict"):
            st.session_state.page = "預測"
            st.rerun()
    
    if today_count > 0:
        st.caption(f"📝 今日已進行 {today_count} 次預測")
    else:
        st.caption("📝 今日尚未進行預測")

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
            
            if CONFIG.get("enable_invite_reward", True):
                invite_code_input = st.text_input("邀請碼（如有）", key="reg_invite_code", placeholder="輸入朋友的邀請碼")
            else:
                invite_code_input = None
            
            col1, col2 = st.columns([3, 1])
            with col1:
                verify_code_input = st.text_input("驗證碼", key="reg_verify", placeholder="輸入 6 位數字", max_chars=6)
            with col2:
                if st.form_submit_button("📨 獲取驗證碼", type="secondary"):
                    code = generate_verification_code()
                    st.session_state['reg_verify_code'] = code
                    st.session_state['reg_verify_expiry'] = datetime.now() + timedelta(minutes=CONFIG.get('verification_expiry', 5))
                    st.info(f"📧 你嘅驗證碼係：**{code}**（有效期 5 分鐘）")
            
            st.divider()
            with st.expander("📜 服務條款（請仔細閱讀）"):
                st.markdown("""
                **SHTSN 賽馬預測系統 服務條款**

                **1. 服務說明**
                本系統提供賽馬預測數據及分析，僅供參考及娛樂用途，並非投注建議。用戶應自行判斷，所有投注決定及後果由用戶自行承擔。

                **2. 用戶責任**
                - 用戶必須年滿 18 歲。
                - 用戶需確保所提供嘅資料真實、準確、完整。
                - 用戶不得將本系統用於任何非法或不當用途。

                **3. 免責聲明**
                - 預測結果僅為演算法分析，不構成任何形式嘅投資建議或保證。
                - 本系統不保證預測準確度，亦不對用戶因使用本系統而產生嘅任何損失負責。
                - 用戶明白賽馬活動存在風險，應量力而為。

                **4. 付款與退款**
                - 用戶付款後即表示同意購買所選方案。
                - 付款後不設退款，除非系統因技術問題未能提供服務。
                - 管理員保留最終審核及拒絕退款嘅權利。

                **5. 帳戶安全**
                - 用戶需自行保管帳號及密碼，任何經由帳戶進行嘅活動均視為用戶本人所為。
                - 如發現帳戶被盜用，應立即通知管理員。

                **6. 終止服務**
                - 管理員保留隨時終止或暫停用戶帳戶嘅權利，如用戶違反條款或進行不當行為。
                - 終止後，用戶將無法使用系統服務，已付費用將不獲退還。

                **7. 條款修訂**
                本系統有權隨時修訂服務條款，修訂後會於系統內公告。用戶繼續使用即表示同意最新條款。

                **8. 聯絡我們**
                如有任何疑問，可透過 Telegram 聯絡管理員：@bryhjdjbrbxibvrjskofndhiebdpaq

                **最後更新日期：2026 年 8 月 25 日**
                """)
            
            agree_terms = st.checkbox("✅ 我已閱讀並同意上述服務條款", key="agree_terms")
            
            submitted = st.form_submit_button("註冊")
            
            if submitted:
                if len(new_user) < 3:
                    st.error("❌ 用戶名稱至少 3 個字")
                elif new_pass != new_pass2:
                    st.error("❌ 密碼不一致")
                elif len(new_pass) < 4:
                    st.error("❌ 密碼至少 4 個字")
                elif 'reg_verify_code' not in st.session_state or \
                     verify_code_input != st.session_state['reg_verify_code'] or \
                     datetime.now() > st.session_state.get('reg_verify_expiry', datetime.now()):
                    st.error("❌ 驗證碼無效或已過期，請重新獲取")
                elif not agree_terms:
                    st.error("❌ 請先閱讀並同意服務條款，方可註冊")
                else:
                    users = load_users()
                    if new_user in users:
                        st.error("❌ 用戶名稱已被使用")
                    else:
                        invited_by = None
                        if CONFIG.get("enable_invite_reward", True) and invite_code_input:
                            for uid, u in users.items():
                                if u.get('invite_code') == invite_code_input:
                                    invited_by = uid
                                    break
                            if not invited_by:
                                st.warning("⚠️ 邀請碼無效，請確認後再試。")
                        
                        new_user_data = {
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
                            'history': [],
                            'terms_agreed': datetime.now().isoformat(),
                            'invite_code': new_user.upper() + str(random.randint(100, 999)),
                            'invited_by': invited_by,
                            'invite_rewards': 0,
                            'invite_count': 0
                        }
                        users[new_user] = new_user_data
                        save_users(users)
                        
                        if CONFIG.get("enable_invite_reward", True) and invited_by:
                            inviter = users.get(invited_by)
                            if inviter:
                                reward_inviter = CONFIG.get("invite_reward_inviter", 1)
                                reward_invitee = CONFIG.get("invite_reward_invitee", 1)
                                if inviter['predictions_limit'] != -1:
                                    inviter['predictions_limit'] += reward_inviter
                                inviter['invite_count'] = inviter.get('invite_count', 0) + 1
                                inviter['invite_rewards'] = inviter.get('invite_rewards', 0) + reward_inviter
                                if new_user_data['predictions_limit'] != -1:
                                    new_user_data['predictions_limit'] += reward_invitee
                                new_user_data['invite_rewards'] = reward_invitee
                                save_users(users)
                                st.success(f"✅ 註冊成功！你同邀請人各獲得 {reward_invitee} 次免費預測獎勵！")
                            else:
                                st.success("✅ 註冊成功！")
                        else:
                            st.success("✅ 註冊成功！")
                        st.rerun()

# ============================================================
# 🔧 付款牆
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
        st.info("📩 提交後請 Telegram 通知管理員（可加快審核）")
        st.markdown("💬 Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**")
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
            if not st.session_state.get('logged_in', False):
                st.error("❌ 請先登入")
                st.stop()
            
            original_price = get_plan_price(plan_choice)
            final_price = original_price
            discount_applied = False
            discount_desc = ""
            promo_code_used = None
            
            if promo_input:
                try:
                    promos = load_promos()
                    promo_data = promos.get(promo_input)
                    if promo_data and not promo_data.get('used', False):
                        expiry = promo_data.get('expiry')
                        if expiry:
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
# 8. 後台所有模組（完整）
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
                        "history": [],
                        "terms_agreed": datetime.now().isoformat(),
                        "invite_code": new_username.upper() + str(random.randint(100, 999)),
                        "invited_by": None,
                        "invite_rewards": 0,
                        "invite_count": 0
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
           
