#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""賽馬預測系統 v16.0 - 完整可用版"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import random
import time
from datetime import datetime, timedelta
import pytz
import warnings
import requests
import re
warnings.filterwarnings('ignore')

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

SUPABASE_URL = "https://fewanagxvezelufmuggq.supabase.co"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"

st.markdown("""
<style>
    div[data-testid="stToolbar"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
</style>
""", unsafe_allow_html=True)
CONFIG_FILE = 'system_config.json'
DEFAULT_CONFIG = {
    "enable_registration": True,
    "enable_payment": True,
    "enable_admin": True,
    "enable_lottery": True,
    "enable_shop": True,
    "currency": "HKD",
    "free_limit": 10,
    "admin_password": "z54060437K",
    "price_day": 18,
    "price_month": 128,
    "price_quarter": 328,
    "daily_virtual_coin": 1000,
    "virtual_coin_enabled": True,
    "session_timeout_minutes": 60,
    "enable_invite_reward": True,
    "invite_rewards": {
        "level1": 5,
        "level2": 2,
        "level3": 1
    },
    "pool_config": {
        "win": {"enabled": True, "required_group": "free", "label": "獨贏"},
        "place": {"enabled": True, "required_group": "free", "label": "位置"},
        "quinella": {"enabled": True, "required_group": "free", "label": "連贏"},
        "quinella_place": {"enabled": True, "required_group": "free", "label": "位置Q"},
        "tierce": {"enabled": True, "required_group": "paid", "label": "三重彩"},
        "trio": {"enabled": True, "required_group": "paid", "label": "單T"},
        "quartet": {"enabled": True, "required_group": "VIP", "label": "四重彩"},
        "exacta": {"enabled": True, "required_group": "VIP", "label": "二重彩"},
        "first4": {"enabled": True, "required_group": "VIP", "label": "四連環"},
        "double": {"enabled": True, "required_group": "VIP", "label": "孖寶"},
        "treble": {"enabled": True, "required_group": "VIP", "label": "三寶"},
        "six_up": {"enabled": True, "required_group": "VIP", "label": "六環彩"}
    }
}

def load_json(fp, default=None):
    if default is None:
        default = {}
    if os.path.exists(fp):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(fp, data):
    try:
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_system_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception:
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
    except Exception:
        return False

CONFIG = load_system_config()

USER_DATA_FILE = 'users.json'
FINANCE_FILE = 'finance.json'
PROMO_FILE = 'promo_codes.json'
LOG_FILE = 'admin_log.json'
ACCURACY_FILE = 'accuracy.json'
CONTENT_FILE = 'content.json'
PAYMENT_PROOFS_FILE = 'payment_proofs.json'
LOTTERY_FILE = 'lottery_config.json'
SHOP_FILE = 'shop_config.json'

def load_users():
    users = load_json(USER_DATA_FILE)
    if not users or "admin" not in users:
        users = {
            "admin": {
                "username": "admin",
                "password": CONFIG.get("admin_password", "z54060437K"),
                "group": "super_admin",
                "is_paid": True,
                "predictions_limit": -1,
                "free_usage": 0,
                "total_usage": 0,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "history": [],
                "badges": [],
                "level": "👑 超級管理員",
                "exp": 0,
                "virtual_balance": 10000,
                "last_claim_date": "",
                "last_lottery_date": "",
                "invite_code": "ADMIN001",
                "invite_count": 0,
                "invite_rewards": 0,
                "phone": "",
                "note": "系統超級管理員",
                "plan": None,
                "paid_date": None,
                "expiry_date": None,
                "terms_agreed": datetime.now().isoformat(),
                "bets": [],
            }
        }
        save_users(users)
    else:
        for uid, u in users.items():
            defaults = {
                'plan': None, 'paid_date': None, 'expiry_date': None,
                'phone': '', 'note': '', 'history': [], 'free_usage': 0,
                'total_usage': 0, 'terms_agreed': None, 'invited_by': None,
                'invite_rewards': 0, 'invite_count': 0,
                'level': '🥉 銅牌會員', 'exp': 0, 'badges': [],
                'virtual_balance': 1000, 'last_claim_date': '',
                'bets': [], 'last_lottery_date': ''
            }
            for k, v in defaults.items():
                if k not in u:
                    u[k] = v
            if 'invite_code' not in u:
                u['invite_code'] = uid.upper() + str(random.randint(100, 999))
            if 'predictions_limit' not in u:
                if u.get('group') in ['super_admin', 'VIP', 'paid']:
                    u['predictions_limit'] = -1
                else:
                    u['predictions_limit'] = CONFIG.get("free_limit", 10)
        save_users(users)
    return users

def save_users(users):
    return save_json(USER_DATA_FILE, users)

def authenticate(username, password):
    users = load_users()
    if username in users and users[username].get('password') == password:
        return users[username]
    return None

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
def log_user_activity(username, action, detail=""):
    """記錄用戶活動"""
    log_file = "user_activity_log.json"
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = {"records": []}
    except Exception:
        logs = {"records": []}

    if "records" not in logs:
        logs["records"] = []

    logs["records"].append({
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "username": username,
        "action": action,
        "detail": detail
    })

    # 只保留最近 5000 條
    logs["records"] = logs["records"][-5000:]

    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_finance():
    return load_json(FINANCE_FILE)

def save_finance(f):
    return save_json(FINANCE_FILE, f)

def load_promos():
    return load_json(PROMO_FILE)

def save_promos(p):
    return save_json(PROMO_FILE, p)

def load_accuracy():
    return load_json(ACCURACY_FILE)

def save_accuracy(a):
    return save_json(ACCURACY_FILE, a)

def load_payment_proofs():
    return load_json(PAYMENT_PROOFS_FILE)

def save_payment_proofs(d):
    return save_json(PAYMENT_PROOFS_FILE, d)

def load_lottery_config():
    default_config = {
        "prizes": [
            {"name": "100 虛擬幣", "type": "virtual_coin", "value": 100, "weight": 5, "description": "送 100 虛擬幣"},
            {"name": "500 虛擬幣", "type": "virtual_coin", "value": 500, "weight": 2, "description": "送 500 虛擬幣"},
            {"name": "1000 虛擬幣", "type": "virtual_coin", "value": 1000, "weight": 1, "description": "送 1000 虛擬幣"},
            {"name": "VIP 1 天", "type": "vip_days", "value": 1, "weight": 10, "description": "1 天 VIP 體驗"},
            {"name": "免費預測 3 次", "type": "free_predictions", "value": 3, "weight": 20, "description": "額外 3 次預測"},
            {"name": "20% 折扣優惠碼", "type": "promo_code", "value": 20, "weight": 10, "description": "購物 8 折"},
            {"name": "謝謝參與", "type": "nothing", "value": 0, "weight": 30, "description": "下次再嚟"}
        ]
    }
    
    if os.path.exists("lottery_config.json"):
        try:
            with open("lottery_config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            if config.get("prizes"):
                return config
        except Exception:
            pass
            
    # 如果檔案唔存在、讀取失敗或者係空嘅，就寫入預設值
    with open("lottery_config.json", "w", encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    return default_config
    return save_json(LOTTERY_FILE, c)

def load_shop_config():
    """從 Supabase 讀取商城商品"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/shop_config?order=id.asc", headers=headers)
        if res.status_code == 200:
            items = res.json()
            if items:
                return {"items": items}
    except Exception as e:
        print(f"讀取商城失敗: {e}")

    # 如果 Supabase 冇數據，返回預設 3 件商品做後備
    return {
        "items": [
            {"name": "額外 5 次預測", "type": "predictions", "price": 500, "stock": 100, "description": "增加 5 次預測機會"},
            {"name": "VIP 7 天體驗", "type": "vip_days", "price": 3000, "stock": 50, "description": "7 天 VIP 權限"},
            {"name": "神秘盲盒", "type": "mystery_box", "price": 1000, "stock": 20, "description": "隨機獲得獎品"}
        ]
    }
def save_shop_config(c):
    return save_json(SHOP_FILE, c)

def generate_promo_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))

def get_plan_days(plan):
    return {'day': 1, 'month': 30, 'quarter': 90}.get(plan, 0)

def get_plan_name(plan):
    return {'day': '日費', 'month': '月費', 'quarter': '季費'}.get(plan, '未知')

def get_plan_price(plan):
    return {'day': CONFIG['price_day'], 'month': CONFIG['price_month'], 'quarter': CONFIG['price_quarter']}.get(plan, 0)

def _safe_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default

def submit_payment_request(username, plan, final_price, discount_desc, promo_code_used):
    proof = load_payment_proofs()
    if 'proof_records' not in proof:
        proof['proof_records'] = []
    new_id = len(proof['proof_records']) + 1
    proof['proof_records'].append({
        "id": new_id, "username": username, "plan": plan,
        "plan_name": get_plan_name(plan), "final_price": final_price,
        "discount_desc": discount_desc, "promo_code": promo_code_used,
        "submitted_at": datetime.now().isoformat(), "status": "pending"
    })
    save_payment_proofs(proof)
    return True, "申請已提交"

def get_all_pending_requests():
    proof = load_payment_proofs()
    return [
        {"username": r.get('username', ''), "request": r}
        for r in proof.get('proof_records', [])
        if r.get('status') == 'pending'
    ]

def approve_payment_request(username, request_id, admin_username):
    proof = load_payment_proofs()
    for req in proof.get('proof_records', []):
        if req.get('id') == request_id and req.get('status') == 'pending':
            users = load_users()
            if username in users:
                plan = req.get('plan', 'month')
                days = get_plan_days(plan) or 30
                expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
                users[username]['is_paid'] = True
                users[username]['group'] = 'VIP'
                users[username]['paid_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                users[username]['expiry_date'] = expiry
                users[username]['plan'] = plan
                users[username]['predictions_limit'] = -1
                save_users(users)
                req['status'] = 'approved'
                req['approved_by'] = admin_username
                req['approved_at'] = datetime.now().isoformat()
                save_payment_proofs(proof)
                return True, f"已批准 {username}，到期日 {expiry}"
            return False, "用戶不存在"
    return False, "找不到該申請"

def reject_payment_request(username, request_id, admin_username):
    proof = load_payment_proofs()
    for req in proof.get('proof_records', []):
        if req.get('id') == request_id and req.get('status') == 'pending':
            req['status'] = 'rejected'
            req['rejected_by'] = admin_username
            req['rejected_at'] = datetime.now().isoformat()
            save_payment_proofs(proof)
            return True, "已拒絕該申請"
    return False, "找不到該申請"

def generate_pool_recommendations(df, user_group='free'):
    """生成彩池推薦（按會員級別 + 每個彩池只出一個組合）"""
    if df.empty:
        return "⚠️ 無數據"

    config = load_system_config()
    pool_config = config.get('pool_config', {})

    if not pool_config:
        pool_config = {
            "win": {"enabled": True, "required_group": "free", "label": "獨贏"},
            "place": {"enabled": True, "required_group": "free", "label": "位置"},
            "quinella": {"enabled": True, "required_group": "free", "label": "連贏"},
            "quinella_place": {"enabled": True, "required_group": "free", "label": "位置Q"},
            "tierce": {"enabled": True, "required_group": "paid", "label": "三重彩"},
            "trio": {"enabled": True, "required_group": "paid", "label": "單T"},
            "quartet": {"enabled": True, "required_group": "VIP", "label": "四重彩"},
            "exacta": {"enabled": True, "required_group": "VIP", "label": "二重彩"},
            "first4": {"enabled": True, "required_group": "VIP", "label": "四連環"},
            "double": {"enabled": True, "required_group": "VIP", "label": "孖寶"},
            "treble": {"enabled": True, "required_group": "VIP", "label": "三寶"},
            "six_up": {"enabled": True, "required_group": "VIP", "label": "六環彩"},
        }

    group_levels = {'free': 0, 'paid': 1, 'VIP': 2, 'super_admin': 99}
    user_level = group_levels.get(user_group, 0)

    df_sorted = df.sort_values('預測勝率', ascending=False).reset_index(drop=True)
    names = df_sorted['馬名'].tolist()
    probs = df_sorted['預測勝率'].tolist()

    def get_win():
        if len(names) >= 1:
            return f"  {names[0]}（{probs[0]:.1%}）"
        return ""

    def get_place():
        if len(names) >= 2:
            return f"  {names[0]}（{probs[0]:.1%}）+ {names[1]}（{probs[1]:.1%}）"
        elif len(names) >= 1:
            return f"  {names[0]}（{probs[0]:.1%}）"
        return ""

    def get_quinella():
        if len(names) >= 2:
            return f"  {names[0]} + {names[1]}"
        return ""

    def get_quinella_place():
        if len(names) >= 2:
            return f"  {names[0]} + {names[1]}"
        return ""

    def get_tierce():
        if len(names) >= 3:
            return f"  {names[0]} > {names[1]} > {names[2]}"
        return ""

    def get_trio():
        if len(names) >= 3:
            return f"  {names[0]} + {names[1]} + {names[2]}"
        return ""

    def get_quartet():
        if len(names) >= 4:
            return f"  {names[0]} > {names[1]} > {names[2]} > {names[3]}"
        return ""

    def get_exacta():
        if len(names) >= 2:
            return f"  {names[0]} > {names[1]}"
        return ""

    def get_first4():
        if len(names) >= 4:
            return f"  {names[0]} + {names[1]} + {names[2]} + {names[3]}"
        return ""

    def get_double():
        return "  ⚠️ 需要 2 場賽事數據（孖寶）"

    def get_treble():
        return "  ⚠️ 需要 3 場賽事數據（三寶）"

    def get_six_up():
        return "  ⚠️ 需要 6 場賽事數據（六環彩）"

    generators = {
        'win': get_win, 'place': get_place, 'quinella': get_quinella,
        'quinella_place': get_quinella_place, 'tierce': get_tierce,
        'trio': get_trio, 'quartet': get_quartet, 'exacta': get_exacta,
        'first4': get_first4, 'double': get_double, 'treble': get_treble,
        'six_up': get_six_up,
    }

    rec_lines = []
    for key, cfg in pool_config.items():
        if not cfg.get('enabled', True):
            continue
        required = cfg.get('required_group', 'free')
        if user_level < group_levels.get(required, 0):
            rec_lines.append(f"【{cfg.get('label', key)}】🔒 需要更高級會員")
            continue
        gen = generators.get(key)
        if gen:
            content = gen()
            if content:
                rec_lines.append(f"【{cfg.get('label', key)}】\n{content}")

    if not rec_lines:
        return "⚠️ 所有彩池已關閉或未開放"
    return "\n\n".join(rec_lines)

    return "\n\n".join(rec_lines)
    for _, i, j, k, l in qt[:3]:
        rec += f"  {names[i]} > {names[j]} > {names[k]} > {names[l]}\n"

    return rec

@st.cache_resource
def load_ml_models():
    """載入 XGBoost + CatBoost + Ranking 模型"""
    import pickle
    xgb_model = None
    cat_model = None
    rank_model = None

    try:
        with open('hk_racing_model.pkl', 'rb') as f:
            obj = pickle.load(f)
            xgb_model = obj[0] if isinstance(obj, tuple) else obj
    except Exception as e:
        print(f"XGBoost 載入失敗：{e}")

    try:
        from catboost import CatBoostClassifier
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
    except Exception as e:
        print(f"CatBoost 載入失敗：{e}")

    try:
        with open('hk_ranking_model.pkl', 'rb') as f:
            obj = pickle.load(f)
            rank_model = obj[0] if isinstance(obj, tuple) else obj
    except Exception as e:
        print(f"Ranking 載入失敗：{e}")

    return xgb_model, cat_model, rank_model


def _build_features(race_df, history_df):
    """為排位表每匹馬計算特徵"""
    import numpy as np

    history_df = history_df.copy()
    history_df['race_date'] = pd.to_datetime(history_df['race_date'], errors='coerce')
    history_df = history_df.dropna(subset=['race_date'])
    history_df['finish_position'] = pd.to_numeric(history_df['finish_position'], errors='coerce')
    history_df = history_df.dropna(subset=['finish_position'])

    result = race_df.copy()

    # ========================================================
    # 🛡️ 智能馬名對照：用中文馬名去匹配 horse_id
    # ========================================================
    mapping_file = "horse_name_mapping_cn.csv"
    if os.path.exists(mapping_file):
        try:
            mapping_df = pd.read_csv(mapping_file, encoding='utf-8-sig')
            mapping_df.columns = [str(c).replace('\ufeff', '').strip() for c in mapping_df.columns]

            if 'horse_name_cn' in mapping_df.columns and 'horse_id' in mapping_df.columns:
                def normalize_name(name):
                    if pd.isna(name):
                        return ''
                    name = str(name).strip()
                    name = re.sub(r'[\(（].*?[\)）]', '', name)
                    name = name.replace(' ', '').replace('\u3000', '')
                    name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', name)
                    return name

                # 用中文名做 key
                mapping_df['norm_name'] = mapping_df['horse_name_cn'].apply(normalize_name)
                mapping_df = mapping_df.dropna(subset=['norm_name'])
                mapping_df = mapping_df[mapping_df['norm_name'] != '']

                mapping_dict = dict(zip(
                    mapping_df['norm_name'],
                    mapping_df['horse_id'].astype(str).str.strip()
                ))

                if 'horse_name' in result.columns:
                    result['norm_name'] = result['horse_name'].apply(normalize_name)
                    mapped_ids = result['norm_name'].map(mapping_dict)
                    result['horse_id'] = mapped_ids.fillna(result['horse_id']).astype(str).str.strip()
                    result = result.drop(columns=['norm_name'], errors='ignore')

                    matched = mapped_ids.notna().sum()
                    total = len(result)
                    st.success(f"✅ 馬名對照：成功匹配 {matched}/{total} 匹馬")
        except Exception as e:
            st.warning(f"⚠️ 加載馬名對照表失敗：{e}")

    feature_cols = [
        'draw', 'weight', 'distance', 'Rtg.', 'avg_rank_last3',
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
    for c in feature_cols:
        if c not in result.columns:
            result[c] = 0.0

    # 填充基本欄位
    if 'draw' in race_df.columns:
        result['draw'] = pd.to_numeric(race_df['draw'], errors='coerce').fillna(0)
    if 'weight' in race_df.columns:
        result['weight'] = pd.to_numeric(race_df['weight'], errors='coerce').fillna(0)
    if 'distance' in race_df.columns:
        result['distance'] = pd.to_numeric(race_df['distance'], errors='coerce').fillna(0)
    if 'rtg' in race_df.columns:
        result['Rtg.'] = pd.to_numeric(race_df['rtg'], errors='coerce').fillna(0)
    if 'win_odds' in race_df.columns:
        result['win_odds'] = pd.to_numeric(race_df['win_odds'], errors='coerce').fillna(0)

    # 賠率排名
    if 'win_odds' in result.columns:
        result['odds_rank_in_race'] = result['win_odds'].rank(method='min', ascending=True).fillna(0)

    # 歷史統計
    if not history_df.empty:
        # 騎師勝率
        if 'jockey' in history_df.columns and 'jockey' in result.columns:
            jockey_stats = history_df.groupby('jockey').apply(
                lambda g: (g['finish_position'] == 1).sum() / max(len(g), 1)
            ).to_dict()
            result['jockey_win_rate_50'] = result['jockey'].map(jockey_stats).fillna(0)

        # 練馬師勝率
        if 'trainer' in history_df.columns and 'trainer' in result.columns:
            trainer_stats = history_df.groupby('trainer').apply(
                lambda g: (g['finish_position'] == 1).sum() / max(len(g), 1)
            ).to_dict()
            result['trainer_win_rate_50'] = result['trainer'].map(trainer_stats).fillna(0)

        # 馬匹近3場平均名次
        if 'horse_id' in history_df.columns and 'horse_id' in result.columns:
            def _avg3(g):
                g = g.sort_values('race_date').tail(3)
                return g['finish_position'].mean() if len(g) > 0 else 99
            avg3 = history_df.groupby('horse_id').apply(_avg3).to_dict()
            result['avg_rank_last3'] = result['horse_id'].map(avg3).fillna(99)

            # 馬匹同路程勝率
            if 'distance' in history_df.columns and 'distance' in result.columns:
                def _dist_win(row):
                    sub = history_df[(history_df['horse_id'] == row['horse_id']) &
                                     (history_df['distance'] == row['distance'])]
                    return 0 if len(sub) == 0 else (sub['finish_position'] == 1).sum() / len(sub)
                result['distance_win_rate'] = result.apply(_dist_win, axis=1)

            # 騎練組合勝率
            if 'jockey' in history_df.columns and 'trainer' in history_df.columns:
                def _jt_win(row):
                    sub = history_df[(history_df['jockey'] == row['jockey']) &
                                     (history_df['trainer'] == row['trainer'])]
                    return 0 if len(sub) == 0 else (sub['finish_position'] == 1).sum() / len(sub)
                result['jockey_trainer_win_rate'] = result.apply(_jt_win, axis=1)

            # 出賽相隔日數
            last_run = history_df.groupby('horse_id')['race_date'].max().to_dict()
            result['days_since_last_run'] = result['horse_id'].map(
                lambda h: (datetime.now() - last_run[h]).days if h in last_run else 999
            ).fillna(999)

    # 填充剩餘特徵
    for c in feature_cols:
        result[c] = pd.to_numeric(result[c], errors='coerce').fillna(0)

    return result
def _repair_racecard(df):
    """自動修復混合格式嘅 racecard CSV"""
    # 讀取原始檔案（唔用 header）
    df_raw = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig', header=None, dtype=str)

    std_cols = ['horse_id', 'horse_name', 'draw', 'weight', 'jockey',
                'trainer', 'race_no', 'race_date', 'win_odds']

    # 中文格式欄位順序：馬號,馬名,檔位,負磅,騎師,練馬師,場次,比賽日期,賠率
    cn_cols = ['horse_id', 'horse_name', 'draw', 'weight', 'jockey',
               'trainer', 'race_no', 'race_date', 'win_odds']

    # 英文格式欄位順序：race_date,race_no,horse_no,horse_name,draw,weight,jockey,trainer,win_odds
    en_cols = ['race_date', 'race_no', 'horse_id', 'horse_name',
               'draw', 'weight', 'jockey', 'trainer', 'win_odds']

    parts = []

    for _, row in df_raw.iterrows():
        first_val = str(row[0]).strip()

        # 跳過 header 行
        if first_val.lower() in ['馬號', 'race_date', 'nan', '']:
            continue

        # 中文格式：第一列係純數字（馬號）
        if first_val.isdigit():
            row_df = pd.DataFrame([row.values], columns=cn_cols)
            parts.append(row_df)

        # 英文格式：第一列係日期（YYYY-MM-DD）
        elif len(first_val) == 10 and first_val[4] == '-' and first_val[7] == '-':
            row_df = pd.DataFrame([row.values], columns=en_cols)
            parts.append(row_df)

    if not parts:
        return pd.DataFrame(columns=std_cols)

    result = pd.concat(parts, ignore_index=True)
    result = result[std_cols]
    return result

def run_prediction(date_str, race_no):
    """用真正 ML 模型預測（統一 36 特徵版）"""
    if not os.path.exists("racecard_uploaded.csv"):
        st.error("❌ 找不到 racecard_uploaded.csv")
        return None, None

    try:
        race_df = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig')
        race_df = _repair_racecard(race_df)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None, None

    rename_map = {
        '馬名': 'horse_name', '檔位': 'draw', '場次': 'race_no',
        '比賽日期': 'race_date', '騎師': 'jockey', '練馬師': 'trainer',
        '負磅': 'weight', '馬號': 'horse_id', '賠率': 'win_odds',
        '路程': 'distance', '評分': 'rtg'
    }
    existing = [c for c in rename_map if c in race_df.columns]
    if existing:
        race_df.rename(columns={c: rename_map[c] for c in existing}, inplace=True)

    if 'race_date' not in race_df.columns:
        st.error("❌ 缺少 '比賽日期'")
        return None, None

    race_df['race_date'] = pd.to_datetime(race_df['race_date'], errors='coerce')
    race_df = race_df.dropna(subset=['race_date'])
    race_df['race_date_str'] = race_df['race_date'].dt.strftime('%Y-%m-%d')
    race_df['race_no'] = pd.to_numeric(race_df['race_no'], errors='coerce').fillna(0).astype(int)

    available_dates = sorted(race_df['race_date_str'].unique())
    if not available_dates:
        st.error("❌ 無可用日期")
        return None, None

    if date_str not in available_dates:
        st.warning(f"⚠️ {date_str} 冇數據，自動改用 {available_dates[-1]}")
        date_str = available_dates[-1]

    try:
        race_no = int(race_no)
    except Exception:
        race_no = 1

    df_date = race_df[race_df['race_date_str'] == date_str]
    if 'race_no' not in df_date.columns:
        st.error("❌ 缺少 '場次'")
        return None, None

    avail_races = sorted(df_date['race_no'].unique())
    if race_no not in avail_races:
        st.warning(f"⚠️ {date_str} 冇第 {race_no} 場，改用第 {avail_races[0]} 場")
        race_no = avail_races[0]

    filtered = df_date[df_date['race_no'] == race_no].copy().reset_index(drop=True)
    if filtered.empty:
        st.error(f"❌ {date_str} 第 {race_no} 場冇馬匹數據")
        return None, None

    st.success(f"✅ 成功載入 {date_str} 第 {race_no} 場，共 {len(filtered)} 匹馬")

    # ===== 歷史數據 =====
    history_df = pd.DataFrame()
    if os.path.exists("ALL_DATA_MERGED.csv"):
        try:
            history_df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
            history_df.columns = [str(c).replace('\ufeff', '').strip() for c in history_df.columns]
            if 'finish_position' not in history_df.columns and 'Pla' in history_df.columns:
                history_df['finish_position'] = history_df['Pla']
        except Exception as e:
            st.warning(f"⚠️ 讀取歷史數據失敗：{e}")

    # ===== 建立特徵 =====
    with st.spinner("🔧 計算特徵中..."):
        features_df = _build_features(filtered, history_df)

    # ===== 載入模型 =====
    xgb_model, cat_model, rank_model = load_ml_models()

    # ===== 36 特徵列表 =====
    features_36 = ['draw', 'weight', 'distance', 'Rtg.', 'avg_rank_last3',
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
                   'injury_60d', 'injury_90d', 'total_injuries', 'injury_severity']

    pred_xgb = None
    pred_cat = None
    pred_rank = None
    models_used = []

    # ===== XGBoost（強制用 36 特徵）=====
    if xgb_model is not None:
        try:
            X_xgb = features_df[features_36].fillna(0).values
            pred_xgb = xgb_model.predict_proba(X_xgb)[:, 1]
            models_used.append("XGBoost(36特徵)")
        except Exception as e:
            st.warning(f"⚠️ XGBoost 失敗：{e}")

    # ===== CatBoost（強制用 36 特徵）=====
    if cat_model is not None:
        try:
            X_cat = features_df[features_36].fillna(0).values
            pred_cat = cat_model.predict_proba(X_cat)[:, 1]
            models_used.append("CatBoost(36特徵)")
        except Exception as e:
            st.warning(f"⚠️ CatBoost 失敗：{e}")

    # ===== Ranking（強制用 36 特徵）=====
    if rank_model is not None:
        try:
            X_rank = features_df[features_36].fillna(0).values
            pred_rank = rank_model.predict(X_rank)
            pred_rank = np.array(pred_rank, dtype=float)
            if pred_rank.max() > pred_rank.min():
                pred_rank = (pred_rank - pred_rank.min()) / (pred_rank.max() - pred_rank.min())
            models_used.append("Ranking(36特徵)")
        except Exception as e:
            st.warning(f"⚠️ Ranking 失敗：{e}")

    # ===== 融合 =====
    all_preds = [p for p in [pred_xgb, pred_cat, pred_rank] if p is not None]

    if all_preds:
        # ===== 從 Supabase 讀取動態權重 =====
        try:
            headers_tune = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            res_tune = requests.get(f"{SUPABASE_URL}/rest/v1/model_weights?id=eq.1", headers=headers_tune)
            if res_tune.status_code == 200 and res_tune.json():
                tune = res_tune.json()[0]
                w_xgb = float(tune.get('xgb_weight', 0.30))
                w_cat = float(tune.get('cat_weight', 0.50))
                w_rank = float(tune.get('rank_weight', 0.20))
            else:
                w_xgb, w_cat, w_rank = 0.30, 0.50, 0.20
        except Exception:
            w_xgb, w_cat, w_rank = 0.30, 0.50, 0.20

        weights = []
        if pred_xgb is not None:
            weights.append(w_xgb)
        if pred_cat is not None:
            weights.append(w_cat)
        if pred_rank is not None:
            weights.append(w_rank)

        weights = np.array(weights) / sum(weights)

        pred_proba = np.zeros(len(filtered))
        for i, p in enumerate(all_preds):
            pred_proba += weights[i] * p

        st.success(f"✅ 使用模型：{', '.join(models_used)}（權重：XGB {weights[0]:.2f} / Cat {weights[1]:.2f} / Rank {weights[2]:.2f}）")
    else:
        st.warning("⚠️ 冇可用模型，改用賠率估算")
        win_odds = pd.to_numeric(filtered.get('win_odds', 4.0), errors='coerce').fillna(4.0).replace(0, 4.0)
        inv = 1 / win_odds
        pred_proba = (inv / inv.sum()).values

    # 正規化
    pred_proba = pred_proba / pred_proba.sum()

    # ===== 結果 =====
    id_col = None
    for col in ['horse_id', '馬號', 'horse_no']:
        if col in filtered.columns:
            id_col = col
            break

    if id_col:
        result_df = filtered[[id_col, 'horse_name']].copy()
        result_df = result_df.rename(columns={id_col: '馬號'})
    else:
        result_df = filtered[['horse_name']].copy()
        result_df.insert(0, '馬號', range(1, len(result_df) + 1))

    for c in ['draw', 'weight', 'jockey', 'trainer']:
        if c in filtered.columns:
            result_df[c] = filtered[c]

    result_df = result_df.rename(columns={
        'horse_name': '馬名',
        'draw': '檔位',
        'weight': '負磅',
        'jockey': '騎師',
        'trainer': '練馬師'
    })
    result_df['預測勝率'] = pred_proba
    result_df['值博指數'] = result_df['預測勝率'] * 10
    result_df['信心指數'] = result_df['預測勝率'].apply(
        lambda x: '⭐⭐⭐ 高' if x > 0.2 else '⭐⭐ 中' if x > 0.1 else '⭐ 低'
    )
    result_df = result_df.sort_values('預測勝率', ascending=False).reset_index(drop=True)

    # ===== 儲存到 Supabase =====
    from database import save_prediction
    key = f"{date_str}_{race_no}"
    save_prediction(key, {
        "date": date_str, "race": race_no,
        "top_horse": result_df.iloc[0]['馬名'],
        "top_prob": float(result_df.iloc[0]['預測勝率']),
        "all_horses": result_df['馬名'].tolist(),
        "model_used": models_used,
        "predicted_at": datetime.now().isoformat()
    })

    user_group = st.session_state.get('role', 'free')
    return result_df, generate_pool_recommendations(result_df, user_group)

def _find_data_col(df, keywords):
    """搵一個有數據嘅欄位（唔止名要對，仲要有實際值）"""
    for c in df.columns:
        cl = str(c).lower().strip()
        if any(k.lower() in cl for k in keywords):
            # 檢查呢個欄位係咪真係有數據
            non_empty = df[c].dropna().astype(str).str.strip()
            non_empty = non_empty[~non_empty.isin(['', 'nan', 'None', '-', 'NaN'])]
            if len(non_empty) > 10:  # 至少要 10 條有數據先算
                return c
    return None


def _find_pos_col(df):
    """搵名次欄位"""
    for c in df.columns:
        cl = str(c).lower().strip()
        if cl in ['pla', 'plc', '名次', 'finish_position', 'finishing_position',
                  'pos', 'position', 'rank', 'place', 'finish']:
            non_empty = df[c].dropna().astype(str).str.strip()
            non_empty = non_empty[~non_empty.isin(['', 'nan', 'None', '-'])]
            if len(non_empty) > 10:
                return c
    # 模糊搜尋
    for c in df.columns:
        cl = str(c).lower()
        if 'pla' in cl or '名次' in cl or 'finish' in cl:
            non_empty = df[c].dropna().astype(str).str.strip()
            non_empty = non_empty[~non_empty.isin(['', 'nan', 'None', '-'])]
            if len(non_empty) > 10:
                return c
    return None


def _rank_from_csv(col_keywords):
    """無敵版：自動搵出有數據嘅欄位"""
    # 讀取 CSV
    df = None
    for fp in ["ALL_DATA_MERGED.csv", "HKCJ_FULL_YEAR_DATA.csv"]:
        if not os.path.exists(fp):
            continue
        for enc in ['utf-8-sig', 'utf-8', 'big5', 'gbk']:
            try:
                df = pd.read_csv(fp, encoding=enc, low_memory=False)
                st.caption(f"📁 讀取：{fp}（{len(df)} 行）")
                break
            except Exception:
                continue
        if df is not None:
            break

    if df is None:
        st.error("❌ 搵唔到 ALL_DATA_MERGED.csv 或 HKCJ_FULL_YEAR_DATA.csv")
        return None

    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    pos_col = _find_pos_col(df)
    target_col = _find_data_col(df, col_keywords)

    if not pos_col or not target_col:
        st.error(f"❌ 搵唔到有數據嘅欄位！名次: `{pos_col}`，目標: `{target_col}`")
        with st.expander("🔍 診斷：所有欄位 + 非空數量", expanded=True):
            info = []
            for c in df.columns:
                non_empty = df[c].dropna().astype(str).str.strip()
                non_empty = non_empty[~non_empty.isin(['', 'nan', 'None', '-'])]
                info.append({'欄位': c, '非空數量': len(non_empty)})
            st.dataframe(pd.DataFrame(info), use_container_width=True)
        return None

    # 提取數據
    ts = df[target_col]
    if isinstance(ts, pd.DataFrame):
        ts = ts.iloc[:, 0]
    ps = df[pos_col]
    if isinstance(ps, pd.DataFrame):
        ps = ps.iloc[:, 0]

    # 轉名次做數字
    pos_str = ps.astype(str).str.strip()
    pos_num = pd.to_numeric(pos_str, errors='coerce')
    if pos_num.notna().sum() == 0:
        pos_num = pd.to_numeric(pos_str.str.extract(r'(\d+)')[0], errors='coerce')
    if pos_num.notna().sum() == 0:
        def _p(x):
            x = str(x).strip().lower()
            for s in ['st', 'nd', 'rd', 'th']:
                x = x.replace(s, '')
            try:
                return float(x.strip())
            except Exception:
                return None
        pos_num = pos_str.apply(_p)

    temp = pd.DataFrame({'name': ts.astype(str).str.strip(), 'finish_position': pos_num})
    temp = temp.dropna(subset=['finish_position'])
    temp = temp[~temp['name'].str.lower().isin(['nan', 'none', '', '-', '未知'])]

    if temp.empty:
        st.warning("⚠️ 過濾後數據為空！")
        with st.expander("🔍 診斷（點擊展開）", expanded=True):
            st.write(f"**使用欄位**：名次=`{pos_col}`，目標=`{target_col}`")
            st.write(f"**名次樣本**：{ps.head(10).tolist()}")
            st.write(f"**目標樣本**：{ts.head(10).tolist()}")
            st.write(f"**名次轉換後有效**：{pos_num.notna().sum()} / {len(pos_num)}")
        return None

    total = temp.groupby('name').size().reset_index(name='總出賽')
    wins = temp[temp['finish_position'] == 1].groupby('name').size().reset_index(name='勝出')
    stats = pd.merge(total, wins, on='name', how='left').fillna({'勝出': 0})
    stats['勝出'] = stats['勝出'].astype(int)
    stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
    return stats.sort_values('勝出', ascending=False)


def _get_pos_series(df):
    """自动选择名次欄位：优先 Pla，如果冇就用 finish_position"""
    # 試 Pla（用位置索引，避免隱藏字元）
    pla_idx = None
    for i, c in enumerate(df.columns):
        if str(c).strip().lower() == 'pla':
            pla_idx = i
            break
    if pla_idx is None:
        pla_idx = 2  # 預設第 3 列

    pos = pd.to_numeric(df.iloc[:, pla_idx], errors='coerce')
    if pos.notna().sum() >= 100:
        return pos, f'Pla (第 {pla_idx} 列)'

    # 如果 Pla 唔得，試 finish_position
    if 'finish_position' in df.columns:
        pos = pd.to_numeric(df['finish_position'], errors='coerce')
        if pos.notna().sum() >= 100:
            return pos, 'finish_position'

    return pos, '未知'

def admin_horse_ranking():
    st.subheader("🏇 馬匹勝率排行榜")

    import os
    import pandas as pd

    result_file = "race_results_clean.csv"
    if not os.path.exists(result_file):
        st.warning("⚠️ 找不到 race_results_clean.csv")
        return

    try:
        df = pd.read_csv(result_file, encoding='utf-8-sig')
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return

    # 🛡️ 智能偵測欄位名（支援中英文）
    name_col = None
    for c in ['horse_name', '馬名', '馬匹名稱', 'Name']:
        if c in df.columns:
            name_col = c
            break

    pos_col = None
    for c in ['finish_position', '名次', 'Pla.', '最終名次']:
        if c in df.columns:
            pos_col = c
            break

    if name_col is None or pos_col is None:
        st.write(f"可用欄位：{df.columns.tolist()}")
        st.warning("⚠️ 賽果檔案缺少「馬名」或「名次」欄位")
        return

    # 清理數據
    df[name_col] = df[name_col].astype(str).str.strip()
    df[pos_col] = pd.to_numeric(df[pos_col], errors='coerce')
    df = df.dropna(subset=[pos_col, name_col])
    df = df[df[name_col] != '']

    # 計算每匹馬嘅出賽次數、勝出次數、勝率
    stats = df.groupby(name_col).agg(
        總出賽=(pos_col, 'count'),
        勝出=(pos_col, lambda x: (x == 1).sum())
    ).reset_index()

    stats['勝率'] = stats['勝出'] / stats['總出賽']
    stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)
    stats = stats[stats['總出賽'] >= 1]

    st.success(f"✅ 共 {len(stats)} 匹馬（有效數據：{len(df)} 條）")

    # 格式化顯示
    stats['勝率'] = stats['勝率'].apply(lambda x: f"{x:.1%}")
    stats.columns = ['馬名', '總出賽', '勝出', '勝率']

    st.dataframe(stats, use_container_width=True, hide_index=True, height=600)
def admin_jockey_ranking():
    st.subheader("🏇 騎師勝率排行榜")
    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]

        pos_series, pos_name = _get_pos_series(df)
        st.caption(f"📊 使用名次欄位：**{pos_name}**（有效數據：{pos_series.notna().sum()}）")

        temp = pd.DataFrame()
        temp['騎師'] = df['jockey'].astype(str).str.strip()
        temp['名次'] = pos_series
        temp = temp.dropna(subset=['名次'])
        temp = temp[~temp['騎師'].str.lower().isin(['nan', 'none', ''])]

        if temp.empty:
            st.warning("⚠️ 過濾後數據為空！")
            return

        total = temp['騎師'].value_counts()
        wins = temp[temp['名次'] == 1]['騎師'].value_counts()
        stats = pd.DataFrame({'騎師': total.index, '總出賽': total.values})
        stats['勝出'] = stats['騎師'].map(wins).fillna(0).astype(int)
        stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
        stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)

        jmap = {}
        if os.path.exists("jockey_mapping.json"):
            try:
                jmap = load_json("jockey_mapping.json")
            except Exception:
                pass
        if jmap:
            stats['騎師'] = stats['騎師'].map(jmap).fillna(stats['騎師'])

        st.success(f"✅ 共 {len(stats)} 位騎師")
        st.dataframe(stats.head(30), use_container_width=True)
    except Exception as e:
        st.error(f"讀取失敗：{e}")


def admin_trainer_ranking():
    st.subheader("🏇 練馬師勝率排行榜")
    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]

        pos_series, pos_name = _get_pos_series(df)
        st.caption(f"📊 使用名次欄位：**{pos_name}**（有效數據：{pos_series.notna().sum()}）")

        temp = pd.DataFrame()
        temp['練馬師'] = df['trainer'].astype(str).str.strip()
        temp['名次'] = pos_series
        temp = temp.dropna(subset=['名次'])
        temp = temp[~temp['練馬師'].str.lower().isin(['nan', 'none', ''])]

        if temp.empty:
            st.warning("⚠️ 過濾後數據為空！")
            return

        total = temp['練馬師'].value_counts()
        wins = temp[temp['名次'] == 1]['練馬師'].value_counts()
        stats = pd.DataFrame({'練馬師': total.index, '總出賽': total.values})
        stats['勝出'] = stats['練馬師'].map(wins).fillna(0).astype(int)
        stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
        stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)

        tmap = {}
        if os.path.exists("trainer_mapping.json"):
            try:
                tmap = load_json("trainer_mapping.json")
            except Exception:
                pass
        if tmap:
            stats['練馬師'] = stats['練馬師'].map(tmap).fillna(stats['練馬師'])

        st.success(f"✅ 共 {len(stats)} 位練馬師")
        st.dataframe(stats.head(30), use_container_width=True)
    except Exception as e:
        st.error(f"讀取失敗：{e}")
def admin_lottery_config():
    st.subheader("🎰 抽獎設定")
    config = load_lottery_config()
    prizes = config.get("prizes", [])
    st.write(f"目前有 **{len(prizes)}** 個獎品")

    # ===== 現有獎品表 =====
    if prizes:
        _type_cn = {
            "virtual_coin": "🪙 虛擬幣",
            "vip_days": "👑 VIP",
            "free_predictions": "🔮 預測",
            "promo_code": "🎟️ 優惠碼",
            "custom": "🎁 自訂",
            "nothing": "😅 無獎"
        }
        rows = []
        for p in prizes:
            rows.append({
                "獎品": p.get('name', ''),
                "類型": _type_cn.get(p.get('type', ''), p.get('type', '')),
                "數值": p.get('value', 0),
                "權重": p.get('weight', 0),
                "描述": p.get('description', '')
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("➕ 新增獎品")

    # ===== 表單 =====
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        p_name = st.text_input("獎品名稱", key="lot_name")
    with col2:
        p_value = st.number_input("數值", min_value=0, value=100, key="lot_value")
    with col3:
        p_weight = st.number_input("權重", min_value=1, value=10, key="lot_weight")

    col_type, col_desc = st.columns([1, 2])
    with col_type:
        p_type = st.selectbox(
            "獎品類型",
            ["virtual_coin", "vip_days", "free_predictions", "promo_code", "custom", "nothing"],
            format_func=lambda x: {
                "virtual_coin": "🪙 虛擬幣",
                "vip_days": "👑 VIP",
                "free_predictions": "🔮 預測",
                "promo_code": "🎟️ 優惠碼",
                "custom": "🎁 自訂",
                "nothing": "😅 無獎"
            }.get(x, x),
            key="lot_type"
        )
    with col_desc:
        p_desc = st.text_input("描述", key="lot_desc")

    if st.button("➕ 新增獎品", key="add_lot_v2", use_container_width=True):
        prizes.append({
            "name": p_name,
            "type": p_type,
            "value": p_value,
            "weight": p_weight,
            "description": p_desc
        })
        config["prizes"] = prizes
        if save_lottery_config(config):
            st.success("✅ 已新增獎品！")
            st.rerun()
        else:
            st.error("❌ 儲存失敗")

    # ===== 編輯獎品 =====
    if prizes:
        st.divider()
        st.subheader("✏️ 編輯獎品")
        for i, p in enumerate(prizes):
            with st.expander(f"{p.get('name', '獎品')}（權重 {p.get('weight', 0)}）"):
                _w = _safe_int(p.get('weight', 10), 10)
                _v = _safe_int(p.get('value', 0), 0)
                ec1, ec2 = st.columns(2)
                with ec1:
                    nw = st.number_input("中獎機率", min_value=1, value=max(1, _w), key=f"ew_{i}")
                with ec2:
                    nv = st.number_input("數值", min_value=0, value=max(0, _v), key=f"ev_{i}")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("💾 儲存", key=f"sp_{i}", use_container_width=True):
                        prizes[i]['weight'] = nw
                        prizes[i]['value'] = nv
                        config["prizes"] = prizes
                        save_lottery_config(config)
                        st.success("✅ 已儲存")
                        st.rerun()
                with cb:
                    if st.button("🗑️ 刪除", key=f"dp_{i}", use_container_width=True):
                        prizes.pop(i)
                        config["prizes"] = prizes
                        save_lottery_config(config)
                        st.success("✅ 已刪除")
                        st.rerun()
def save_shop_config(c):
    """寫入商城商品到 Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    items = c.get("items", [])
    try:
        # 先刪走所有舊商品
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/shop_config?id=gt.0",
            headers=headers, timeout=15
        )
        # 再插入新商品
        if items:
            clean_items = []
            for item in items:
                clean_item = {k: v for k, v in item.items() if k != 'id'}
                clean_items.append(clean_item)
            res = requests.post(
                f"{SUPABASE_URL}/rest/v1/shop_config",
                headers=headers, json=clean_items, timeout=15
            )
            if res.status_code in (200, 201, 204):
                return True
            else:
                print(f"save_shop_config failed: {res.status_code} - {res.text}")
                return False
        return True
    except Exception as e:
        print(f"保存商城失敗: {e}")
        return False


def admin_shop_config():
    st.subheader("🛒 商城設定")
    config = load_shop_config()
    items = config.get("items", [])
    st.write(f"目前有 **{len(items)}** 件商品")
    if items:
        try:
            st.dataframe(pd.DataFrame(items), use_container_width=True)
        except Exception:
            pass

    st.divider()
    st.subheader("➕ 新增商品")
    col1, col2, col3 = st.columns(3)
    with col1:
        i_name = st.text_input("商品名稱", key="shop_name")
        i_type = st.selectbox(
            "商品類型",
            ["predictions", "vip_days", "lottery_draws", "title", "mystery_box"],
            key="shop_type"
        )
    with col2:
        i_price = st.number_input("價格", min_value=0, value=100, key="shop_price")
        i_stock = st.number_input("庫存", min_value=0, value=100, key="shop_stock")
    with col3:
        i_desc = st.text_input("描述", key="shop_desc")

    if st.button("➕ 新增商品", key="add_shop"):
        items.append({
            "name": i_name, "type": i_type, "price": i_price,
            "stock": i_stock, "description": i_desc
        })
        config["items"] = items
        if save_shop_config(config):
            st.success("✅ 已新增商品！")
            st.rerun()
        else:
            st.error("❌ 儲存失敗")

    if items:
        st.divider()
        st.subheader("✏️ 直接編輯商品表格")
        try:
            edited = st.data_editor(
                pd.DataFrame(items),
                use_container_width=True,
                key="shop_editor",
                num_rows="dynamic"
            )
            if st.button("💾 儲存所有變更", key="save_shop"):
                config["items"] = edited.to_dict(orient='records')
                save_shop_config(config)
                st.success("✅ 已儲存")
                st.rerun()
        except Exception as e:
            st.error(f"編輯器錯誤：{e}")
def show_paywall():
    st.subheader("💳 選擇你嘅方案")
    plan_options = {
        "day": f"☀️ 日費  ${CONFIG['price_day']}   (1天)",
        "month": f"📆 月費  ${CONFIG['price_month']}  (30天)",
        "quarter": f"📅 季費  ${CONFIG['price_quarter']} (90天)"
    }

    with st.form(key="payment_form"):
        plan_choice = st.radio(
            "請選擇付費方案：",
            options=list(plan_options.keys()),
            format_func=lambda x: plan_options[x],
            horizontal=True,
            key="plan_radio"
        )
        promo_input = st.text_input("優惠碼（如有）", key="promo_input_form")

        st.divider()
        st.markdown("""
        **📤 付款方式：FPS 轉數快 `12345678`（SHTSN SYSTEM）**
        💬 過數後請將截圖發送 Telegram：**@bryhjdjbrbxibvrjskofndhiebdpaq**
        """)

        submitted = st.form_submit_button("📩 提交付款申請", type="primary")

        if submitted:
            if not plan_choice:
                st.error("❌ 請選擇方案")
                return
            username = st.session_state.get('username')
            if not username:
                st.error("❌ 請先登入")
                return

            original_price = get_plan_price(plan_choice)
            final_price = original_price
            discount_desc = ""
            promo_code_used = None

            if promo_input:
                promos = load_promos()
                promo_data = promos.get(promo_input.strip())
                if promo_data and not promo_data.get('used', False):
                    expiry = promo_data.get('expiry')
                    valid = True
                    if expiry:
                        try:
                            if datetime.fromisoformat(expiry) < datetime.now():
                                valid = False
                        except Exception:
                            pass
                    if valid:
                        dtype = promo_data.get('discount_type', 'percentage')
                        dval = promo_data.get('discount_value', 0)
                        if dtype == 'percentage':
                            final_price = original_price * (1 - dval / 100)
                            discount_desc = f"{dval}% 折扣"
                        elif dtype == 'fixed':
                            final_price = max(0, original_price - dval)
                            discount_desc = f"減 ${dval}"
                        elif dtype == 'free':
                            final_price = 0
                            discount_desc = "全免！"
                        final_price = round(final_price, 2)
                        promo_code_used = promo_input.strip()
                        st.success(f"✅ 優惠碼已套用！折扣後：${final_price}")
                else:
                    st.warning("⚠️ 優惠碼無效")            
            # 如果用到優惠碼，立即標記為已使用
            if promo_code_used:
                promos = load_promos()
                if promo_code_used in promos:
                    promos[promo_code_used]['used'] = True
                    promos[promo_code_used]['used_by'] = username
                    promos[promo_code_used]['used_at'] = datetime.now().isoformat()
                    save_promos(promos)

            success, msg = submit_payment_request(username, plan_choice, final_price, discount_desc, promo_code_used)
            if success:
                st.success(msg)
                st.info(f"方案：{get_plan_name(plan_choice)}，金額：${final_price}")
                st.info("📩 提交後請 Telegram 通知管理員")
def do_checkin(username):
    """執行簽到，返回 (成功?, 訊息, 金幣, 連續日數, 有冇VIP)"""
    import pytz
    from datetime import datetime, timedelta

    hk_tz = pytz.timezone('Asia/Hong_Kong')
    now_hk = datetime.now(hk_tz)
    today = now_hk.strftime('%Y-%m-%d')
    yesterday = (now_hk - timedelta(days=1)).strftime('%Y-%m-%d')

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/checkin_history?username=eq.{username}&checkin_date=eq.{today}&limit=1",
            headers=headers, timeout=10
        )
        existing = res.json() if res.status_code == 200 else []
    except Exception as e:
        return False, f"連線錯誤：{e}", 0, 0, False

    if existing:
        return False, "今日已簽到，聽日再嚟！", 0, 0, False

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/checkin_history?username=eq.{username}&order=checkin_date.desc&limit=1",
            headers=headers, timeout=10
        )
        last_records = res.json() if res.status_code == 200 else []
    except Exception as e:
        return False, f"連線錯誤：{e}", 0, 0, False

    if last_records:
        last_date = str(last_records[0].get('checkin_date', ''))
        last_streak = int(last_records[0].get('streak_day', 0))
        if last_date == yesterday:
            streak = last_streak + 1
            if streak > 7:
                streak = 1
        else:
            streak = 1
    else:
        streak = 1

    coin_map = {1: 500, 2: 800, 3: 1100, 4: 1400, 5: 1700, 6: 2000, 7: 2500}
    coins = coin_map.get(streak, 500)
    is_vip_reward = (streak == 7)

    payload = {
        "username": username,
        "checkin_date": today,
        "streak_day": streak,
        "coins_earned": coins
    }
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/checkin_history",
            headers=headers, json=payload, timeout=10
        )
        if res.status_code not in (200, 201, 204):
            return False, f"寫入失敗：{res.text}", 0, 0, False
    except Exception as e:
        return False, f"連線錯誤：{e}", 0, 0, False

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}&limit=1",
            headers=headers, timeout=10
        )
        user_data = res.json() if res.status_code == 200 else []
        old_balance = float(user_data[0].get('virtual_balance', 0) or 0) if user_data else 0.0
    except Exception:
        user_data = []
        old_balance = 0.0

    new_balance = old_balance + coins
    update_payload = {"virtual_balance": new_balance}

    if is_vip_reward:
        update_payload["user_group"] = "VIP"
        try:
            expiry = user_data[0].get('expiry_date') if user_data else None
            if expiry and str(expiry).strip() and str(expiry) != 'EMPTY':
                expiry_dt = datetime.strptime(str(expiry)[:10], '%Y-%m-%d')
                new_expiry = (expiry_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                new_expiry = (now_hk + timedelta(days=1)).strftime('%Y-%m-%d')
            update_payload["expiry_date"] = new_expiry
        except Exception:
            update_payload["expiry_date"] = (now_hk + timedelta(days=1)).strftime('%Y-%m-%d')

    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=headers, json=update_payload, timeout=10
        )
    except Exception as e:
        return False, f"更新用戶失敗：{e}", coins, streak, is_vip_reward

    return True, f"簽到成功！連續第 {streak} 日", coins, streak, is_vip_reward


def show_checkin_button(username):
    """主頁顯示簽到掣"""
    import pytz
    from datetime import datetime, timedelta

    hk_tz = pytz.timezone('Asia/Hong_Kong')
    now_hk = datetime.now(hk_tz)
    today = now_hk.strftime('%Y-%m-%d')
    yesterday = (now_hk - timedelta(days=1)).strftime('%Y-%m-%d')

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/checkin_history?username=eq.{username}&checkin_date=eq.{today}&limit=1",
            headers=headers, timeout=10
        )
        today_records = res.json() if res.status_code == 200 else []
    except Exception:
        today_records = []

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/checkin_history?username=eq.{username}&order=checkin_date.desc&limit=7",
            headers=headers, timeout=10
        )
        history = res.json() if res.status_code == 200 else []
    except Exception:
        history = []

    streak = 0
    if history:
        last = history[0]
        last_date = str(last.get('checkin_date', ''))
        last_streak = int(last.get('streak_day', 0))
        if last_date == today or last_date == yesterday:
            streak = last_streak
        else:
            streak = 0

    st.markdown("### 📅 每日簽到")
    st.caption(f"連續簽到：**{streak}** / 7 日")

    if today_records:
        st.success(f"✅ 今日已簽到（連續第 {streak} 日）")
        st.info("聽日再嚟簽到，獎勵會更多！")
    else:
        next_day = streak + 1 if streak < 7 else 1
        coin_map = {1: 500, 2: 800, 3: 1100, 4: 1400, 5: 1700, 6: 2000, 7: 2500}
        next_coins = coin_map.get(next_day, 500)
        msg = f"下次簽到係連續第 {next_day} 日，可獲得 **{next_coins}** 金幣"
        if next_day == 7:
            msg += " + **VIP 1 日**"
        st.info(msg)

        if st.button("✅ 今日簽到", type="primary", use_container_width=True, key="checkin_btn"):
            ok, message, coins, new_streak, got_vip = do_checkin(username)
            if ok:
                success_msg = f"✅ {message}，獲得 {coins} 金幣"
                if got_vip:
                    success_msg += " + VIP 1 日！"
                st.success(success_msg)
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.warning(f"⚠️ {message}")

    if history:
        with st.expander("📜 過去簽到紀錄", expanded=False):
            for rec in history:
                d = str(rec.get('checkin_date', ''))
                sd = rec.get('streak_day', '?')
                ce = rec.get('coins_earned', '?')
                st.write(f"📅 {d} — 連續第 {sd} 日 — +{ce} 金幣")


def show_lottery_interface(username):
    st.subheader("🎰 每日抽獎")
    if not username:
        st.info("請先登入")
        return

    # ===== 倒數計時 =====
    try:
        hk_tz = pytz.timezone("Asia/Hong_Kong")
        now = datetime.now(hk_tz)
        tm = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        secs = int((tm - now).total_seconds())
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        st.info(f"⏰ 距離下次重置：**{h} 小時 {m} 分 {s} 秒**")
    except Exception:
        pass

    config = load_lottery_config()
    prizes = config.get("prizes", [])
    if not prizes:
        st.warning("暫無獎品，請管理員新增")
        return

    users = load_users()
    user = users.get(username, {})

    # ===== 🔥 每日自動重置抽獎次數 =====
    today = datetime.now().strftime('%Y-%m-%d')
    reset_key = f"_lottery_reset_done_{username}_{today}"

    if user.get('last_lottery_reset', '') != today:
        if not st.session_state.get(reset_key, False):
            st.session_state[reset_key] = True
            daily_chances = 1
            user['lottery_chances'] = user.get('lottery_chances', 0) + daily_chances
            user['last_lottery_reset'] = today
            users[username] = user
            try:
                if 'update_single_user' in globals():
                    update_single_user(username, user)
                else:
                    save_users(users)
            except Exception as e:
                print(f"每日重置寫入失敗: {e}")
            st.success(f"🎁 每日重置！你獲得 {daily_chances} 次抽獎機會！")

    # 重新讀取最新狀態
    users = load_users()
    user = users.get(username, {})
    lottery_chances = user.get('lottery_chances', 0)

    # 初始化 session state
    if 'lottery_rolling' not in st.session_state:
        st.session_state.lottery_rolling = False
    if 'lottery_result' not in st.session_state:
        st.session_state.lottery_result = None

    # ===== 🎯 優先顯示中獎結果（即使次數變 0）=====
    if st.session_state.lottery_result is not None:
        result = st.session_state.lottery_result
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f9d423, #ff4e50);
                    padding: 30px; border-radius: 16px; text-align: center;
                    color: white; box-shadow: 0 8px 25px rgba(255,78,80,0.4);">
            <div style="font-size: 70px;">{result['icon']}</div>
            <div style="font-size: 24px; font-weight: 800; margin-top: 10px;">
                🎉 恭喜中獎！
            </div>
            <div style="font-size: 32px; font-weight: 900; margin-top: 12px;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                {result['name']}
            </div>
            <div style="font-size: 18px; opacity: 0.95; margin-top: 10px;">
                {result['desc']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.balloons()
        st.snow()

        if st.button("🔄 再抽一次", use_container_width=True, key="roll_again"):
            st.session_state.lottery_result = None
            st.rerun()
        return  # 顯示完結果就 return

    # ===== 顯示抽獎次數 =====
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea, #764ba2);
                padding: 18px 22px; border-radius: 14px; color: white;
                text-align: center; margin-bottom: 16px;">
        <div style="font-size: 14px; opacity: 0.9;">🎟️ 你嘅抽獎機會</div>
        <div style="font-size: 48px; font-weight: 800; line-height: 1.2;">{lottery_chances}</div>
        <div style="font-size: 12px; opacity: 0.8;">次</div>
    </div>
    """, unsafe_allow_html=True)

    if lottery_chances <= 0:
        st.warning("⚠️ 你冇抽獎次數啦！請聽日再嚟，或者聯絡管理員增加。")
        return

    # ===== 動畫區域 =====
    animation_placeholder = st.empty()

    if st.session_state.lottery_rolling:
        icons = ["🎁", "🎰", "💎", "🏆", "🎊", "⭐", "🍀", "🎯"]
        for i in range(12):
            icon = icons[i % len(icons)]
            animation_placeholder.markdown(f"""
            <div style="background: linear-gradient(135deg, #ffecd2, #fcb69f);
                        padding: 40px; border-radius: 16px; text-align: center;
                        border: 3px dashed #ff6b6b;">
                <div style="font-size: 80px;">{icon}</div>
                <div style="font-size: 20px; font-weight: bold; color: #d63447; margin-top: 10px;">
                    抽獎中...
                </div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(0.15)

    # ===== 抽獎按鈕 =====
    if not st.session_state.lottery_rolling:
        if st.button("🎲 開始抽獎！", type="primary", use_container_width=True, key="start_lottery"):
            st.session_state.lottery_rolling = True
            st.rerun()

    # ===== 執行抽獎邏輯 =====
    if st.session_state.lottery_rolling:
        users[username]['lottery_chances'] = lottery_chances - 1

        weights = [_safe_int(p.get('weight', 1), 1) for p in prizes]
        if sum(weights) <= 0:
            weights = [1] * len(prizes)
        chosen = random.choices(prizes, weights=weights, k=1)[0]
        ptype = chosen.get('type', 'nothing')
        pval = _safe_int(chosen.get('value', 0), 0)
        pname = chosen.get('name', '獎品')

        icon = "🎁"
        desc = ""

        if ptype == 'virtual_coin':
            users[username]['virtual_balance'] = user.get('virtual_balance', 0) + pval
            icon = "💰"
            desc = f"+${pval} 虛擬幣"
        elif ptype == 'vip_days':
            users[username]['group'] = 'VIP'
            users[username]['predictions_limit'] = -1
            icon = "👑"
            desc = f"VIP {pval} 天"
        elif ptype == 'free_predictions':
            if users[username].get('predictions_limit', 0) != -1:
                users[username]['predictions_limit'] = users[username].get('predictions_limit', 0) + pval
            icon = "🔮"
            desc = f"{pval} 次免費預測"
        elif ptype == 'promo_code':
            code = generate_promo_code()
            promos = load_promos()
            promos[code] = {
                "used": False,
                "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                "discount_type": "percentage",
                "discount_value": 20,
                "source": "lottery",
                "created_by": username
            }
            save_promos(promos)
            icon = "🎟️"
            desc = f"優惠碼：{code}"
            pname = f"優惠碼 {code}"
        elif ptype == 'nothing':
            icon = "😅"
            desc = "冇中獎，下次再嚟！"
        else:
            icon = "🎁"
            desc = chosen.get('description', '')

        save_users(users)
        time.sleep(1.5)

        st.session_state.lottery_result = {
            'name': pname,
            'desc': desc,
            'icon': icon
        }
        st.session_state.lottery_rolling = False
        st.rerun()

    # ===== 獎品一覽 =====
    st.divider()
    with st.expander("🎁 獎品一覽", expanded=False):
        rows = []
        for p in prizes:
            rows.append({
                "獎品": p.get('name', ''),
                "類型": p.get('type', ''),
                "數值": p.get('value', 0),
                "中獎機率": f"{p.get('weight', 0)}"
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def show_shop_interface(username):
    st.subheader("🛒 虛擬商城")
    if not username:
        st.info("請先登入")
        return

    users = load_users()
    user = users.get(username, {})
    balance = user.get('virtual_balance', 0)
    st.metric("💎 你嘅虛擬幣結餘", f"${balance:,.0f}")

    config = load_shop_config()
    items = config.get("items", [])
    if not items:
        st.info("暫無商品")
        return

    for i, item in enumerate(items):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{item.get('name', '商品')}**")
            st.caption(item.get('description', ''))
        with col2:
            st.write(f"💰 ${item.get('price', 0)}")
            st.caption(f"庫存：{item.get('stock', 0)}")
        with col3:
            if st.button("🛒 購買", key=f"buy_{i}"):
                price = _safe_int(item.get('price', 0), 0)
                stock = _safe_int(item.get('stock', 0), 0)
                if stock <= 0:
                    st.error("❌ 已售罄")
                elif balance < price:
                    st.error("❌ 餘額不足")
                else:
                    users[username]['virtual_balance'] = balance - price
                    items[i]['stock'] = stock - 1
                    config['items'] = items
                    save_shop_config(config)
                    save_users(users)
                    st.success(f"✅ 已購買 {item.get('name')}！")
                    st.rerun()
        st.divider()
def admin_dashboard():
    st.subheader("📊 系統儀表板")
    users = load_users()
    acc = load_accuracy()
    finance = load_finance()
    records = acc.get('records', [])
    proof = load_payment_proofs()
    today = datetime.now().date()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("👤 總用戶", len(users))
    c2.metric("📈 今日新增", sum(1 for u in users.values() if u.get('created_at', '').startswith(str(today))))
    c3.metric("💰 總收入", f"${finance.get('total_income', 0):.2f}")
    c4.metric("📊 總預測", len(records))
    total = len([r for r in records if r.get('is_hit') is not None])
    hit = sum(1 for r in records if r.get('is_hit') is True)
    c5.metric("🎯 命中率", f"{hit/total:.2%}" if total > 0 else "0%")
    pending = len([p for p in proof.get('proof_records', []) if p.get('status') == 'pending'])
    c6.metric("⏳ 待審核", pending)

def admin_user_management():
    st.subheader("👥 用戶管理")
    user_file = "users.json"

    if not os.path.exists(user_file):
        st.error("❌ users.json 不存在")
        return

    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return

    st.info(f"✅ 成功載入 {len(users)} 個用戶")

    # ===== 1. 用戶列表 =====
    if users:
        df = pd.DataFrame.from_dict(users, orient='index')
        for c, d in [('level', '🥉 銅牌會員'), ('exp', 0), ('badges', []),
                     ('virtual_balance', 0), ('group', 'free')]:
            if c not in df.columns:
                df[c] = d
        df['badges_count'] = df['badges'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        cols = ['username', 'group', 'level', 'exp', 'badges_count', 'total_usage', 'is_paid', 'virtual_balance']
        display_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("暫無用戶")

    st.divider()

    # ===== 2. 新增用戶 =====
    with st.expander("➕ 新增用戶", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            nu = st.text_input("新用戶名", key="nu_name")
            np_ = st.text_input("密碼", type="password", key="nu_pw")
        with col2:
            ng = st.selectbox("群組", ["free", "paid", "VIP", "super_admin"], key="nu_group")
            npaid = st.checkbox("付費狀態", value=False, key="nu_paid")
        if st.button("建立用戶", key="create_user_btn"):
            if not nu or not np_:
                st.warning("請填寫用戶名同密碼")
            elif nu in users:
                st.error("❌ 用戶名已被使用")
            else:
                users[nu] = {
                    "password": np_, "phone": "", "is_paid": npaid,
                    "paid_date": None, "expiry_date": None,
                    "free_usage": 0, "total_usage": 0,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "note": "手動新增", "group": ng, "plan": None,
                    "predictions_limit": -1 if ng in ['super_admin', 'VIP'] else CONFIG.get("free_limit", 2),
                    "history": [], "terms_agreed": datetime.now().isoformat(),
                    "invite_code": nu.upper() + str(random.randint(100, 999)),
                    "invited_by": None, "invite_rewards": 0, "invite_count": 0,
                    "level": "🥉 銅牌會員", "exp": 0, "badges": [],
                    "virtual_balance": CONFIG.get("daily_virtual_coin", 1000),
                    "last_claim_date": '', "bets": [], "last_lottery_date": ""
                }
                if save_users(users):
                    st.success(f"✅ 用戶 {nu} 已建立！")
                    st.rerun()
                else:
                    st.error("❌ 儲存失敗")

    st.divider()

    # ===== 3. 編輯用戶 =====
    st.subheader("✏️ 編輯用戶")
    sel = st.selectbox("選擇要編輯嘅用戶", list(users.keys()), key="edit_user_sel")
    if sel:
        u = users[sel]
        col1, col2 = st.columns(2)
        with col1:
            grp_options = ['free', 'paid', 'VIP', 'super_admin']
            cur_grp = u.get('group', 'free')
            ngrp = st.selectbox(
                "群組", grp_options,
                index=grp_options.index(cur_grp) if cur_grp in grp_options else 0,
                key="edit_grp"
            )
            npaid = st.checkbox("付費狀態", value=u.get('is_paid', False), key="edit_paid")
            npw = st.text_input("新密碼（留空 = 不改）", type="password", key="edit_pw")
            phone = st.text_input("手機號碼", value=u.get('phone', ''), key="edit_phone")
        with col2:
            level_options = ["🥉 銅牌會員", "🥈 銀牌會員", "🥇 金牌會員",
                             "💎 鑽石會員", "👑 傳說會員", "👑 超級管理員"]
            cur_lv = u.get('level', '🥉 銅牌會員')
            if cur_lv not in level_options:
                level_options.append(cur_lv)
            nlv = st.selectbox(
                "等級", level_options,
                index=level_options.index(cur_lv) if cur_lv in level_options else 0,
                key="edit_lv"
            )
            nexp = st.number_input("經驗值", min_value=0, value=int(u.get('exp', 0)), step=10, key="edit_exp")
            all_badges = ["🏆 首勝", "🔥 三連勝", "⚡ 五連勝", "💯 百場預測",
                          "🎯 命中大師", "👥 社交達人", "💰 付費會員", "🏇 馬匹專家"]
            cur_badges = u.get('badges', [])
            nbadges = st.multiselect(
                "勳章", all_badges,
                default=[b for b in cur_badges if b in all_badges],
                key="edit_badges"
            )

        note = st.text_area("備註", value=u.get('note', ''), key="edit_note")

        if st.button("💾 儲存變更", type="primary", key="save_user_changes"):
            users[sel]['group'] = ngrp
            users[sel]['is_paid'] = npaid
            users[sel]['note'] = note
            users[sel]['level'] = nlv
            users[sel]['exp'] = nexp
            users[sel]['badges'] = nbadges
            users[sel]['phone'] = phone
            if npw:
                users[sel]['password'] = npw
            if ngrp in ['super_admin', 'VIP']:
                users[sel]['predictions_limit'] = -1
            else:
                users[sel]['predictions_limit'] = CONFIG.get("free_limit", 2)
            if save_users(users):
                st.success("✅ 已更新用戶資料！")
                st.rerun()
            else:
                st.error("❌ 儲存失敗")

    st.divider()

    # ===== 4. 管理員贈送虛擬幣 =====
    st.subheader("🎁 贈送虛擬幣")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        target = st.selectbox("選擇用戶", list(users.keys()), key="gift_user_sel")
        if target:
            cur_bal = users[target].get('virtual_balance', 0)
            st.caption(f"目前餘額：**${cur_bal:,.0f}**")
    with col2:
        amount = st.number_input("金額", min_value=1, value=100, step=100, key="gift_amount")
    with col3:
        st.write("")
        if st.button("🎁 贈送", type="primary", use_container_width=True, key="gift_send"):
            if target:
                users[target]['virtual_balance'] = users[target].get('virtual_balance', 0) + amount
                if save_users(users):
                    st.success(f"✅ 已贈送 ${amount} 給 {target}，新餘額：${users[target]['virtual_balance']:,.0f}")
                    st.rerun()
                else:
                    st.error("❌ 儲存失敗")

    st.divider()

    # ===== 5. 快速扣款 =====
    with st.expander("➖ 扣款"):
        col1, col2 = st.columns(2)
        with col1:
            target2 = st.selectbox("選擇用戶", list(users.keys()), key="deduct_user_sel")
        with col2:
            amt2 = st.number_input("扣款金額", min_value=1, value=100, step=100, key="deduct_amt")
        if st.button("➖ 確認扣款", key="deduct_btn"):
            if target2:
                cur = users[target2].get('virtual_balance', 0)
                if cur < amt2:
                    st.error(f"❌ 餘額不足（${cur:,.0f}）")
                else:
                    users[target2]['virtual_balance'] = cur - amt2
                    if save_users(users):
                        st.success(f"✅ 已扣除 ${amt2}，新餘額：${users[target2]['virtual_balance']:,.0f}")
                        st.rerun()

    st.divider()

    # ===== 6. 查看用戶視角 =====
    with st.expander("👁️ 查看用戶視角"):
        target3 = st.selectbox("選擇用戶", list(users.keys()), key="view_user_sel")
        if target3:
            u = users[target3]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👤 用戶", target3)
            c2.metric("🏷️ 級別", u.get('group', 'free').upper())
            c3.metric("📊 總預測次數", len(u.get('history', [])))
            limit = u.get('predictions_limit', CONFIG.get('free_limit', 2))
            if limit == -1:
                c4.metric("📊 剩餘場次", "♾️ 無限")
            else:
                used = u.get('free_usage', 0)
                c4.metric("📊 剩餘場次", max(0, limit - used))

            history = u.get('history', [])
            if history:
                st.markdown("**最近 20 次預測記錄：**")
                st.dataframe(pd.DataFrame(history[-20:][::-1]), use_container_width=True)
            else:
                st.info("呢個用戶暫時冇任何預測記錄")

    st.divider()

    # ===== 7. 刪除用戶 =====
    with st.expander("🗑️ 刪除用戶"):
        del_user = st.selectbox("選擇要刪除嘅用戶", list(users.keys()), key="del_user_sel")
        if del_user:
            if del_user == "admin":
                st.warning("⚠️ 唔可以刪除 admin 帳號")
            else:
                confirm = st.checkbox(f"確認刪除 {del_user}？", key="confirm_del")
                if confirm and st.button("🗑️ 確認刪除", key="del_user_btn"):
                    users.pop(del_user)
                    if save_users(users):
                        st.success(f"✅ 用戶 {del_user} 已刪除")
                        st.rerun()

    st.divider()

def admin_downloads():
    st.subheader("📥 下載中心")
    st.divider()

    # ===== users.json =====
    st.markdown("### 👥 用戶名單")
    if os.path.exists("users.json"):
        size = os.path.getsize("users.json") / 1024
        st.caption(f"📁 users.json（{size:.1f} KB）")
        try:
            with open("users.json", "rb") as f:
                data = f.read()
            st.download_button(
                label="📥 下載 users.json",
                data=data,
                file_name="users.json",
                mime="application/json",
                use_container_width=True,
                key="dl_users_json"
            )
        except Exception as e:
            st.error(f"❌ 讀取失敗：{e}")
    else:
        st.info("ℹ️ 未有 users.json")

    st.divider()

# ===== ai_predictions.json =====
    st.markdown("### 🤖 AI 預測記錄")
    if os.path.exists("ai_predictions.json"):
        size = os.path.getsize("ai_predictions.json") / 1024
        st.caption(f"📁 ai_predictions.json（{size:.1f} KB）")
        try:
            with open("ai_predictions.json", "rb") as f:
                data = f.read()
            st.download_button(
                label="📥 下載 ai_predictions.json",
                data=data,
                file_name="ai_predictions.json",
                mime="application/json",
                use_container_width=True,
                key="dl_ai_pred"
            )
        except Exception as e:
            st.error(f"❌ 讀取失敗：{e}")
    else:
        st.info("ℹ️ 未有 ai_predictions.json")

def admin_manage_predictions():
    st.subheader("📊 管理用戶次數")
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return

    sel = st.selectbox("👤 揀用戶", list(users.keys()), key="mp_user")
    if not sel:
        return

    user = users[sel]
    lottery_chances = user.get('lottery_chances', 0)
    cur_bal = user.get('virtual_balance', 0)

    st.info(f"你而家揀緊：**{sel}**　|　🎰 抽獎 {lottery_chances} 次　|　💰 虛擬幣 ${cur_bal:,.0f}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🎰 加抽獎次數**")
        add_lottery = st.number_input("次數", min_value=1, value=1, key="add_lot")
        if st.button("➕ 加抽獎", use_container_width=True, key="do_add_lot"):
            users[sel]['lottery_chances'] = lottery_chances + add_lottery
            save_users(users)
            st.success(f"✅ 已幫 {sel} 加 {add_lottery} 次")
            st.rerun()

    with col2:
        st.markdown("**💰 送虛擬幣**")
        add_coin = st.number_input("金額", min_value=1, value=100, step=100, key="add_coin")
        if st.button("🎁 送幣", use_container_width=True, key="do_add_coin"):
            users[sel]['virtual_balance'] = cur_bal + add_coin
            save_users(users)
            st.success(f"✅ 已送 ${add_coin:,.0f} 俾 {sel}")
            st.rerun()
def admin_analytics():
    st.subheader("📊 數據分析")
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return
    df = pd.DataFrame.from_dict(users, orient='index')
    if 'created_at' in df.columns and HAS_PLOTLY:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.dropna(subset=['created_at'])
        df['date'] = df['created_at'].dt.date
        daily = df.groupby('date').size().reset_index(name='new').sort_values('date')
        daily['cum'] = daily['new'].cumsum()
        fig = px.line(daily, x='date', y=['new', 'cum'], title='用戶增長')
        st.plotly_chart(fig, use_container_width=True)

def admin_course_analysis():
    st.subheader("📊 場地/路程勝率分析")
    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
        df = df.reset_index(drop=True)

        # 名次
        pos_series, pos_name = _get_pos_series(df)
        st.caption(f"📊 使用名次欄位：**{pos_name}**（有效數據：{pos_series.notna().sum()}）")

        # 搵場地欄位
        track_col = None
        for c in df.columns:
            if 'RC/Track' in str(c) or 'track' in str(c).lower() or 'course' in str(c).lower() or '場地' in str(c):
                track_col = c
                break

        # 搵路程欄位
        dist_col = None
        for c in df.columns:
            if str(c).lower() in ['dist.', 'dist', 'distance'] or '路程' in str(c):
                dist_col = c
                break

        st.write(f"**場地欄位**：`{track_col}`　**路程欄位**：`{dist_col}`")

        # ===== 場地分析 =====
        if track_col:
            st.divider()
            st.markdown("### 🏟️ 場地勝率分析")

            temp = df[[track_col]].copy()
            temp.columns = ['場地']
            temp['名次'] = pos_series.values
            temp['場地'] = temp['場地'].astype(str).str.strip()
            temp = temp.dropna(subset=['名次'])
            temp = temp[~temp['場地'].str.lower().isin(['nan', 'none', '', '-'])]

            if not temp.empty:
                total = temp['場地'].value_counts()
                wins = temp[temp['名次'] == 1]['場地'].value_counts()
                stats = pd.DataFrame({'場地': total.index, '總出賽': total.values})
                stats['勝出'] = stats['場地'].map(wins).fillna(0).astype(int)
                stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
                stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)
                stats.index = stats.index + 1
                st.dataframe(stats, use_container_width=True)
            else:
                st.info("冇場地數據")

        # ===== 路程分析 =====
        if dist_col:
            st.divider()
            st.markdown("### 📏 路程勝率分析")

            temp = df[[dist_col]].copy()
            temp.columns = ['路程']
            temp['名次'] = pos_series.values
            temp['路程'] = pd.to_numeric(temp['路程'], errors='coerce')
            temp = temp.dropna(subset=['名次', '路程'])
            temp['路程'] = temp['路程'].astype(int).astype(str) + ' 米'

            if not temp.empty:
                total = temp['路程'].value_counts()
                wins = temp[temp['名次'] == 1]['路程'].value_counts()
                stats = pd.DataFrame({'路程': total.index, '總出賽': total.values})
                stats['勝出'] = stats['路程'].map(wins).fillna(0).astype(int)
                stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
                stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)
                stats.index = stats.index + 1
                st.dataframe(stats, use_container_width=True)
            else:
                st.info("冇路程數據")

        # ===== 場地 + 路程組合 =====
        if track_col and dist_col:
            st.divider()
            st.markdown("### 🎯 場地 × 路程 組合分析")

            temp = df[[track_col, dist_col]].copy()
            temp.columns = ['場地', '路程']
            temp['名次'] = pos_series.values
            temp['場地'] = temp['場地'].astype(str).str.strip()
            temp['路程'] = pd.to_numeric(temp['路程'], errors='coerce')
            temp = temp.dropna(subset=['名次', '路程'])
            temp = temp[~temp['場地'].str.lower().isin(['nan', 'none', '', '-'])]
            temp['路程'] = temp['路程'].astype(int).astype(str) + '米'
            temp['組合'] = temp['場地'] + ' | ' + temp['路程']

            if not temp.empty:
                total = temp['組合'].value_counts()
                wins = temp[temp['名次'] == 1]['組合'].value_counts()
                stats = pd.DataFrame({'場地 | 路程': total.index, '總出賽': total.values})
                stats['勝出'] = stats['場地 | 路程'].map(wins).fillna(0).astype(int)
                stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
                stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)
                stats.index = stats.index + 1
                st.dataframe(stats.head(30), use_container_width=True)
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        import traceback
        st.code(traceback.format_exc())

def admin_monthly_report():
    st.subheader("📅 每月命中率報告")

    # ===== 從 Supabase 讀取預測紀錄 =====
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/predictions?order=date.desc",
            headers=headers,
            timeout=10
        )
        records = res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"❌ 讀取預測紀錄失敗：{e}")
        records = []

    if not records:
        st.info("暫無足夠數據")
        return

    # ===== 讀取賽果 =====
    result_file = "race_results_clean.csv"
    if not os.path.exists(result_file):
        st.info("暫無足夠數據")
        return

    try:
        df_results = pd.read_csv(result_file, encoding='utf-8-sig')
        df_results['horse_name'] = df_results['horse_name'].astype(str).str.strip()
        df_results['horse_name'] = df_results['horse_name'].str.replace(
            r'\s*\([A-Z]\d+\)\s*$', '', regex=True
        ).str.strip()
        df_results['finish_position'] = pd.to_numeric(df_results['finish_position'], errors='coerce')
        df_results['race_no'] = pd.to_numeric(df_results['race_no'], errors='coerce')
        df_results = df_results.dropna(subset=['race_no', 'finish_position'])
        df_results['race_no'] = df_results['race_no'].astype(int)
        df_results['race_date'] = pd.to_datetime(df_results['race_date'], errors='coerce')
    except Exception as e:
        st.error(f"❌ 讀取賽果失敗：{e}")
        return

    # ===== 建立賽果 lookup：(date, race) -> 真實頭 3 名 =====
    results_map = {}
    df_results['date_str'] = df_results['race_date'].dt.strftime('%Y-%m-%d')
    for (date_str, race_no), group in df_results.groupby(['date_str', 'race_no']):
        top3 = group.sort_values('finish_position').head(3)['horse_name'].tolist()
        results_map[(date_str, int(race_no))] = top3

    # ===== 逐條預測計算命中 =====
    rows = []
    for rec in records:
        date_str = str(rec.get('date', '')).strip()
        race_no = rec.get('race')
        if not date_str or race_no is None:
            continue
        try:
            race_no = int(race_no)
        except Exception:
            continue

        horse_list = []
        raw_all = rec.get('all_horses')
        if raw_all:
            try:
                parsed = json.loads(raw_all) if isinstance(raw_all, str) else raw_all
                if isinstance(parsed, list):
                    horse_list = [str(h).strip() for h in parsed if str(h).strip()]
            except Exception:
                pass
        if not horse_list:
            top = rec.get('top_horse')
            if top:
                horse_list = [str(top).strip()]

        key = (date_str, race_no)
        if key not in results_map:
            continue

        top3_real = results_map[key]
        hit_count = sum(1 for h in horse_list[:4] if h in top3_real)
        is_hit = hit_count > 0

        rows.append({'date': date_str, 'is_hit': is_hit})

    if not rows:
        st.info("暫無足夠數據")
        return

    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)

    monthly = df.groupby('month').agg(
        total=('is_hit', 'count'),
        hit=('is_hit', 'sum')
    ).reset_index()
    monthly['hit_rate'] = (monthly['hit'] / monthly['total'] * 100).round(1).astype(str) + '%'
    monthly.columns = ['月份', '預測場次', '命中場次', '命中率']

    st.dataframe(monthly, use_container_width=True, hide_index=True)
def admin_finance():
    st.subheader("💰 財務管理")
    f = load_finance()
    c1, c2, c3 = st.columns(3)
    c1.metric("總收入", f"${f.get('total_income', 0):.2f}")
    c2.metric("本月", f"${f.get('monthly_income', 0):.2f}")
    c3.metric("今年", f"${f.get('yearly_income', 0):.2f}")
    with st.expander("➕ 新增收入"):
        a = st.number_input("金額", min_value=0.0, step=10.0, key="fin_amt")
        d = st.text_input("描述", key="fin_desc")
        if st.button("記錄", key="fin_add"):
            for k in ['total_income', 'monthly_income', 'yearly_income']:
                f[k] = f.get(k, 0) + a
            save_finance(f)
            st.success("✅ 已記錄")
            st.rerun()

def _is_promo_valid(promo):
    if promo.get('used', False):
        return False
    expiry = promo.get('expiry')
    if not expiry:
        return True
    try:
        return datetime.fromisoformat(expiry) >= datetime.now()
    except Exception:
        return False


def admin_promo_codes():
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()

    # ===== 統計 =====
    if promos:
        total = len(promos)
        used = sum(1 for p in promos.values() if p.get('used', False))
        active = sum(1 for p in promos.values() if not p.get('used', False) and _is_promo_valid(p))
        expired = sum(1 for p in promos.values() if not p.get('used', False) and not _is_promo_valid(p))
        total_discount = sum(p.get('discount_amount', 0) for p in promos.values() if p.get('used', False))

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🎟️ 總數", total)
        c2.metric("✅ 已使用", used)
        c3.metric("🟢 有效", active)
        c4.metric("🔴 已過期", expired)
        c5.metric("💰 總折扣", f"${total_discount:.0f}")
    else:
        total = used = active = expired = 0

    st.divider()

    # ===== 產生新優惠碼 =====
    st.subheader("➕ 產生新優惠碼")
    col1, col2, col3 = st.columns(3)
    with col1:
        duration = st.number_input("有效期 (天)", min_value=1, value=30, key="pr_dur")
        quantity = st.number_input("數量", min_value=1, value=1, max_value=100, key="pr_qty")
        dtype = st.selectbox(
            "折扣類型",
            ["percentage", "fixed", "free", "first_order", "min_spend"],
            key="pr_dtype",
            format_func=lambda x: {
                "percentage": "百分比折扣（如 20% off）",
                "fixed": "固定金額（如 -$50）",
                "free": "完全免費",
                "first_order": "首單優惠",
                "min_spend": "滿減（消費滿 X 減 Y）"
            }.get(x, x)
        )
    with col2:
        dval = st.number_input("折扣數值", min_value=0, value=20, key="pr_dval")
        min_spend = st.number_input("最低消費 (滿減用)", min_value=0, value=100, key="pr_minspend")
        max_uses = st.number_input("每人限用次數", min_value=0, value=1, key="pr_maxuses")
    with col3:
        st.write("")
        st.write("")
        note = st.text_input("備註（選填）", key="pr_note")

    if st.button("🎟️ 產生優惠碼", type="primary", use_container_width=True, key="pr_gen"):
        new_codes = []
        for _ in range(int(quantity)):
            code = generate_promo_code()
            promos[code] = {
                "used": False,
                "expiry": (datetime.now() + timedelta(days=duration)).isoformat(),
                "created_at": datetime.now().isoformat(),
                "discount_type": dtype,
                "discount_value": dval,
                "min_spend": min_spend,
                "max_uses_per_user": max_uses,
                "used_by": [],
                "discount_amount": 0,
                "note": note
            }
            new_codes.append(code)
        save_promos(promos)
        st.success(f"✅ 已產生 {len(new_codes)} 個優惠碼！")
        st.code("\n".join(new_codes))
        st.rerun()

    st.divider()

    # ===== 篩選清單 =====
    if promos:
        st.subheader("📋 優惠碼清單")
        filter_option = st.radio(
            "篩選",
            ["全部", "有效", "已使用", "已過期"],
            horizontal=True,
            key="pr_filter"
        )

        filtered = {}
        for code, p in promos.items():
            is_used = p.get('used', False)
            is_valid = _is_promo_valid(p)
            if filter_option == "全部":
                filtered[code] = p
            elif filter_option == "有效" and not is_used and is_valid:
                filtered[code] = p
            elif filter_option == "已使用" and is_used:
                filtered[code] = p
            elif filter_option == "已過期" and not is_used and not is_valid:
                filtered[code] = p

        if filtered:
            rows = []
            for code, p in filtered.items():
                expiry = p.get('expiry', '')
                days_left = "永久"
                if expiry:
                    try:
                        exp_dt = datetime.fromisoformat(expiry)
                        delta = (exp_dt - datetime.now()).days
                        days_left = f"{delta} 天" if delta >= 0 else "已過期"
                    except Exception:
                        pass

                used_by = p.get('used_by', [])
                used_by_str = ", ".join(used_by) if used_by else "-"
                status = "✅ 已使用" if p.get('used', False) else ("🟢 有效" if _is_promo_valid(p) else "🔴 過期")

                rows.append({
                    "優惠碼": code,
                    "類型": p.get('discount_type', ''),
                    "數值": p.get('discount_value', 0),
                    "狀態": status,
                    "剩餘": days_left,
                    "使用者": used_by_str,
                    "備註": p.get('note', '')
                })

            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info(f"冇符合「{filter_option}」嘅優惠碼")

    st.divider()

    # ===== 快速操作 =====
    st.subheader("⚡ 快速操作")
    ca, cb, cc = st.columns(3)
    with ca:
        if st.button("🧹 清理過期優惠碼", use_container_width=True, key="pr_clean"):
            before = len(promos)
            promos = {k: v for k, v in promos.items()
                      if v.get('used', False) or _is_promo_valid(v)}
            save_promos(promos)
            st.success(f"✅ 已清理 {before - len(promos)} 個過期優惠碼")
            st.rerun()
    with cb:
        if promos:
            rows = []
            for code, p in promos.items():
                rows.append({
                    "優惠碼": code,
                    "類型": p.get('discount_type', ''),
                    "數值": p.get('discount_value', 0),
                    "過期日": p.get('expiry', ''),
                    "已使用": p.get('used', False),
                    "備註": p.get('note', '')
                })
            csv = pd.DataFrame(rows).to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下載優惠碼 CSV",
                data=csv,
                file_name=f"promo_codes_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="pr_dl_btn"
            )
    with cc:
        confirm_clear = st.checkbox("確認清空", key="pr_confirm_clear")
        if st.button("🗑️ 清空所有優惠碼", use_container_width=True, key="pr_clear_all"):
            if confirm_clear:
                save_promos({})
                st.success("✅ 已清空所有優惠碼")
                st.rerun()
            else:
                st.warning("請先勾選「確認清空」")
def admin_model_weights():
    st.subheader("⚖️ 模型權重設定")
    st.caption("分開調整沙田 (ST) 同跑馬地 (HV) 嘅模型融合權重，改完即刻生效。")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # 讀取現有權重
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/venue_model_weights?order=venue.asc", headers=headers)
        configs = res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        return

    if not configs:
        st.warning("⚠️ 未有場地權重設定，請先喺 Supabase 建立。")
        return

    # 轉為 dict 方便讀取
    cfg_map = {c['venue']: c for c in configs}

    # ===== 分開兩個 Tab 顯示 =====
    tab_st, tab_hv = st.tabs(["🏇 沙田 (ST)", "🏇 跑馬地 (HV)"])

    for venue, tab in [('ST', tab_st), ('HV', tab_hv)]:
        with tab:
            cfg = cfg_map.get(venue, {})
            current_xgb = float(cfg.get('xgb_weight', 0.30))
            current_cat = float(cfg.get('cat_weight', 0.50))
            current_rank = float(cfg.get('rank_weight', 0.20))

            st.markdown(f"### 📊 {venue} 目前權重")
            c1, c2, c3 = st.columns(3)
            c1.metric("XGBoost", f"{current_xgb:.2f}")
            c2.metric("CatBoost", f"{current_cat:.2f}")
            c3.metric("Ranking", f"{current_rank:.2f}")

            st.divider()

            st.markdown(f"### ✏️ 調整 {venue} 權重")
            new_xgb = st.slider(f"XGBoost 權重 ({venue})", 0.0, 1.0, current_xgb, 0.05, key=f"slider_xgb_{venue}")
            new_cat = st.slider(f"CatBoost 權重 ({venue})", 0.0, 1.0, current_cat, 0.05, key=f"slider_cat_{venue}")
            new_rank = st.slider(f"Ranking 權重 ({venue})", 0.0, 1.0, current_rank, 0.05, key=f"slider_rank_{venue}")

            total = new_xgb + new_cat + new_rank
            if abs(total - 1.0) > 0.01:
                st.warning(f"⚠️ 三個權重加埋係 {total:.2f}，必須等於 1.0 先可以儲存。")
            else:
                st.success(f"✅ 權重總和：{total:.2f}（正確）")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"💾 儲存 {venue} 權重", type="primary", use_container_width=True,
                             disabled=(abs(total - 1.0) > 0.01), key=f"save_{venue}"):
                    try:
                        requests.patch(
                            f"{SUPABASE_URL}/rest/v1/venue_model_weights?venue=eq.{venue}",
                            headers=headers,
                            json={
                                "xgb_weight": new_xgb,
                                "cat_weight": new_cat,
                                "rank_weight": new_rank,
                                "updated_at": datetime.now().isoformat()
                            }
                        )
                        st.success(f"✅ 已更新 {venue}：XGB {new_xgb:.2f} / Cat {new_cat:.2f} / Rank {new_rank:.2f}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"儲存失敗：{e}")

            with col2:
                if st.button(f"🔄 重設 {venue} 為預設", use_container_width=True, key=f"reset_{venue}"):
                    try:
                        requests.patch(
                            f"{SUPABASE_URL}/rest/v1/venue_model_weights?venue=eq.{venue}",
                            headers=headers,
                            json={"xgb_weight": 0.30, "cat_weight": 0.50, "rank_weight": 0.20}
                        )
                        st.success(f"✅ 已重設 {venue} 為預設值")
                        st.rerun()
                    except Exception as e:
                        st.error(f"重設失敗：{e}")
def admin_accuracy_monitor():
    st.subheader("📈 AI 預測準確率監控（頭 3 名）")

    from database import load_predictions
    ai_data = load_predictions()

    if not ai_data:
        st.warning("⚠️ 未有 AI 預測記錄")
        return

    st.info(f"📊 總共 {len(ai_data)} 個預測記錄")

    result_file = "race_results_clean.csv"
    if not os.path.exists(result_file):
        st.warning("⚠️ 未有賽果檔案")
        return

    try:
        results_df = pd.read_csv(result_file, encoding='utf-8-sig')
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
        results_df = results_df.dropna(subset=['race_date'])
        results_df['race_date_str'] = results_df['race_date'].dt.strftime('%Y-%m-%d')
        results_df['race_no'] = pd.to_numeric(results_df['race_no'], errors='coerce')
        results_df['finish_position'] = pd.to_numeric(results_df['finish_position'], errors='coerce')
        results_df['horse_name'] = results_df['horse_name'].astype(str).str.strip()
        results_df['horse_name'] = results_df['horse_name'].str.replace(r'\([A-Z]\d+\)', '', regex=True).str.strip()
        
        # 👇👇👇 新增：如果 CSV 冇場地欄位，自動根據日期推算 👇👇👇
        if 'venue' not in results_df.columns and 'racecourse' not in results_df.columns and '馬場' not in results_df.columns:
            # 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
            results_df['venue'] = results_df['race_date'].apply(
                lambda d: 'HV' if d.weekday() == 2 else ('ST' if d.weekday() in [5, 6] else '未知')
            )
        else:
            # 如果有現成欄位，就直接用
            for col in ['venue', 'racecourse', '馬場']:
                if col in results_df.columns:
                    results_df['venue'] = results_df[col]
                    break
        # 👆👆👆 新增部分完結 👆👆👆
                
    except Exception as e:
        st.error(f"❌ 讀取賽果失敗：{e}")
        return

    real_top3 = {}
    venue_map = {}
    
    for _, row in results_df.iterrows():
        if pd.isna(row['race_no']) or pd.isna(row['finish_position']):
            continue
        key = f"{row['race_date_str']}_{int(row['race_no'])}"
        
        # 記錄場地
        if key not in venue_map:
            venue_map[key] = row.get('venue', '未知')
        
        if key not in real_top3:
            real_top3[key] = []
        if row['finish_position'] <= 3:
            real_top3[key].append({
                'horse': row['horse_name'],
                'pos': int(row['finish_position'])
            })

    compare_rows = []
    combo_hit = 0
    total_with_result = 0
    pending_count = 0
    horse_hit = 0
    horse_total = 0

    for key, pred in ai_data.items():
        date_str = pred.get('date')
        race_no = pred.get('race')
        all_horses = pred.get('all_horses', [])

        pred_top3 = all_horses[:3] if len(all_horses) >= 3 else all_horses
        pred_top3_str = ", ".join(pred_top3)

        lookup_key = f"{date_str}_{race_no}"
        current_venue = venue_map.get(lookup_key, '未知')
        
        if lookup_key not in real_top3 or not real_top3[lookup_key]:
            compare_rows.append({
                '日期': date_str,
                '場次': race_no,
                '場地': current_venue,
                '預測頭3名': pred_top3_str,
                '真實頭3名': '⏳ 未有賽果',
                '命中數': '-',
                '結果': '⏳ 待定'
            })
            pending_count += 1
            continue

        real_top3_list = real_top3[lookup_key]
        real_names = [r['horse'] for r in real_top3_list]
        real_str = ", ".join([f"{r['horse']}({r['pos']})" for r in real_top3_list])

        hits = [h for h in pred_top3 if h in real_names]
        hit_count = len(hits)

        total_with_result += 1
        horse_total += len(pred_top3)
        horse_hit += hit_count

        if hit_count > 0:
            combo_hit += 1
            result_str = f"✅ 命中 {hit_count} 匹"
        else:
            result_str = "❌ 全部失準"

        compare_rows.append({
            '日期': date_str,
            '場次': race_no,
            '場地': current_venue,
            '預測頭3名': pred_top3_str,
            '真實頭3名': real_str,
            '命中數': hit_count,
            '結果': result_str
        })

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📊 總預測", len(ai_data))
    c2.metric("✅ 已比對", total_with_result)
    c3.metric("🎯 命中場次", combo_hit)
    if total_with_result > 0:
        combo_rate = combo_hit / total_with_result
        c4.metric("📈 場次命中率", f"{combo_rate:.1%}")
    else:
        c4.metric("📈 場次命中率", "N/A")

    if horse_total > 0:
        st.metric(
            "🐎 馬匹命中率（預測頭3名中，有幾多匹跑入真實頭3名）",
            f"{horse_hit}/{horse_total} = {horse_hit/horse_total:.1%}"
        )

    if pending_count > 0:
        st.caption(f"⏳ 仲有 {pending_count} 場未出賽果")
        
    # ===== 分場地命中率 =====
    st.markdown("---")
    st.subheader("📍 分場地命中率")
    venue_stats = {}
    for row in compare_rows:
        v = row['場地']
        if row['結果'] == '⏳ 待定':
            continue
        if v not in venue_stats:
            venue_stats[v] = {'total': 0, 'hit': 0}
        venue_stats[v]['total'] += 1
        if row['命中數'] != '-' and int(row['命中數']) > 0:
            venue_stats[v]['hit'] += 1
            
    if venue_stats:
        vc1, vc2 = st.columns(2)
        for idx, (v, stats) in enumerate(venue_stats.items()):
            if stats['total'] > 0:
                rate = stats['hit'] / stats['total']
                if idx == 0:
                    vc1.metric(f"{v} 命中率", f"{rate:.1%}", f"{stats['hit']}/{stats['total']} 場")
                else:
                    vc2.metric(f"{v} 命中率", f"{rate:.1%}", f"{stats['hit']}/{stats['total']} 場")
    else:
        st.info("暫時未有足夠數據計算分場地命中率")
        
    # ===== 命中率走勢圖 =====
    st.markdown("---")
    st.subheader("📉 命中率走勢圖")
    if compare_rows:
        df_trend = pd.DataFrame(compare_rows)
        df_trend = df_trend[df_trend['結果'] != '⏳ 待定']
        
        if not df_trend.empty:
            trend_data = []
            for date, group in df_trend.groupby('日期'):
                total = len(group)
                hit_races = len(group[group['命中數'].apply(lambda x: int(x) if str(x).isdigit() else 0) > 0])
                if total > 0:
                    trend_data.append({
                        '日期': date,
                        '場次命中率': hit_races / total
                    })
            
            df_trend_final = pd.DataFrame(trend_data).sort_values('日期')
            fig = px.line(df_trend_final, x='日期', y='場次命中率', markers=True, title='每日場次命中率走勢')
            fig.update_layout(yaxis_tickformat='.0%', xaxis_title='日期', yaxis_title='命中率')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無足夠數據顯示走勢圖")

    # ===== 明細表 =====
    if compare_rows:
        st.subheader("📋 預測頭3名 vs 真實頭3名")
        df = pd.DataFrame(compare_rows).sort_values(['日期', '場次'], ascending=[False, True])

        def _color(row):
            if row['結果'] == '⏳ 待定':
                return ['background-color: #fff3cd'] * len(row)
            elif '✅' in str(row['結果']):
                return ['background-color: #d4edda'] * len(row)
            else:
                return ['background-color: #f8d7da'] * len(row)

        st.dataframe(df.style.apply(_color, axis=1), use_container_width=True, hide_index=True)

    # ===== 7. 管理員操作 =====
    st.divider()
    st.subheader("🔧 管理操作")
    if st.button("🔄 重新整理", use_container_width=True, key="refresh_acc"):
        st.rerun()

def admin_subscription():
    st.subheader("⏰ 訂閱管理")
    users = load_users()
    paid = {u: d for u, d in users.items() if d.get('is_paid', False) or d.get('group') in ['VIP', 'super_admin']}
    if not paid:
        st.info("暫無付費用戶")
    else:
        df = pd.DataFrame.from_dict(paid, orient='index')
        for c in ['is_paid', 'group', 'plan', 'paid_date', 'expiry_date']:
            if c not in df.columns:
                df[c] = None
        st.dataframe(df[['is_paid', 'group', 'plan', 'paid_date', 'expiry_date']], use_container_width=True)
    st.divider()
    if st.button("🔍 檢查並終止過期會員", key="check_exp"):
        users = load_users()
        today = datetime.now()
        exp = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    if pd.to_datetime(u['expiry_date']) < today:
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        u['plan'] = None
                        exp.append(uid)
                except Exception:
                    pass
        if exp:
            save_users(users)
            st.success(f"✅ 已降級 {len(exp)} 位：{', '.join(exp)}")
        else:
            st.info("✅ 沒有過期會員")

def admin_payment_review():
    st.subheader("📤 付款審核")
    pending = get_all_pending_requests()
    if not pending:
        st.info("✅ 目前沒有待審核付款")
        return
    for item in pending:
        u = item['username']
        req = item['request']
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        c1.write(f"👤 **{u}**")
        c2.write(f"📌 {req.get('plan_name')}　💰 ${req.get('final_price')}")
        if c3.button("✅ 批准", key=f"ap_{req.get('id')}"):
            ok, msg = approve_payment_request(u, req['id'], st.session_state.get('username', 'admin'))
            if ok:
                st.success(msg)
            else:
                st.error(msg)
            st.rerun()
        if c4.button("❌ 拒絕", key=f"rj_{req.get('id')}"):
            ok, msg = reject_payment_request(u, req['id'], st.session_state.get('username', 'admin'))
            if ok:
                st.warning(msg)
            else:
                st.error(msg)
            st.rerun()
        st.divider()
def admin_user_activity():
    st.subheader("👤 用戶記錄")
    st.caption("記錄用戶嘅登入、預測、抽獎、購買、付款等活動。")

    log_file = "user_activity_log.json"

    if not os.path.exists(log_file):
        st.info("📭 暫無任何用戶活動記錄")
        return

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return

    records = data.get("records", [])
    if not records:
        st.info("📭 暫無任何用戶活動記錄")
        return

    st.markdown("### 📊 活動統計")
    df_all = pd.DataFrame(records)
    c1, c2, c3 = st.columns(3)
    c1.metric("📋 總記錄數", len(df_all))
    c2.metric("👥 活躍用戶", df_all['username'].nunique())
    today_str = datetime.now().strftime('%Y-%m-%d')
    c3.metric("📅 今日記錄", len(df_all[df_all['time'].str.startswith(today_str)]))

    st.divider()
    st.markdown("### 🔍 篩選")

    col1, col2, col3 = st.columns(3)
    with col1:
        user_filter = st.selectbox(
            "選擇用戶",
            ["全部"] + sorted(df_all['username'].unique().tolist()),
            key="act_user_filter"
        )
    with col2:
        action_filter = st.selectbox(
            "活動類型",
            ["全部"] + sorted(df_all['action'].unique().tolist()),
            key="act_action_filter"
        )
    with col3:
        limit = st.number_input("顯示最近幾多條", min_value=10, max_value=5000, value=100, step=10, key="act_limit")

    df_filtered = df_all.copy()
    if user_filter != "全部":
        df_filtered = df_filtered[df_filtered['username'] == user_filter]
    if action_filter != "全部":
        df_filtered = df_filtered[df_filtered['action'] == action_filter]

    df_filtered = df_filtered.tail(int(limit)).iloc[::-1].reset_index(drop=True)
    df_filtered.index = df_filtered.index + 1

    st.write(f"**顯示 {len(df_filtered)} 條記錄**")

    df_display = df_filtered[['time', 'username', 'action', 'detail']].copy()
    df_display.columns = ['時間', '用戶', '活動', '詳情']
    st.dataframe(df_display, use_container_width=True)

    csv_data = df_display.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載用戶記錄 CSV",
        data=csv_data,
        file_name=f"user_activity_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_user_activity"
    )

def admin_monitoring():
    st.subheader("📡 系統監控")
    files = ['ALL_DATA_MERGED.csv', 'HKCJ_FULL_YEAR_DATA.csv', 'users.json',
             'system_config.json', 'accuracy.json', 'lottery_config.json']
    for f in files:
        if os.path.exists(f):
            st.success(f"✅ {f} ({os.path.getsize(f)/1024:.1f} KB)")
        else:
            st.error(f"❌ {f} 不存在")

def admin_content():
    st.subheader("📝 內容管理")
    content = load_json(CONTENT_FILE)
    with st.expander("📢 發佈公告"):
        t = st.text_input("標題", key="ct_title")
        x = st.text_area("內容", key="ct_txt")
        if st.button("📤 發佈", key="ct_pub"):
            if 'announcements' not in content:
                content['announcements'] = []
            content['announcements'].append({
                "id": len(content['announcements']) + 1,
                "title": t, "content": x,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "status": "active"
            })
            save_json(CONTENT_FILE, content)
            st.success("✅ 已發佈")
            st.rerun()
def cleanup_activity_log(days=30):
    """清理超過 N 日嘅用戶活動日誌"""
    log_file = "user_activity_log.json"
    if not os.path.exists(log_file):
        return 0

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return 0

    records = data.get("records", [])
    if not records:
        return 0

    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)

    kept = []
    removed = 0
    for r in records:
        try:
            t = datetime.strptime(r.get("time", ""), "%Y-%m-%d %H:%M:%S")
            if t >= cutoff:
                kept.append(r)
            else:
                removed += 1
        except Exception:
            kept.append(r)

    if removed > 0:
        data["records"] = kept
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return removed


def cleanup_expired_promos():
    """清理過期優惠碼"""
    promo_file = "promo_codes.json"
    if not os.path.exists(promo_file):
        return 0

    try:
        with open(promo_file, 'r', encoding='utf-8') as f:
            promos = json.load(f)
    except Exception:
        return 0

    if not promos:
        return 0

    from datetime import datetime
    today = datetime.now()
    kept = {}
    removed = 0

    for code, info in promos.items():
        try:
            expiry_str = info.get("expiry", "")
            if expiry_str:
                expiry = pd.to_datetime(expiry_str)
                if expiry < today:
                    removed += 1
                    continue
            kept[code] = info
        except Exception:
            kept[code] = info

    if removed > 0:
        try:
            with open(promo_file, 'w', encoding='utf-8') as f:
                json.dump(kept, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return removed


def admin_auto_maintenance():
    st.subheader("🤖 自動維護")
    if st.button("🚀 執行維護", type="primary", use_container_width=True, key="run_maint"):
        users = load_users()
        today = datetime.now()
        exp = []
        for uid, u in users.items():
            if u.get('group') == 'VIP' and u.get('expiry_date'):
                try:
                    if pd.to_datetime(u['expiry_date']) < today:
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        exp.append(uid)
                except Exception:
                    pass
        if exp:
            save_users(users)

        # 清理活動日誌
        removed_logs = cleanup_activity_log(days=30)

        # 清理過期優惠碼
        removed_promos = cleanup_expired_promos()

        # 顯示結果
        st.success(f"✅ 維護完成")
        st.write(f"   - 過期 VIP：{len(exp)} 位降級")
        st.write(f"   - 舊活動日誌：{removed_logs} 條清理")
        st.write(f"   - 過期優惠碼：{removed_promos} 個清理")

def admin_automation():
    st.subheader("🤖 自動化工具")
    st.markdown("### ⚙️ 自動化排程")
    st.info("以下自動化任務由 GitHub Actions 定時執行，唔需要人手操作。")

    automation_data = [
        {"Workflow": "retrain_models.yml", "執行時間": "每星期日 08:00", "用途": "自動重新訓練 AI 模型"},
        {"Workflow": "update_results.yml", "執行時間": "星期日/一/四 08:00", "用途": "自動爬取賽果"},
        {"Workflow": "update_racecard.yml", "執行時間": "星期三 17:00、星期六日 11:00", "用途": "自動爬取排位表"},
        {"Workflow": "update_ai_accuracy.yml", "執行時間": "每日 20:00", "用途": "自動更新 AI 命中率"},
    ]
    st.dataframe(automation_data, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("💡 提示：如果想手動觸發，可以喺 GitHub 倉庫嘅 Actions 頁面撳 Run workflow。")

def admin_security():
    st.subheader("🔐 安全與權限")
    
    import os, json
    log_file = "admin_log.json"
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if logs:
                st.markdown("### 📋 管理員操作日誌")
                df_logs = pd.DataFrame(logs)
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.info("📭 暫無操作記錄。")
        except Exception as e:
            st.warning(f"讀取日誌時出錯：{e}")
    else:
        st.info("📭 暫無日誌檔案。")
def admin_reward_management():
    st.subheader("❤️ 打賞管理")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    tab1, tab2 = st.tabs(["📋 未收款", "📋 已收款"])

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/reward_history?order=rewarded_at.desc&limit=100",
            headers=headers,
            timeout=10
        )
        records = res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"讀取打賞記錄失敗：{e}")
        records = []

    if not records:
        st.info("暫無打賞記錄。")
        return

    df = pd.DataFrame(records)
    if 'status' not in df.columns:
        df['status'] = 'pending'

    pending = df[df['status'] == 'pending']
    approved = df[df['status'] == 'approved']

    # ===== Tab 1：未收款 =====
    with tab1:
        st.caption("未收款打賞紀錄。撳「✅ 已收款」標記為已處理（唔會加 VIP）。")
        if pending.empty:
            st.info("暫無未收款打賞。")
        else:
            h1, h2, h3, h4 = st.columns([2, 1, 2, 1])
            h1.markdown("**用戶名**")
            h2.markdown("**金額**")
            h3.markdown("**提交時間**")
            h4.markdown("**操作**")
            st.divider()

            for _, row in pending.iterrows():
                c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
                c1.write(f"{row.get('username', '未知')}")
                c2.write(f"${float(row.get('amount', 0) or 0):.0f}")
                c3.write(f"{str(row.get('rewarded_at', ''))[:16]}")
                if c4.button("✅ 已收款", key=f"mark_paid_{row['id']}", use_container_width=True):
                    try:
                        patch_res = requests.patch(
                            f"{SUPABASE_URL}/rest/v1/reward_history?id=eq.{row['id']}",
                            headers=headers,
                            json={"status": "approved"},
                            timeout=10
                        )
                        if patch_res.status_code in (200, 204):
                            st.success(f"已標記 {row.get('username', '')} 為已收款")
                            st.rerun()
                        else:
                            st.error(f"標記失敗 (HTTP {patch_res.status_code})：{patch_res.text}")
                    except Exception as e:
                        st.error(f"連線錯誤：{e}")

    # ===== Tab 2：已收款 =====
    with tab2:
        st.caption("已收款打賞紀錄。")
        if approved.empty:
            st.info("暫無已收款紀錄。")
        else:
            display_cols = [c for c in ['username', 'amount', 'rewarded_at'] if c in approved.columns]
            st.dataframe(
                approved[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "username": st.column_config.TextColumn("用戶名"),
                    "amount": st.column_config.NumberColumn("金額", format="$%.0f"),
                    "rewarded_at": st.column_config.TextColumn("提交時間"),
                }
            )
def admin_pool_config():
    st.subheader("🎯 彩池設定")
    st.caption("可以獨立開關每個彩池，同設定最低會員級別。")

    config = load_system_config()
    pool_config = config.get('pool_config', {})

    # 如果未有彩池設定，用預設值
    if not pool_config:
        pool_config = {
            "win": {"enabled": True, "required_group": "free", "label": "獨贏"},
            "place": {"enabled": True, "required_group": "free", "label": "位置"},
            "quinella": {"enabled": True, "required_group": "free", "label": "連贏"},
            "quinella_place": {"enabled": True, "required_group": "free", "label": "位置Q"},
            "tierce": {"enabled": True, "required_group": "paid", "label": "三重彩"},
            "trio": {"enabled": True, "required_group": "paid", "label": "單T"},
            "quartet": {"enabled": True, "required_group": "VIP", "label": "四重彩"},
            "exacta": {"enabled": True, "required_group": "VIP", "label": "二重彩"},
            "first4": {"enabled": True, "required_group": "VIP", "label": "四連環"},
            "double": {"enabled": True, "required_group": "VIP", "label": "孖寶"},
            "treble": {"enabled": True, "required_group": "VIP", "label": "三寶"},
            "six_up": {"enabled": True, "required_group": "VIP", "label": "六環彩"},
        }

    st.markdown("### 📊 彩池列表")

    # 顯示表格式設定
    updated_config = {}

    for key, cfg in pool_config.items():
        col1, col2, col3 = st.columns([2, 1, 2])

        with col1:
            st.markdown(f"**{cfg.get('label', key)}**")
            st.caption(f"`{key}`")

        with col2:
            enabled = st.checkbox(
                "啟用",
                value=cfg.get('enabled', True),
                key=f"pool_enabled_{key}"
            )

        with col3:
            group_options = ['free', 'paid', 'VIP']
            group_labels = {
                'free': '🆓 普通用戶',
                'paid': '💰 付費用戶（日/月）',
                'VIP': '👑 VIP / 季費 / 年費'
            }
            current_group = cfg.get('required_group', 'free')
            if current_group not in group_options:
                current_group = 'free'
            required_group = st.selectbox(
                "最低會員級別",
                group_options,
                index=group_options.index(current_group),
                format_func=lambda x: group_labels[x],
                key=f"pool_group_{key}"
            )

        updated_config[key] = {
            "enabled": enabled,
            "required_group": required_group,
            "label": cfg.get('label', key)
        }

        st.divider()

    if st.button("💾 儲存彩池設定", type="primary", use_container_width=True, key="save_pool_cfg"):
        config['pool_config'] = updated_config
        if save_system_config(config):
            st.success("✅ 彩池設定已儲存！")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 儲存失敗")


def _get_pool_config_default():
    """回傳預設彩池設定"""
    return {
        "win": {"enabled": True, "required_group": "free", "label": "獨贏"},
        "place": {"enabled": True, "required_group": "free", "label": "位置"},
        "quinella": {"enabled": True, "required_group": "free", "label": "連贏"},
        "quinella_place": {"enabled": True, "required_group": "free", "label": "位置Q"},
        "tierce": {"enabled": True, "required_group": "paid", "label": "三重彩"},
        "trio": {"enabled": True, "required_group": "paid", "label": "單T"},
        "quartet": {"enabled": True, "required_group": "VIP", "label": "四重彩"},
        "exacta": {"enabled": True, "required_group": "VIP", "label": "二重彩"},
        "first4": {"enabled": True, "required_group": "VIP", "label": "四連環"},
        "double": {"enabled": True, "required_group": "VIP", "label": "孖寶"},
        "treble": {"enabled": True, "required_group": "VIP", "label": "三寶"},
        "six_up": {"enabled": True, "required_group": "VIP", "label": "六環彩"},
    }

def admin_system_settings():
    st.subheader("⚙️ 系統設定")
    config = load_system_config()
    c1, c2 = st.columns(2)
    with c1:
        er = st.checkbox("開放註冊", value=config.get("enable_registration", True), key="s_er")
        ep = st.checkbox("啟用付款", value=config.get("enable_payment", True), key="s_ep")
        ea = st.checkbox("啟用後台", value=config.get("enable_admin", True), key="s_ea")
        el = st.checkbox("啟用抽獎", value=config.get("enable_lottery", True), key="s_el")
        es = st.checkbox("啟用商城", value=config.get("enable_shop", True), key="s_es")
        pd_ = st.number_input("日費", min_value=0, value=_safe_int(config.get("price_day", 18), 18), step=1, key="s_pd")
        pm = st.number_input("月費", min_value=0, value=_safe_int(config.get("price_month", 128), 128), step=1, key="s_pm")
        pq = st.number_input("季費", min_value=0, value=_safe_int(config.get("price_quarter", 328), 328), step=1, key="s_pq")
    with c2:
        fl = st.number_input("免費預測次數", min_value=0, value=_safe_int(config.get("free_limit", 2), 2), step=1, key="s_fl")
        cur = st.text_input("貨幣單位", value=config.get("currency", "HKD"), key="s_cur")
        ap = st.text_input("管理員密碼", value=config.get("admin_password", ""), type="password", key="s_ap")
        vc = st.checkbox("啟用虛擬幣", value=config.get("virtual_coin_enabled", True), key="s_vc")
        dvc = st.number_input("每日派幣", min_value=0, value=_safe_int(config.get("daily_virtual_coin", 1000), 1000), step=100, key="s_dvc")
    if st.button("💾 儲存設定", type="primary", key="save_sys"):
        merged = dict(config)
        merged.update({
            "enable_registration": er, "enable_payment": ep, "enable_admin": ea,
            "enable_lottery": el, "enable_shop": es,
            "price_day": pd_, "price_month": pm, "price_quarter": pq,
            "free_limit": fl, "currency": cur,
            "admin_password": ap, "virtual_coin_enabled": vc,
            "daily_virtual_coin": dvc
        })
        if save_system_config(merged):
            st.success("✅ 已儲存！")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 儲存失敗")

def admin_page():
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.title("🔐 後台管理 - 身份驗證")
        pw = st.text_input("管理員密碼", type="password", key="adm_pw")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔓 解鎖後台", type="primary", key="unlock"):
                if pw == CONFIG["admin_password"]:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_username = "admin"
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤！")
        with c2:
            if st.button("⬅️ 返回主頁", key="back_home"):
                st.session_state.show_admin = False
                st.rerun()
        return

    st.title("🔐 後台管理")
    st.info(f"👤 管理員：{st.session_state.get('admin_username', 'admin')}")
    if st.button("🚪 登出後台", key="logout_adm"):
        st.session_state.admin_authenticated = False
        st.session_state.show_admin = False
        st.rerun()
    st.divider()

    tabs_def = [
        ("📊 儀表板", admin_dashboard),
        ("👥 用戶管理", admin_user_management),
        ("📥 下載中心", admin_downloads),
        ("📊 次數管理", admin_manage_predictions),
        ("📊 數據分析", admin_analytics),
        ("🏇 馬匹排行榜", admin_horse_ranking),
        ("👨‍🏫 騎師排行榜", admin_jockey_ranking),
        ("👨‍🏫 練馬師排行榜", admin_trainer_ranking),
        ("📊 場地/路程分析", admin_course_analysis),
        ("📅 每月報告", admin_monthly_report),
        ("💰 財務", admin_finance),
        ("🎟️ 優惠碼", admin_promo_codes),
        ("📈 預測監控", admin_accuracy_monitor),
        ("⏰ 訂閱管理", admin_subscription),
        ("❤️ 打賞管理", admin_reward_management),
        ("📡 監控", admin_monitoring),
        ("📝 內容", admin_content),
        ("🤖 自動維護", admin_auto_maintenance),
        ("⚖️ 模型權重", admin_model_weights),
        ("🤖 自動化", admin_automation),
        ("🔐 安全", admin_security),
        ("👤 用戶記錄", admin_user_activity),
        ("🎰 抽獎設定", admin_lottery_config),
        ("🛒 商城設定", admin_shop_config),
        ("🎯 彩池設定", admin_pool_config),
        ("⚙️ 系統設定", admin_system_settings),
    ]

    tabs = st.tabs([t[0] for t in tabs_def])
    for i, (name, fn) in enumerate(tabs_def):
        with tabs[i]:
            try:
                fn()
            except Exception as e:
                st.error(f"⚠️ 呢個分頁載入失敗：{e}")
                import traceback
                st.code(traceback.format_exc())

def display_race_calendar():
    try:
        hk_tz = pytz.timezone("Asia/Hong_Kong")
        now_hk = datetime.now(hk_tz)
        wd = now_hk.weekday()
        target = None
        rn = ""
        vn = ""

        if wd == 2:
            rt = now_hk.replace(hour=19, minute=15, second=0, microsecond=0)
            if now_hk < rt:
                target, rn, vn = rt, "跑馬地夜馬", "HV"
        elif wd == 6:
            rt = now_hk.replace(hour=12, minute=30, second=0, microsecond=0)
            if now_hk < rt:
                target, rn, vn = rt, "沙田日馬", "ST"

        if target is None:
            for i in range(1, 8):
                fut = now_hk + timedelta(days=i)
                if fut.weekday() == 2:
                    target = fut.replace(hour=19, minute=15, second=0, microsecond=0)
                    rn, vn = "跑馬地夜馬", "HV"
                    break
                elif fut.weekday() == 6:
                    target = fut.replace(hour=12, minute=30, second=0, microsecond=0)
                    rn, vn = "沙田日馬", "ST"
                    break

        if not target:
            st.info("📅 暫無未來賽事資料")
            return

        ts = int((target - now_hk).total_seconds())
        if ts <= 0:
            st.success(f"🏇 **{rn}** 已經開始！")
            return

        d = ts // 86400
        h = (ts % 86400) // 3600
        m = (ts % 3600) // 60
        s = ts % 60
        is_today = (target.date() == now_hk.date())
        bg = "linear-gradient(135deg, #ff6b6b, #ee5a24)" if is_today else "linear-gradient(135deg, #667eea, #764ba2)"
        title = f"🔥 今日有賽事！{rn}" if is_today else f"⏰ 距離下場賽事：{rn}"

        st.markdown(f"""
        <div style="background:{bg};padding:20px 24px;border-radius:16px;color:white;box-shadow:0 6px 20px rgba(102,126,234,0.35);margin-bottom:16px;">
            <div style="font-size:15px;opacity:0.9;margin-bottom:8px;">{title}</div>
            <div style="display:flex;gap:16px;align-items:baseline;flex-wrap:wrap;">
                <div style="text-align:center;"><div style="font-size:42px;font-weight:800;">{d}</div><div style="font-size:12px;opacity:0.8;">日</div></div>
                <div style="text-align:center;"><div style="font-size:42px;font-weight:800;">{h:02d}</div><div style="font-size:12px;opacity:0.8;">時</div></div>
                <div style="text-align:center;"><div style="font-size:42px;font-weight:800;">{m:02d}</div><div style="font-size:12px;opacity:0.8;">分</div></div>
                <div style="text-align:center;"><div style="font-size:42px;font-weight:800;">{s:02d}</div><div style="font-size:12px;opacity:0.8;">秒</div></div>
            </div>
            <div style="font-size:13px;opacity:0.85;margin-top:10px;">📍 {target.strftime('%Y年%m月%d日 %H:%M')} · {vn}</div>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"⚠️ 倒數計時器失敗：{e}")
def check_session_timeout():
    """檢查 session 是否超時"""
    if not st.session_state.get('logged_in', False):
        return

    timeout_minutes = CONFIG.get("session_timeout_minutes", 60)
    now = datetime.now()
    last = st.session_state.get('_last_activity')

    if last is None:
        st.session_state._last_activity = now
        return

    try:
        last_dt = datetime.fromisoformat(last) if isinstance(last, str) else last
        elapsed = (now - last_dt).total_seconds() / 60
    except Exception:
        st.session_state._last_activity = now
        return

    if elapsed > timeout_minutes:
        for k in ['logged_in', 'username', 'role', '_last_activity']:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state._timeout_message = f"⏰ 你已閒置超過 {timeout_minutes} 分鐘，已自動登出"
        st.rerun()

    st.session_state._last_activity = now

def login_page():
    st.title("🔐 登入 / 註冊")

    # 🛡️ 顯示超時訊息
    if st.session_state.get('_timeout_message'):
        st.warning(st.session_state._timeout_message)
        del st.session_state._timeout_message

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔑 登入", use_container_width=True, key="pg_login"):
            st.session_state.page_mode = "login"
    with c2:
        if st.button("📝 註冊", use_container_width=True, key="pg_reg"):
            st.session_state.page_mode = "register"

    mode = st.session_state.get("page_mode", "login")

    if mode == "login":
        with st.form("login_form"):
            u = st.text_input("用戶名稱", key="login_user")
            p = st.text_input("密碼", type="password", key="login_pass")
            if st.form_submit_button("登入"):
                user = authenticate(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state._last_activity = datetime.now()
                    log_user_activity(u, "登入", "登入成功")
                    st.session_state.role = user.get('group', 'free')
                    st.rerun()
                else:
                    st.error("❌ 用戶名或密碼錯誤")
    else:
        st.subheader("📝 註冊新帳號")
        with st.form("register_form"):
            new_user = st.text_input("用戶名稱（最少 3 個字）", key="reg_user")
            phone = st.text_input("手機號碼（可選）", key="reg_phone")
            new_pass = st.text_input("密碼", type="password", key="reg_pass")
            new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")

            # ===== 邀請碼 =====
            if CONFIG.get("enable_invite_reward", True):
                invite_code_input = st.text_input(
                    "邀請碼（如有）",
                    key="reg_invite_code",
                    placeholder="輸入朋友嘅邀請碼，雙方都會獲得獎勵"
                )
            else:
                invite_code_input = None

            agree_terms = st.checkbox("✅ 我已閱讀並同意服務條款", key="agree_terms")
            submitted = st.form_submit_button("註冊")

            if submitted:
                if len(new_user) < 3:
                    st.error("❌ 用戶名稱至少 3 個字")
                elif new_pass != new_pass2:
                    st.error("❌ 密碼不一致")
                elif len(new_pass) < 4:
                    st.error("❌ 密碼至少 4 個字")
                elif not agree_terms:
                    st.error("❌ 請同意服務條款")
                else:
                    users = load_users()

                    # ===== 驗證邀請碼 =====
                    invited_by = None
                    if CONFIG.get("enable_invite_reward", True) and invite_code_input:
                        invite_code_input = invite_code_input.strip().upper()
                        for uid, u in users.items():
                            if u.get('invite_code', '').upper() == invite_code_input:
                                invited_by = uid
                                break
                        if not invited_by:
                            st.error("❌ 邀請碼無效，請確認後再試")
                            st.stop()

                    if new_user in users:
                        st.error("❌ 用戶名稱已被使用")
                    else:
                        # ===== 建立新用戶 =====
                        users[new_user] = {
                            'password': hash_password(new_pass),
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
                            'predictions_limit': CONFIG.get("free_limit", 10),
                            'history': [],
                            'terms_agreed': datetime.now().isoformat(),
                            'invite_code': new_user.upper() + str(random.randint(100, 999)),
                            'invited_by': invited_by,
                            'invite_rewards': 0,
                            'invite_count': 0,
                            'referred_users': [],
                            'level': '🥉 銅牌會員',
                            'exp': 0,
                            'badges': [],
                            'virtual_balance': CONFIG.get('daily_virtual_coin', 1000),
                            'last_claim_date': '',
                            'bets': [],
                            'last_lottery_date': ''
                        }

                        # ===== 多級獎勵回溯 =====
                        if invited_by and CONFIG.get("enable_invite_reward", True):
                            rewards = CONFIG.get("invite_rewards", {"level1": 5, "level2": 2, "level3": 1})

                            # Level 1：直接邀請人
                            inviter = users.get(invited_by)
                            if inviter:
                                bonus1 = rewards.get("level1", 5)
                                if inviter.get('predictions_limit', 0) != -1:
                                    inviter['predictions_limit'] = inviter.get('predictions_limit', 0) + bonus1
                                inviter['invite_count'] = inviter.get('invite_count', 0) + 1
                                inviter['invite_rewards'] = inviter.get('invite_rewards', 0) + bonus1
                                if 'referred_users' not in inviter:
                                    inviter['referred_users'] = []
                                if new_user not in inviter['referred_users']:
                                    inviter['referred_users'].append(new_user)

                                # 新用戶自己都獲得獎勵
                                users[new_user]['predictions_limit'] += rewards.get("level1", 5)
                                users[new_user]['invite_rewards'] += rewards.get("level1", 5)

                                # Level 2：上線（邀請人嘅邀請人）
                                level2_user = inviter.get('invited_by')
                                if level2_user and level2_user in users:
                                    bonus2 = rewards.get("level2", 2)
                                    if users[level2_user].get('predictions_limit', 0) != -1:
                                        users[level2_user]['predictions_limit'] += bonus2
                                    users[level2_user]['invite_rewards'] = users[level2_user].get('invite_rewards', 0) + bonus2

                                    # Level 3：上上線
                                    level3_user = users[level2_user].get('invited_by')
                                    if level3_user and level3_user in users:
                                        bonus3 = rewards.get("level3", 1)
                                        if users[level3_user].get('predictions_limit', 0) != -1:
                                            users[level3_user]['predictions_limit'] += bonus3
                                        users[level3_user]['invite_rewards'] = users[level3_user].get('invite_rewards', 0) + bonus3

                        save_users(users)
                        log_user_activity(new_user, "註冊", f"邀請人：{invited_by or '無'}")
                        st.success(f"✅ 註冊成功！你獲得 {CONFIG.get('invite_rewards', {}).get('level1', 5)} 次額外預測獎勵！")
                        st.session_state.page_mode = "login"
                        st.rerun()
def show_chat_room():
    """聊天室內容（配合 popover 用）"""

    # 🛡️ 每 5 秒自動刷新
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=3000, key="chat_autorefresh")
    except Exception:
        pass

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    current_user = st.session_state.get('username', 'unknown')
    is_admin = st.session_state.get('role') == 'super_admin'
    ...

    # ===== 檢查封鎖 =====
    banned = False
    ban_reason = ""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_bans?username=eq.{current_user}",
            headers=headers, timeout=10
        )
        bans = r.json() if r.status_code == 200 else []
        if bans:
            ban = bans[0]
            until = ban.get('banned_until')
            if until:
                import pytz
                until_dt = pd.to_datetime(until)
                if until_dt.tzinfo is None:
                    until_dt = until_dt.tz_localize('UTC')
                now = pd.Timestamp.now(tz='UTC')
                if until_dt > now:
                    banned = True
                    ban_reason = ban.get('reason', '')
    except Exception:
        pass

    # ===== 讀取消息 =====
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_messages?deleted=eq.false&order=created_at.desc&limit=30",
            headers=headers, timeout=10
        )
        messages = res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        messages = []

    # ===== 顯示消息 =====
    if not messages:
        st.info("暫無消息，快啲嚟講第一句！")
    else:
        users_cache = load_users()
        for msg in reversed(messages):
            user = msg.get('username', '未知')
            text = msg.get('message', '')
            msg_id = msg.get('id')
            time_str = str(msg.get('created_at', ''))[11:16]

            is_admin_msg = users_cache.get(user, {}).get('group') == 'super_admin'
            crown = " 👑" if is_admin_msg else ""
            is_me = (user == current_user)

            bg = "#dcf8c6" if is_me else "#f1f1f1"
            align = "right" if is_me else "left"

            col1, col2 = st.columns([9, 1])
            with col1:
                st.markdown(
                    f"<div style='text-align:{align}; background:{bg}; "
                    f"padding:6px 10px; border-radius:8px; margin:3px 0; font-size:13px;'>"
                    f"<b>{user}{crown}</b> <small style='color:#888;'>{time_str}</small><br>{text}</div>",
                    unsafe_allow_html=True
                )
            with col2:
                if is_admin:
                    if st.button("🗑️", key=f"del_{msg_id}", help="刪除"):
                        try:
                            requests.patch(
                                f"{SUPABASE_URL}/rest/v1/chat_messages?id=eq.{msg_id}",
                                headers=headers,
                                json={"deleted": True},
                                timeout=10
                            )
                            st.rerun()
                        except Exception:
                            pass

            # 管理員封鎖
            if is_admin and not is_me:
                with st.expander(f"⚙️ 管理 {user}", expanded=False):
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        ban_min = st.number_input(
                            "禁言（分鐘）", min_value=1, max_value=10080,
                            value=60, key=f"bm_{msg_id}"
                        )
                    with bc2:
                        st.write("")
                        st.write("")
                        if st.button("🚫 封鎖", key=f"ban_{msg_id}_{user}"):
                            from datetime import datetime, timedelta
                            import pytz
                            hk_tz = pytz.timezone('Asia/Hong_Kong')
                            until = (datetime.now(hk_tz) + timedelta(minutes=ban_min)).isoformat()
                            try:
                                requests.delete(
                                    f"{SUPABASE_URL}/rest/v1/chat_bans?username=eq.{user}",
                                    headers=headers, timeout=10
                                )
                                requests.post(
                                    f"{SUPABASE_URL}/rest/v1/chat_bans",
                                    headers=headers,
                                    json={
                                        "username": user,
                                        "banned_until": until,
                                        "reason": "違規發言",
                                        "banned_by": current_user
                                    },
                                    timeout=10
                                )
                                st.success(f"✅ 已封鎖 {user}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"失敗：{e}")

                    if st.button("✅ 解封", key=f"unban_{msg_id}_{user}"):
                        try:
                            requests.delete(
                                f"{SUPABASE_URL}/rest/v1/chat_bans?username=eq.{user}",
                                headers=headers, timeout=10
                            )
                            st.success(f"✅ 已解封 {user}")
                            st.rerun()
                        except Exception:
                            pass

    st.divider()

    # ===== 發送消息 =====
    if banned:
        st.error(f"🚫 你已被禁言。原因：{ban_reason}")
    else:
        # 🛡️ 用 callback 發送，唔會影響輸入框
        def send_chat_message():
            msg = st.session_state.get('chat_input', '')
            if not msg or not msg.strip():
                return
            try:
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/chat_messages",
                    headers=headers,
                    json={"username": current_user, "message": msg.strip()[:200]},
                    timeout=10
                )
                st.session_state.chat_input = ''
            except Exception as e:
                st.session_state.chat_error = str(e)

        c1, c2 = st.columns([4, 1])
        with c1:
            st.text_input(
                "msg",
                key="chat_input",
                label_visibility="collapsed",
                placeholder="輸入消息..."
            )
        with c2:
            st.button(
                "📤",
                use_container_width=True,
                key="chat_send",
                on_click=send_chat_message
            )

        if st.session_state.get('chat_error'):
            st.error(f"失敗：{st.session_state.chat_error}")
            del st.session_state.chat_error

    if st.button("🔄 刷新", key="chat_refresh", use_container_width=True):
        st.rerun()

def main():    
    # 🛡️ 已登入用戶每 60 秒自動 rerun，檢查 session 超時
    if st.session_state.get('logged_in', False):
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=60000, key="timeout_check")

    check_session_timeout()

    defaults = {
        'logged_in': False, 'username': None, 'role': 'free',
        'show_admin': False, 'show_lottery': False, 'show_shop': False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if CONFIG["enable_registration"] and not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.show_admin and CONFIG["enable_admin"]:
        admin_page()
        return
    c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 1])
    with c1:
        st.title("🏇 賽馬預測系統")
        st.markdown("AI 驅動・即時預測・彩池推薦")
        st.caption(f"{datetime.now().strftime('%Y年%m月%d日')}")
    with c2:
        if CONFIG["enable_admin"] and st.session_state.get("role") == "super_admin":
            if st.button("🔐 後台", use_container_width=True, key="go_admin"):
                st.session_state.show_admin = True
                st.rerun()
    with c3:
        if st.button("❓ 常見問題", use_container_width=True, key="faq_btn"):
            st.switch_page("pages/FAQ.py")
    with c4:
        if st.session_state.get('logged_in', False):
            username = st.session_state.username
            users = load_users()
            user_data = users.get(username, {})
            virtual_balance = user_data.get('virtual_balance', 0)
            group = user_data.get('group', 'free')
            level = user_data.get('level', '🥉 銅牌會員')

            with st.popover("👤 個人中心", use_container_width=True):
                # ===== 推薦記錄 =====
                with st.expander("👥 我的推薦記錄", expanded=False):
                    users_all = load_users()
                    me = users_all.get(st.session_state.get('username', ''), {})
                    referred = me.get('referred_users', [])
                    invite_code = me.get('invite_code', '')
                    invite_count = me.get('invite_count', 0)
                    invite_rewards = me.get('invite_rewards', 0)

                    st.markdown(f"**你嘅邀請碼**：`{invite_code}`")
                    st.caption(f"已成功邀請 **{invite_count}** 位朋友，共獲得 **{invite_rewards}** 次額外預測")

                    if referred:
                        st.markdown("**直接下線列表：**")
                        df_ref = pd.DataFrame({
                            "用戶": referred,
                            "註冊時間": [users_all.get(u, {}).get('created_at', '') for u in referred]
                        })
                        st.dataframe(df_ref, use_container_width=True, hide_index=True)
                    else:
                        st.info("📭 暫時未邀請過朋友")
                st.markdown(f"### 👤 {username}")
                st.markdown(f"**級別**：{group.upper()}　|　**等級**：{level}")
                st.metric("💰 虛擬幣結餘", f"${virtual_balance:,.0f}")

                st.divider()

                # 更改密碼
                with st.expander("🔑 更改密碼", expanded=False):
                    old_pw = st.text_input("舊密碼", type="password", key="pc_old_pw")
                    new_pw = st.text_input("新密碼（最少 4 字）", type="password", key="pc_new_pw")
                    confirm_pw = st.text_input("確認新密碼", type="password", key="pc_confirm_pw")
                    if st.button("✅ 確認更改", key="pc_change_pw", use_container_width=True):
                        users2 = load_users()
                        if username not in users2:
                            st.error("❌ 用戶不存在")
                        elif users2[username].get('password') != old_pw:
                            st.error("❌ 舊密碼不正確")
                        elif len(new_pw) < 4:
                            st.error("❌ 新密碼最少 4 個字")
                        elif new_pw != confirm_pw:
                            st.error("❌ 兩次密碼不一致")
                        else:
                            users2[username]['password'] = new_pw
                            if save_users(users2):
                                st.success("✅ 密碼已更改！")
                            else:
                                st.error("❌ 儲存失敗")

                # 預測記錄
                with st.expander("📜 預測記錄", expanded=False):
                    history = user_data.get('history', [])
                    if not history:
                        st.info("📭 暫無預測記錄")
                    else:
                        total = len(history)
                        hits = sum(1 for h in history if h.get('is_hit') is True)
                        hit_rate = hits / total if total > 0 else 0
                        hc1, hc2, hc3 = st.columns(3)
                        hc1.metric("總預測", total)
                        hc2.metric("命中", hits)
                        hc3.metric("命中率", f"{hit_rate:.1%}")
                        st.divider()
                        df_hist = pd.DataFrame(history[-20:][::-1])
                        cols = [c for c in ['date', 'race', 'horse', 'is_hit'] if c in df_hist.columns]
                        if cols:
                            df_show = df_hist[cols].copy()
                            df_show.rename(columns={
                                'date': '日期', 'race': '場次',
                                'horse': '預測馬', 'is_hit': '結果'
                            }, inplace=True)
                            if '結果' in df_show.columns:
                                df_show['結果'] = df_show['結果'].apply(
                                    lambda x: '✅' if x is True else ('❌' if x is False else '⏳')
                                )
                            st.dataframe(df_show, use_container_width=True, hide_index=True)

    # 👇 c4 完結，縮進 4 格
    if st.session_state.get('logged_in', False):
        _checkin_user = st.session_state.get('username')
        if _checkin_user:
            st.divider()
            show_checkin_button(_checkin_user)    
    # 🛡️ 聊天室（Popover - 加大版）
    if st.session_state.get('logged_in', False):
        st.divider()

        # 🎨 CSS：加大 popover 寬度
        st.markdown("""
        <style>
        div[data-testid="stPopoverBody"] {
            min-width: 600px !important;
            max-width: 90vw !important;
            max-height: 80vh !important;
            overflow-y: auto !important;
        }
        </style>
        """, unsafe_allow_html=True)

        chat_col1, chat_col2 = st.columns([1, 4])
        with chat_col1:
            with st.popover("💬 聊天室", use_container_width=True):
                show_chat_room()

    with c5:
        if st.session_state.get('logged_in', False):
            if st.button("🚪 登出", use_container_width=True, key="logout_main"):
                for k in ['logged_in', 'username', 'role']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    st.markdown("---")
    
    # =========================================================================
    # 👇👇👇 重要：倒數卡片（⏰ 距離下場賽事）一定要放喺呢度！ 👇👇👇
    # 你必須將包含「⏰ 距離下場賽事」嘅代碼，原封不動咁貼喺呢度。
    # 記住：呢度嘅代碼前面「唔可以有 with c1: 或者 with c2: 嘅縮排」，佢一定要係最左邊（或者同上面 c1, c2... 對齊）。
    # 咁樣佢就會自動佔滿成行，變返做「成條橫額」！
    # =========================================================================
    
    # (貼上你原本倒數卡片嘅代碼，例如：)
    # st.markdown("⏰ 距離下場賽事：跑馬地夜馬")
    # st.markdown("## 2 00 11")
    # ...
    
    display_race_calendar()
    st.markdown("---")

    if st.session_state.logged_in:
        ca, cb = st.columns(2)
        with ca:
            if CONFIG.get("enable_lottery", True):
                if st.button("🎰 每日抽獎", use_container_width=True, key="go_lot"):
                    st.session_state.show_lottery = True
                    st.session_state.show_shop = False
        with cb:
            if CONFIG.get("enable_shop", True):
                if st.button("🛒 虛擬商城", use_container_width=True, key="go_shp"):
                    st.session_state.show_shop = True
                    st.session_state.show_lottery = False

        if st.session_state.get('show_lottery'):
            show_lottery_interface(st.session_state.username)
            if st.button("⬅️ 返回", key="bl"):
                st.session_state.show_lottery = False
                st.rerun()

        if st.session_state.get('show_shop'):
            show_shop_interface(st.session_state.username)
            if st.button("⬅️ 返回", key="bs"):
                st.session_state.show_shop = False
                st.rerun()

    st.divider()
    st.subheader("🎯 賽事預測")    
    # ============================================================
    # 🔧 管理員專用：一鍵預測所有場次
    # ============================================================
    if st.session_state.get('role') == 'super_admin':
        with st.expander("🛠️ 管理員工具：一鍵預測所有場次"):
            st.caption("⚠️ 只限管理員使用，會自動預測指定日期嘅所有場次。")

            col_date, col_btn, col_status = st.columns([2, 1, 2])

            with col_date:
                selected_date = st.date_input(
                    "📅 選擇日期",
                    value=pd.to_datetime("2026-09-06"),
                    key="batch_pred_date"
                )

            with col_btn:
                st.write("")
                run_batch = st.button(
                    "🔮 一鍵預測",
                    use_container_width=True,
                    key="batch_predict_btn_v3"
                )

            with col_status:
                st.write("")
                date_str = selected_date.strftime("%Y-%m-%d")
                try:
                    rc_df = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig')
                    rc_df = _repair_racecard(rc_df)
                    rc_df = rc_df.loc[:, ~rc_df.columns.duplicated()]
                    rename_map = {'馬名': 'horse_name', '檔位': 'draw', '場次': 'race_no',
                                  '比賽日期': 'race_date', '騎師': 'jockey', '練馬師': 'trainer',
                                  '負磅': 'weight', '馬號': 'horse_id', '賠率': 'win_odds'}
                    existing = [c for c in rename_map if c in rc_df.columns]
                    if existing:
                        rc_df.rename(columns={c: rename_map[c] for c in existing}, inplace=True)
                    rc_df = rc_df.loc[:, ~rc_df.columns.duplicated()]
                    if isinstance(rc_df['race_date'], pd.DataFrame):
                        rc_df['race_date'] = rc_df['race_date'].iloc[:, 0]
                    rc_df['race_date'] = pd.to_datetime(rc_df['race_date'], errors='coerce')
                    rc_df = rc_df.dropna(subset=['race_date'])
                    rc_df['race_date_str'] = rc_df['race_date'].dt.strftime('%Y-%m-%d')
                    rc_df['race_no'] = pd.to_numeric(rc_df['race_no'], errors='coerce').fillna(0).astype(int)
                    day_races = sorted(rc_df[rc_df['race_date_str'] == date_str]['race_no'].unique())
                    if not day_races:
                        st.warning(f"⚠️ {date_str} 冇數據")
                    else:
                        st.success(f"✅ 準備就緒（共 {len(day_races)} 場）")
                except Exception as e:
                    st.error(f"讀取失敗：{e}")

            # ===== 一鍵預測執行 =====
            if run_batch:
                date_str = selected_date.strftime("%Y-%m-%d")
                st.info(f"🚀 開始預測 {date_str} 所有場次...")

                try:
                    rc_df = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig')
                    rc_df = _repair_racecard(rc_df)
                    rc_df = rc_df.loc[:, ~rc_df.columns.duplicated()]
                    rename_map = {'馬名': 'horse_name', '檔位': 'draw', '場次': 'race_no',
                                  '比賽日期': 'race_date', '騎師': 'jockey', '練馬師': 'trainer',
                                  '負磅': 'weight', '馬號': 'horse_id', '賠率': 'win_odds'}
                    existing = [c for c in rename_map if c in rc_df.columns]
                    if existing:
                        rc_df.rename(columns={c: rename_map[c] for c in existing}, inplace=True)
                    rc_df = rc_df.loc[:, ~rc_df.columns.duplicated()]
                    if isinstance(rc_df['race_date'], pd.DataFrame):
                        rc_df['race_date'] = rc_df['race_date'].iloc[:, 0]
                    rc_df['race_date'] = pd.to_datetime(rc_df['race_date'], errors='coerce')
                    rc_df = rc_df.dropna(subset=['race_date'])
                    rc_df['race_date_str'] = rc_df['race_date'].dt.strftime('%Y-%m-%d')
                    rc_df['race_no'] = pd.to_numeric(rc_df['race_no'], errors='coerce').fillna(0).astype(int)
                    day_races = sorted(rc_df[rc_df['race_date_str'] == date_str]['race_no'].unique())

                    if not day_races:
                        st.warning(f"⚠️ {date_str} 冇任何場次數據")
                    else:
                        st.info(f"📋 準備預測 {len(day_races)} 場：{day_races}")
                        progress = st.progress(0)
                        status = st.empty()
                        success_count = 0
                        fail_count = 0
                        all_results = {}

                        for i, rn in enumerate(day_races):
                            status.text(f"⏳ 預測第 {rn} 場中...（{i+1}/{len(day_races)}）")
                            try:
                                result, pool = run_prediction(date_str, int(rn))
                                if result is not None and not result.empty:
                                    all_results[int(rn)] = result
                                    success_count += 1
                                else:
                                    fail_count += 1
                            except Exception as e:
                                fail_count += 1
                            progress.progress((i + 1) / len(day_races))

                        status.text("✅ 完成！")
                        st.success(f"✅ 成功 {success_count} 場，失敗 {fail_count} 場")

                        # 🔥 儲存到 session_state（防止 rerun 時消失）
                        st.session_state['batch_all_results'] = all_results
                        st.session_state['batch_date_str'] = date_str
                except Exception as e:
                    st.error(f"執行失敗：{e}")

            # ===== 讀取 session_state 嘅結果 =====
            all_results = st.session_state.get('batch_all_results', {})
            date_str_saved = st.session_state.get('batch_date_str', '')

            if all_results:
                st.divider()
                st.subheader(f"🎯 {date_str_saved} 跨場彩池推薦")

                race_list = sorted(all_results.keys())

                # ===== 1. 孖寶 =====
                st.markdown("#### 🎯 孖寶（連續 2 場）")
                if len(race_list) >= 2:
                    double_start = st.selectbox(
                        "孖寶起始場次",
                        race_list,
                        index=None,
                        placeholder="請選擇孖寶起始場次...",
                        key="double_start_selector"
                    )
                    if double_start is not None:
                        d_idx = race_list.index(double_start)
                        d_races = race_list[d_idx:d_idx + 2]
                        if len(d_races) >= 2:
                            d1 = all_results[d_races[0]].iloc[0]['horse_name']
                            d2 = all_results[d_races[1]].iloc[0]['horse_name']
                            st.success(f"**【孖寶】第 {d_races[0]}-{d_races[1]} 場**：{d1} + {d2}")
                        else:
                            st.warning(f"⚠️ 由第 {double_start} 場開始，唔夠 2 場數據")
                else:
                    st.warning("⚠️ 唔夠 2 場賽事，冇孖寶")

                st.divider()

                # ===== 2. 三寶 =====
                st.markdown("#### 🎯 三寶（連續 3 場）")
                if len(race_list) >= 3:
                    treble_start = st.selectbox(
                        "三寶起始場次",
                        race_list,
                        index=None,
                        placeholder="請選擇三寶起始場次...",
                        key="treble_start_selector"
                    )
                    if treble_start is not None:
                        t_idx = race_list.index(treble_start)
                        t_races = race_list[t_idx:t_idx + 3]
                        if len(t_races) >= 3:
                            t1 = all_results[t_races[0]].iloc[0]['horse_name']
                            t2 = all_results[t_races[1]].iloc[0]['horse_name']
                            t3 = all_results[t_races[2]].iloc[0]['horse_name']
                            st.success(f"**【三寶】第 {t_races[0]}-{t_races[2]} 場**：{t1} + {t2} + {t3}")
                        else:
                            st.warning(f"⚠️ 由第 {treble_start} 場開始，唔夠 3 場數據")
                else:
                    st.warning("⚠️ 唔夠 3 場賽事，冇三寶")

                st.divider()

                # ===== 3. 六環彩 =====
                st.markdown("#### 🎯 六環彩（連續 6 場）")
                if len(race_list) >= 6:
                    six_up_start = st.selectbox(
                        "六環彩起始場次",
                        race_list,
                        index=None,
                        placeholder="請選擇六環彩起始場次...",
                        key="six_up_start_selector"
                    )
                    if six_up_start is not None:
                        s_idx = race_list.index(six_up_start)
                        six_up_races = race_list[s_idx:s_idx + 6]
                        if len(six_up_races) >= 6:
                            horses = [all_results[rn].iloc[0]['horse_name'] for rn in six_up_races]
                            st.success(f"**【六環彩】第 {six_up_races[0]}-{six_up_races[-1]} 場**：{' + '.join(horses)}")
                        else:
                            st.warning(f"⚠️ 由第 {six_up_start} 場開始，唔夠 6 場數據（只有 {len(six_up_races)} 場）")
                else:
                    st.warning("⚠️ 唔夠 6 場賽事，冇六環彩")

                st.divider()

                # ===== 4. 各場預測結果 =====
                st.subheader("📊 各場預測結果")
                cols_per_row = 3
                for i in range(0, len(race_list), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx >= len(race_list):
                            break
                        rn = race_list[idx]
                        with col:
                            st.markdown(f"**🏇 第 {rn} 場**")
                            df = all_results[rn].copy()
                            cols_to_show = ['horse_name']
                            if 'draw' in df.columns:
                                cols_to_show.append('draw')
                            cols_to_show.append('預測勝率')
                            df_show = df[cols_to_show].head(3).copy()
                            df_show.columns = ['馬名', '檔位', '勝率'][:len(cols_to_show)]
                            df_show['勝率'] = df_show['勝率'].apply(lambda x: f"{x:.1%}")
                            st.dataframe(df_show, use_container_width=True, hide_index=True)
    cd, cbtn = st.columns([3, 1])
    with cd:
        date = st.date_input("📅 日期", value=pd.to_datetime("2026-09-06"), key="pd_date")
    with cbtn:
        st.write("")
        run_predict = st.button("🚀 執行預測", type="primary", use_container_width=True, key="pd_btn")

    st.markdown("**🏇 選擇場次：**")
    if 'selected_race' not in st.session_state:
        st.session_state.selected_race = 1

    race_cols = st.columns(11)
    for i in range(11):
        race_num = i + 1
        with race_cols[i]:
            if st.session_state.selected_race == race_num:
                if st.button(f"{race_num}", key=f"race_btn_{race_num}", use_container_width=True, type="primary"):
                    st.session_state.selected_race = race_num
            else:
                if st.button(f"{race_num}", key=f"race_btn_{race_num}", use_container_width=True):
                    st.session_state.selected_race = race_num

    race_no = st.session_state.selected_race
    st.caption(f"已選擇：第 {race_no} 場")

    if run_predict:
        with st.spinner("預測中..."):
            result, pool = run_prediction(date.strftime("%Y-%m-%d"), race_no)
            if result is not None and not result.empty:
                st.session_state['last_prediction'] = result
                st.session_state['last_pool'] = pool

    if 'last_prediction' in st.session_state and st.session_state['last_prediction'] is not None:
        st.success("✅ 預測完成！")
        if st.session_state.get('last_pool'):
            st.info(st.session_state['last_pool'])
        st.dataframe(st.session_state['last_prediction'], use_container_width=True)

    # ============================================================
    # 🤖 AI 預測表現 & 賽果對比（全寬，喺預測下面）
    # ============================================================
    st.divider()
    with st.expander("🤖 AI 預測表現 & 賽果對比（點擊展開）", expanded=False):
        # ===== 從 Supabase 讀取預測紀錄 =====
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        try:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/predictions?order=date.desc",
                headers=headers,
                timeout=10
            )
            records = res.json() if res.status_code == 200 else []
        except Exception as e:
            st.error(f"❌ 讀取預測紀錄失敗：{e}")
            records = []

        if not records:
            st.warning("⚠️ 尚未有任何預測紀錄，請先執行預測")
            st.stop()

        st.info(f"✅ 成功讀取 {len(records)} 個預測紀錄")

        # ===== 讀取賽果 =====
        result_file = "race_results_clean.csv"
        df_results = pd.DataFrame()
        if os.path.exists(result_file):
            try:
                df_results = pd.read_csv(result_file, encoding='utf-8-sig')
                required_cols = ['race_date', 'race_no', 'horse_name', 'finish_position']
                if not all(col in df_results.columns for col in required_cols):
                    st.error("❌ 賽果檔案缺少必要欄位")
                    df_results = pd.DataFrame()
                else:
                    df_results['horse_name'] = df_results['horse_name'].astype(str).str.strip()
                    # 🛡️ 清走馬名後面嘅 (H168) 呢類括號
                    df_results['horse_name'] = df_results['horse_name'].str.replace(
                        r'\s*\([A-Z]\d+\)\s*$', '', regex=True
                    ).str.strip()
                    df_results['finish_position'] = pd.to_numeric(df_results['finish_position'], errors='coerce')
                    df_results['race_no'] = pd.to_numeric(df_results['race_no'], errors='coerce')
                    df_results = df_results.dropna(subset=['race_no'])
                    df_results['race_no'] = df_results['race_no'].astype(int)
                    df_results['race_date'] = pd.to_datetime(df_results['race_date'], errors='coerce')
            except Exception as e:
                st.error(f"❌ 讀取賽果失敗：{e}")
                df_results = pd.DataFrame()
        else:
            st.warning("⚠️ 找不到賽果檔案 race_results_clean.csv")

        # ===== 將 Supabase 紀錄轉為 pred_list =====
        pred_list = []
        for rec in records:
            date_str = str(rec.get('date', '')).strip()
            race_no_c = rec.get('race')
            if not date_str or race_no_c is None:
                continue
            try:
                race_no_c = int(race_no_c)
            except Exception:
                continue

            horse_list = []
            raw_all = rec.get('all_horses')
            if raw_all:
                try:
                    parsed = json.loads(raw_all) if isinstance(raw_all, str) else raw_all
                    if isinstance(parsed, list):
                        horse_list = [str(h).strip() for h in parsed if str(h).strip()]
                except Exception:
                    pass

            if not horse_list:
                top = rec.get('top_horse')
                if top:
                    horse_list = [str(top).strip()]

            for idx, horse in enumerate(horse_list[:4], 1):
                pred_list.append({
                    '日期': date_str,
                    '場次': race_no_c,
                    '預測名次': idx,
                    '預測馬': horse
                })

        # ===== 比對 =====
        if pred_list and not df_results.empty:
            df_pred = pd.DataFrame(pred_list)
            df_pred['場次'] = df_pred['場次'].astype(int)
            df_pred['預測名次'] = df_pred['預測名次'].astype(int)

            pred_dates = sorted(df_pred['日期'].unique())
            result_dates = df_results['race_date'].dt.strftime('%Y-%m-%d').unique()
            available_dates = [d for d in pred_dates if d in result_dates]

            if available_dates:
                selected_date = st.selectbox("📅 選擇日期", available_dates,
                    format_func=lambda x: x, key="ai_cmp_date")

                df_pred_date = df_pred[df_pred['日期'] == selected_date].copy()
                df_result_date = df_results[
                    df_results['race_date'].dt.strftime('%Y-%m-%d') == selected_date
                ].copy()

                pred_races = sorted(df_pred_date['場次'].unique())
                result_races = sorted(df_result_date['race_no'].unique())
                available_races = [r for r in pred_races if r in result_races]

                if available_races:
                    selected_race = st.selectbox("🏇 選擇場次", available_races,
                        format_func=lambda x: f"第 {x} 場", key="ai_cmp_race")

                    df_pred_race = df_pred_date[df_pred_date['場次'] == selected_race].copy()

                    # 🛡️ 攞全場真實名次（唔再限頭 3 名）
                    df_result_race = df_result_date[
                        df_result_date['race_no'] == selected_race
                    ].copy()
                    df_result_race = df_result_race.sort_values('finish_position')

                    # 判斷命中：頭 3 名
                    top3_names = df_result_race.head(3)['horse_name'].tolist()

                    # 真實名次 map（全場）
                    all_real_map = dict(zip(
                        df_result_race['horse_name'],
                        df_result_race['finish_position']
                    ))

                    # 🛡️ 比對
                    df_compare = df_pred_race.copy()
                    df_compare['真實名次'] = df_compare['預測馬'].map(all_real_map)
                    df_compare['真實馬'] = df_compare['預測馬']
                    df_compare['結果'] = df_compare['預測馬'].apply(
                        lambda h: '命中' if h in top3_names else '失準'
                    )

                    # 🛡️ 清理顯示格式
                    df_compare['真實名次'] = df_compare['真實名次'].apply(
                        lambda x: int(x) if pd.notna(x) else ''
                    )
                    df_compare['真實馬'] = df_compare['真實馬'].fillna('')

                    display_df = df_compare[['預測名次', '預測馬', '真實名次', '真實馬', '結果']].copy()
                    display_df.columns = ['名次', '預測馬', '真實名次', '真實馬', '結果']

                    st.write(f"📊 {selected_date} 第 {selected_race} 場 預測 vs 賽果")

                    def highlight_row(row):
                        if row['結果'] == '命中':
                            return ['background-color: #d4edda; color: black'] * len(row)
                        elif row['結果'] == '失準':
                            return ['background-color: #f8d7da; color: black'] * len(row)
                        return ['background-color: white; color: black'] * len(row)

                    styled_df = display_df.style.apply(highlight_row, axis=1)
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"ℹ️ {selected_date} 沒有可比對嘅場次")
            else:
                st.info("ℹ️ 沒有日期同時有預測同賽果數據")
        else:
            st.info("ℹ️ 請確保已有預測紀錄及賽果數據")
# ===== 打賞支持 =====
    st.divider()
    st.subheader("❤️ 打賞支持")
    if st.session_state.get('logged_in', False):
        st.caption("你嘅支持係我哋繼續開發嘅動力！")

        amount = st.number_input(
            "請輸入打賞金額（HKD）",
            min_value=0.0,
            step=1.0,
            value=None,
            placeholder="請輸入金額",
            key="reward_amount_input"
        )

        st.markdown("**付款方式：FPS 轉數快**")
        st.code("FPS ID: 你的電話號碼或 FPS ID", language=None)  # ⚠️ 待你提供真實值
        st.markdown("付款後，請撳下面個掣，管理員會盡快審核。")

        if st.button("✅ 我已經付款", type="primary"):
            if amount is None or amount <= 0:
                st.warning("⚠️ 請先輸入打賞金額")
            else:
                headers_post = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                }
                hk_now = datetime.now(pytz.timezone('Asia/Hong_Kong'))
                payload = {
                    "username": st.session_state.get('username', 'unknown'),
                    "amount": float(amount),
                    "vip_days": 0,
                    "rewarded_at": hk_now.isoformat(),
                    "status": "pending"
                }
                try:
                    post_res = requests.post(
                        f"{SUPABASE_URL}/rest/v1/reward_history",
                        headers=headers_post,
                        json=payload,
                        timeout=10
                    )
                    if post_res.status_code in (200, 201, 204):
                        st.success("✅ 已提交！管理員審核後會盡快處理。")
                    else:
                        st.error(f"❌ 提交失敗 (HTTP {post_res.status_code})：{post_res.text}")
                except Exception as e:
                    st.error(f"❌ 連線錯誤：{e}")
    else:
        st.info("請先登入以使用打賞功能")

    st.divider()
    st.warning("⚠️ 免責聲明：本系統預測僅供參考，不構成投注建議。賽馬活動涉及風險，用戶應量力而為。用戶必須年滿18歲。")
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · v16.1")
    st.caption("💬 Telegram：@bryhjdjbrbxibvrjskofndhiebdpaq")


if __name__ == '__main__':
    main()
