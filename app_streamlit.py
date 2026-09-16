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
warnings.filterwarnings('ignore')

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# 第 24-29 行：你原本嘅設定(保留)
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 👇 第 30 行開始，喺呢度加我嗰段 CSS
st.markdown("""
<style>
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
        padding-top: 1rem !important;
    }
    h1 { font-size: 1.3rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 1rem !important; }
    p, div, span, label { font-size: 0.9rem !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* 👇 場次按鈕：一行過，平均分配，唔滑動 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
        overflow: visible !important;
    }
    div[data-testid="column"] {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        max-width: none !important;
        padding: 0 !important;
    }

    /* 將按鈕縮到最細，變成圓形 */
    .stButton button {
        width: 100% !important;
        height: 36px !important;
        min-width: 0 !important;
        padding: 0 !important;
        font-size: 0.75rem !important;
        font-weight: bold !important;
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
}
</style>
""", unsafe_allow_html=True)
<style>
    div[data-testid="stToolbar"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
</style>
""", unsafe_allow_html=True)
CONFIG_FILE = 'system_config.json'
DEFAULT_CONFIG = {
    "enable_registration": True, "enable_payment": True, "enable_admin": True,
    "enable_lottery": True, "enable_shop": True,
    "currency": "HKD", "free_limit": 2, "admin_password": "z54060437K",
    "price_day": 18, "price_month": 128, "price_quarter": 328,
    "daily_virtual_coin": 1000, "virtual_coin_enabled": True,
    "enable_invite_reward": True,    
    "invite_rewards": {
        "level1": 5,   # 直接邀請人：+5 次預測
        "level2": 2,   # 上線(A 邀請 B，B 邀請 C → A 得 2 次)
        "level3": 1,   # 上上線：+1 次
    },
    # ===== 🎯 彩池設定 =====
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
        "six_up": {"enabled": True, "required_group": "VIP", "label": "六環彩"},
    },
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

import requests
import json
import random
from datetime import datetime

SUPABASE_URL = "https://fewanagxvezelufmuggq.supabase.co"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"

@st.cache_data(ttl=60)  # 👈 加呢行！快取 60 秒
def load_users():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/users?select=*", headers=headers)
        if res.status_code == 200:
            raw_users = res.json()
            result = {}
            for row in raw_users:
                result[row["username"]] = {
                    "password": row.get("password", ""),
                    "phone": row.get("phone", ""),
                    "invite_code": row.get("invite_code", ""),
                    "invited_by": row.get("invited_by", ""),
                    "referred_users": json.loads(row["referred_users"]) if row.get("referred_users") else [],
                    "invite_count": row.get("invite_count", 0),
                    "invite_rewards": row.get("invite_rewards", 0),
                    "group": row.get("user_group", "free"),
                    "level": row.get("level", "🥉 銅牌會員"),
                    "virtual_balance": row.get("virtual_balance", 1000),
                    "lottery_chances": row.get("lottery_chances", 0),
                    "last_lottery_reset": row.get("last_lottery_reset", ""),
                    "created_at": row.get("created_at", ""),
                    "history": json.loads(row["history"]) if row.get("history") else [],
                    "is_paid": row.get("is_paid", False),
                    "predictions_limit": row.get("predictions_limit", -1),
                    "total_usage": row.get("total_usage", 0),
                    "badges": json.loads(row["badges"]) if row.get("badges") else [],
                    "exp": row.get("exp", 0),
                    "plan": row.get("plan"),
                    "paid_date": row.get("paid_date"),
                    "expiry_date": row.get("expiry_date"),
                    "terms_agreed": row.get("terms_agreed"),
                    "bets": json.loads(row["bets"]) if row.get("bets") else []
                }
            
            # 如果 Supabase 冇 admin，就建立一個
            if "admin" not in result:
                result["admin"] = {
                    "username": "admin",
                    "password": "z54060437K",
                    "group": "super_admin",
                    "is_paid": True,
                    "predictions_limit": -1,
                    "free_usage": 0,
                    "total_usage": 0,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "history": [], "badges": [], "level": "👑 超級管理員", "exp": 0,
                    "virtual_balance": 10000, "last_claim_date": "", "last_lottery_date": "",
                    "invite_code": "ADMIN001", "invite_count": 0, "invite_rewards": 0,
                    "phone": "", "note": "系統超級管理員", "plan": None, "paid_date": None,
                    "expiry_date": None, "terms_agreed": datetime.now().isoformat(), "bets": []
                }
                save_users(result)
            else:
                # 補齊缺失欄位(保留原本邏輯)
                for uid, u in result.items():
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
                    if 'invite_code' not in u or not u['invite_code']:
                        u['invite_code'] = uid.upper() + str(random.randint(100, 999))
                    if 'predictions_limit' not in u:
                        if u.get('group') in ['super_admin', 'VIP', 'paid']:
                            u['predictions_limit'] = -1
                        else:
                            u['predictions_limit'] = 2
                save_users(result)
            return result
        else:
            return {}
    except Exception as e:
        return {}

def save_users(users):
    """將所有用戶儲存到 Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    for username, data in users.items():
        payload = {
            "username": username,
            "password": data.get("password", ""),
            "phone": data.get("phone", ""),
            "invite_code": data.get("invite_code", ""),
            "invited_by": data.get("invited_by", ""),
            "referred_users": json.dumps(data.get("referred_users", []), ensure_ascii=False),
            "invite_count": data.get("invite_count", 0),
            "invite_rewards": data.get("invite_rewards", 0),
            "user_group": data.get("group", "free"),
            "level": data.get("level", "🥉 銅牌會員"),
            "virtual_balance": data.get("virtual_balance", 0),
            "lottery_chances": data.get("lottery_chances", 0),
            "last_lottery_reset": data.get("last_lottery_reset", ""),
            "created_at": data.get("created_at", ""),
            "history": json.dumps(data.get("history", []), ensure_ascii=False),
            "is_paid": data.get("is_paid", False),
            "predictions_limit": data.get("predictions_limit", -1),
            "total_usage": data.get("total_usage", 0),
            "badges": json.dumps(data.get("badges", []), ensure_ascii=False),
            "exp": data.get("exp", 0),
            "plan": data.get("plan"),
            "paid_date": data.get("paid_date"),
            "expiry_date": data.get("expiry_date"),
            "terms_agreed": data.get("terms_agreed"),
            "bets": json.dumps(data.get("bets", []), ensure_ascii=False)
        }
        try:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=headers, json=payload)
            if res.status_code not in [200, 201, 204]:
                st.error(f"❌ 寫入失敗：{res.text}")
        except Exception as e:
            st.error(f"❌ 寫入錯誤：{e}")
    return users

def save_users(users):
    """將所有用戶儲存到 Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    for username, data in users.items():
        payload = {
            "username": username,
            "password": data.get("password", ""),
            "phone": data.get("phone", ""),
            "invite_code": data.get("invite_code", ""),
            "invited_by": data.get("invited_by", ""),
            "referred_users": json.dumps(data.get("referred_users", []), ensure_ascii=False),
            "invite_count": data.get("invite_count", 0),
            "invite_rewards": data.get("invite_rewards", 0),
            "user_group": data.get("group", "free"),
            "level": data.get("level", "🥉 銅牌會員"),
            "virtual_balance": data.get("virtual_balance", 0),
            "lottery_chances": data.get("lottery_chances", 0),
            "last_lottery_reset": data.get("last_lottery_reset", ""),
            "created_at": data.get("created_at", ""),
            "history": json.dumps(data.get("history", []), ensure_ascii=False)
        }
        try:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=headers, json=payload)
            if res.status_code not in [200, 201, 204]:
                st.error(f"❌ 寫入失敗：{res.text}")
        except Exception as e:
            st.error(f"❌ 寫入錯誤：{e}")
    
    return True

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
    default_config = {
        "items": [
            {"name": "額外 5 次預測", "type": "predictions", "price": 500, "stock": 100, "description": "增加 5 次預測機會"},
            {"name": "VIP 7 天體驗", "type": "vip_days", "price": 3000, "stock": 50, "description": "7 天 VIP 權限"},
            {"name": "神秘盲盒", "type": "mystery_box", "price": 1000, "stock": 20, "description": "隨機獲得獎品"}
        ]
    }
    
    if os.path.exists("shop_config.json"):
        try:
            with open("shop_config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            if config.get("items"):
                return config
        except Exception:
            pass
            
    # 如果檔案唔存在、讀取失敗或者係空嘅，就寫入預設值
    with open("shop_config.json", "w", encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    return default_config

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
    """生成彩池推薦 (按會員級別 + 每個彩池只出一個組合)"""
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
            return f"  {names[0]}({probs[0]:.1%})"
        return ""

    def get_place():
        if len(names) >= 2:
            return f"  {names[0]}({probs[0]:.1%})+ {names[1]}({probs[1]:.1%})"
        elif len(names) >= 1:
            return f"  {names[0]}({probs[0]:.1%})"
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
        return "  ⚠️ 需要 2 場賽事數據(孖寶)"

    def get_treble():
        return "  ⚠️ 需要 3 場賽事數據(三寶)"

    def get_six_up():
        return "  ⚠️ 需要 6 場賽事數據(六環彩)"

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


def _repair_racecard(df):
    """自動修復混合格式嘅 racecard CSV"""
    # 讀取原始檔案(唔用 header)
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

        # 中文格式：第一列係純數字(馬號)
        if first_val.isdigit():
            row_df = pd.DataFrame([row.values], columns=cn_cols)
            parts.append(row_df)

        # 英文格式：第一列係日期(YYYY-MM-DD)
        elif len(first_val) == 10 and first_val[4] == '-' and first_val[7] == '-':
            row_df = pd.DataFrame([row.values], columns=en_cols)
            parts.append(row_df)

    if not parts:
        return pd.DataFrame(columns=std_cols)

    result = pd.concat(parts, ignore_index=True)
    result = result[std_cols]
    return result


def _build_features(race_df, history_df):
    """為排位表每匹馬計算特徵(加入馬名對照，修復歷史數據對唔上嘅問題)"""
    import numpy as np
    import os

    history_df = history_df.copy()
    history_df['race_date'] = pd.to_datetime(history_df['race_date'], errors='coerce')
    history_df = history_df.dropna(subset=['race_date'])
    history_df['finish_position'] = pd.to_numeric(history_df['finish_position'], errors='coerce')
    history_df = history_df.dropna(subset=['finish_position'])

    result = race_df.copy()

    # ========================================================
    # 🛡️ 終極修復：用「馬名」將排位表嘅馬號，對照成真實馬匹編號
    # ========================================================
    if 'horse_name' in result.columns and 'horse_name' in history_df.columns and 'horse_id' in history_df.columns:
        # 清理空格
        history_df['horse_name'] = history_df['horse_name'].astype(str).str.strip()
        history_df['horse_id'] = history_df['horse_id'].astype(str).str.strip()
        result['horse_name'] = result['horse_name'].astype(str).str.strip()
        
        # 建立「馬名 -> 真實馬匹編號」對照表
        name_to_id_map = history_df.drop_duplicates('horse_name').set_index('horse_name')['horse_id'].to_dict()
        
        # 將 result 入面嘅 horse_id(1-14號)替換成真實編號(例如 H196)
        result['horse_id'] = result['horse_name'].map(name_to_id_map).fillna(result['horse_id']).astype(str).str.strip()
    # ========================================================

    # 初始化所有特徵
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

def run_prediction(date_str, race_no):
    """用真正 ML 模型預測(統一 36 特徵版)"""
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

    history_df = pd.DataFrame()
    if os.path.exists("ALL_DATA_MERGED.csv"):
        try:
            history_df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
            history_df.columns = [str(c).replace('\ufeff', '').strip() for c in history_df.columns]
            if 'finish_position' not in history_df.columns and 'Pla' in history_df.columns:
                history_df['finish_position'] = history_df['Pla']
        except Exception as e:
            st.warning(f"⚠️ 讀取歷史數據失敗：{e}")

    with st.spinner("🔧 計算特徵中..."):
        features_df = _build_features(filtered, history_df)

    xgb_model, cat_model, rank_model = load_ml_models()

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

    # ===== XGBoost(強制用 36 特徵)=====
    if xgb_model is not None:
        try:
            X_xgb = features_df[features_36].fillna(0).values
            pred_xgb = xgb_model.predict_proba(X_xgb)[:, 1]
            models_used.append("XGBoost(36特徵)")
        except Exception as e:
            st.warning(f"⚠️ XGBoost 失敗：{e}")

    # ===== CatBoost(強制用 36 特徵)=====
    if cat_model is not None:
        try:
            X_cat = features_df[features_36].fillna(0).values
            pred_cat = cat_model.predict_proba(X_cat)[:, 1]
            models_used.append("CatBoost(36特徵)")
        except Exception as e:
            st.warning(f"⚠️ CatBoost 失敗：{e}")

    # ===== Ranking(強制用 36 特徵)=====
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

    # ===== 融合(優先從 system_config 讀取權重)=====
    all_preds = [p for p in [pred_xgb, pred_cat, pred_rank] if p is not None]
    if all_preds:
        import json
        try:
            with open("system_config.json", "r", encoding="utf-8") as f:
                sys_config = json.load(f)
            w_xgb = sys_config.get("xgb_weight", 0.3)
            w_cat = sys_config.get("cat_weight", 0.5)
            w_rank = 0.2 # 默認 Rank 權重
            # 如果 system_config 寫 25/1，就自動轉換為比例
            if w_xgb > 1 or w_cat > 1:
                total = w_xgb + w_cat + w_rank
                w_xgb = w_xgb / total
                w_cat = w_cat / total
                w_rank = w_rank / total
        except Exception:
            w_xgb, w_cat, w_rank = 0.3, 0.5, 0.2

        weights = []
        if pred_xgb is not None: weights.append(w_xgb)
        if pred_cat is not None: weights.append(w_cat)
        if pred_rank is not None: weights.append(w_rank)

        weights = np.array(weights) / sum(weights)

        pred_proba = np.zeros(len(filtered))
        for i, p in enumerate(all_preds):
            pred_proba += weights[i] * p

        st.success(f"✅ 使用模型：{', '.join(models_used)}(權重：XGB {weights[0]:.2f} / Cat {weights[1]:.2f})")
    else:
        st.warning("⚠️ 冇可用模型，改用賠率估算")
        win_odds = pd.to_numeric(filtered.get('win_odds', 4.0), errors='coerce').fillna(4.0).replace(0, 4.0)
        inv = 1 / win_odds
        pred_proba = (inv / inv.sum()).values

    pred_proba = pred_proba / pred_proba.sum()

    # 提取馬號
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
        'horse_name': '馬名', 'draw': '檔位', 'weight': '負磅',
        'jockey': '騎師', 'trainer': '練馬師'
    })
    result_df['預測勝率'] = pred_proba
    result_df['值博指數'] = result_df['預測勝率'] * 10
    result_df['信心指數'] = result_df['預測勝率'].apply(
        lambda x: '⭐⭐⭐ 高' if x > 0.2 else '⭐⭐ 中' if x > 0.1 else '⭐ 低'
    )
    result_df = result_df.sort_values('預測勝率', ascending=False).reset_index(drop=True)

    # 儲存
    # 儲存到 SQLite
    # 儲存到 Supabase
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
    """搵一個有數據嘅欄位(唔止名要對，仲要有實際值)"""
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
                st.caption(f"📁 讀取：{fp}({len(df)} 行)")
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
        with st.expander("🔍 診斷(點擊展開)", expanded=True):
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
    # 試 Pla(用位置索引，避免隱藏字元)
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

    # 🛡️ 智能偵測欄位名(支援中英文)
    name_col = None
    for c in ['horse_name', '馬名', '馬匹名稱', 'Name']:
        if c in df.columns:
            name_col = c
            break

    pos_col = None
    for c in ['finish_position', 'Pla.', '名次', '最終名次']:
        if c in df.columns:
            pos_col = c
            break

    if name_col is None or pos_col is None:
        st.write(f"可用欄位：{df.columns.tolist()}")
        st.warning("⚠️ 賽果檔案缺少「馬名」或「名次」欄位，請檢查 CSV 格式。")
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

    st.success(f"✅ 共 {len(stats)} 匹馬(有效數據：{len(df)} 條)")

    # 格式化顯示
    stats_display = stats.copy()
    stats_display['勝率'] = stats_display['勝率'].apply(lambda x: f"{x:.1%}")
    stats_display.columns = ['馬名', '總出賽', '勝出', '勝率']

    st.dataframe(stats_display, use_container_width=True, hide_index=True, height=600)
def admin_jockey_ranking():
    st.subheader("🏇 騎師勝率排行榜")

    # 🛡️ 騎師中英文對照表
    JOCKEY_MAP = {
        "Z Purton": "潘頓",
        "H Bowman": "布文",
        "A Atzeni": "艾兆禮",
        "L Ferraris": "霍宏聲",
        "B Avdulla": "艾道拿",
        "K Teetan": "田泰安",
        "K C Leung": "梁家俊",
        "M F Poon": "潘明輝",
        "M Chadwick": "蔡明紹",
        "H Bentley": "班德禮",
        "J Moreira": "莫雷拉",
        "C Y Ho": "何澤堯",
        "A Badel": "巴度",
        "B Shinn": "寶遜",
        "L Hewitson": "希威森",
        "Y L Chung": "鍾易禮",
        "A Hamelin": "賀銘年",
        "E C W Wong": "黃智弘",
        "H T Mo": "巫顯東",
        "M L Yeung": "楊明綸",
        "C L Chau": "周俊樂",
        "M Barzalona": "巴米高",
        "K De Melo": "簡能",
        "J Orman": "奧爾民",
        "R Kingscote": "金誠剛",
        "H Y Yuen": "袁幸堯",
        "P N Wong": "黃寶妮",
        "M Newnham": "廖康銘",
        "D Eustace": "游達榮",
        "B Crawford": "桂福特",
        "D J Whyte": "韋達",
        "D J Hall": "賀賢",
        "A S Cruz": "告東尼",
        "C S Shum": "沈集成",
        "C Fownes": "方嘉柏",
        "J Size": "蔡約翰",
        "F C Lor": "羅富全",
        "K W Lui": "呂健威",
        "P F Yiu": "姚本輝",
        "W Y So": "蘇偉賢",
        "K L Man": "文家良",
        "T P Yung": "容天鵬",
        "Y S Tsui": "徐雨石",
        "C W Chang": "鄭俊偉",
        "C H Yip": "葉楚航",
        "M Newnham": "廖康銘",
        "J Richards": "黎昭昇",
        "D A Hayes": "大衛希斯",
        "P C Ng": "伍鵬志",
        "K H Ting": "丁冠豪",
        "D Whyte": "韋達",
        "G Mosse": "巫斯義",
        "T Marquand": "馬昆",
        "A K Chan": "陳嘉熙",
        "S De Sousa": "蘇兆輝",
        "N Callan": "高力",
        "R Moore": "莫雅",
        "P Beggy": "貝治",
        "A Kirby": "柯比",
        "J McDonald": "麥道朗",
        "H Doyle": "杜苑欣",
        "R Ryan": "羅理雅",
        "W Buick": "布宜學",
        "O Murphy": "莫菲",
        "T Berry": "貝利",
        "C Soumillon": "蘇銘倫",
        "J Doyle": "杜滿樂",
        "F Minarik": "米奈克",
        "T Marquand": "馬昆",
    }

    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]

        # 🛡️ 智能偵測名次欄位
        pos_candidates = ['finish_position', 'Pla.', '名次', '最終名次']
        pos_col = None
        max_valid = 0
        for c in pos_candidates:
            if c in df.columns:
                valid = pd.to_numeric(df[c], errors='coerce').notna().sum()
                if valid > max_valid:
                    max_valid = valid
                    pos_col = c

        # 🛡️ 智能偵測騎師欄位(優先中文，如果冇就用英文)
        jockey_candidates = ['jockey_cn', '騎師', 'jockey', '騎師名']
        jockey_col = None
        max_valid = 0
        for c in jockey_candidates:
            if c in df.columns:
                valid = df[c].astype(str).str.strip().replace(['nan', 'none', ''], pd.NA).notna().sum()
                if valid > max_valid:
                    max_valid = valid
                    jockey_col = c

        if pos_col is None or jockey_col is None:
            st.warning("⚠️ 賽果檔案缺少「騎師」或「名次」欄位")
            st.write(f"可用欄位：{df.columns.tolist()}")
            return

        temp = pd.DataFrame()
        temp['騎師'] = df[jockey_col].astype(str).str.strip()
        temp['名次'] = pd.to_numeric(df[pos_col], errors='coerce')
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

        # 🛡️ 將英文名轉做中文名
        stats['騎師'] = stats['騎師'].apply(lambda x: JOCKEY_MAP.get(x, x))

        stats = stats.sort_values('勝出', ascending=False).reset_index(drop=True)

        st.success(f"✅ 共 {len(stats)} 位騎師")
        st.dataframe(stats.head(30), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        import traceback
        st.code(traceback.format_exc())
def admin_trainer_ranking():
    st.subheader("🏇 練馬師勝率排行榜")
    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]

        pos_series, pos_name = _get_pos_series(df)
        st.caption(f"📊 使用名次欄位：**{pos_name}**(有效數據：{pos_series.notna().sum()})")

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
            with st.expander(f"{p.get('name', '獎品')}(權重 {p.get('weight', 0)})"):
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
def show_lottery_interface(username):
    st.subheader("🎰 每日抽獎")
    if not username:
        st.info("請先登入")
        return

    # 倒數計時
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
    if user.get('last_lottery_reset', '') != today:
        # 每日免費派發 1 次抽獎機會(可自行調整)
        daily_chances = 1
        user['lottery_chances'] = user.get('lottery_chances', 0) + daily_chances
        user['last_lottery_reset'] = today
        users[username] = user
        save_users(users)
        st.success(f"🎁 每日重置！你獲得 {daily_chances} 次抽獎機會！")
        st.rerun()

    lottery_chances = user.get('lottery_chances', 0)

    # 顯示抽獎次數
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

    # 初始化 session state
    if 'lottery_rolling' not in st.session_state:
        st.session_state.lottery_rolling = False
    if 'lottery_result' not in st.session_state:
        st.session_state.lottery_result = None

    # ===== 抽獎動畫區域 =====
    animation_placeholder = st.empty()

    if st.session_state.lottery_rolling:
        icons = ["🎁", "🎰", "💎", "🏆", "🎊", "⭐", "🍀", "🎯"]
        for i in range(12):
            icon = icons[i % len(icons)]
            animation_placeholder.markdown(f"""
            <div style="background: linear-gradient(135deg, #ffecd2, #fcb69f);
                        padding: 40px; border-radius: 16px; text-align: center;
                        border: 3px dashed #ff6b6b;">
                <div style="font-size: 80px; animation: spin 0.3s linear infinite;">{icon}</div>
                <div style="font-size: 20px; font-weight: bold; color: #d63447; margin-top: 10px;">
                    抽獎中...
                </div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(0.15)

    # 顯示中獎結果
    if st.session_state.lottery_result is not None:
        result = st.session_state.lottery_result
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f9d423, #ff4e50);
                    padding: 30px; border-radius: 16px; text-align: center;
                    color: white; box-shadow: 0 8px 25px rgba(255,78,80,0.4);
                    animation: pop 0.5s ease-out;">
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
        <style>
            @keyframes pop {{
                0% {{ transform: scale(0.5); opacity: 0; }}
                70% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); opacity: 1; }}
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
        """, unsafe_allow_html=True)

        st.balloons()
        st.snow()

        if st.button("🔄 再抽一次", use_container_width=True, key="roll_again"):
            st.session_state.lottery_result = None
            st.rerun()

    # ===== 抽獎按鈕 =====
    elif not st.session_state.lottery_rolling:
        if st.button("🎲 開始抽獎！", type="primary", use_container_width=True, key="start_lottery"):
            st.session_state.lottery_rolling = True
            st.rerun()

    # ===== 執行抽獎邏輯 =====
    if st.session_state.lottery_rolling:
        # 扣一次抽獎次數
        users[username]['lottery_chances'] = lottery_chances - 1

        # 抽獎
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

    users = load_users()

    if not users:
        st.error("❌ 讀取用戶失敗，請檢查 Supabase 連線")
        return

    st.info(f"✅ 成功載入 {len(users)} 個用戶")

    # ===== 顯示用戶列表 =====
    df_users = pd.DataFrame([
        {
            "用戶名": u,
            "群組": d.get("group", "free"),
            "等級": d.get("level", "🥉 銅牌會員"),
            "虛擬幣": d.get("virtual_balance", 0),
            "付費": "✅" if d.get("is_paid") else "❌"
        }
        for u, d in users.items()
    ])
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.divider()

    # ===== 編輯用戶 =====
    st.subheader("✏️ 編輯用戶")
    selected_user = st.selectbox("選擇要編輯嘅用戶", list(users.keys()), key="edit_user_select")

    if selected_user:
        u = users[selected_user]

        c1, c2 = st.columns(2)
        with c1:
            group_options = ["free", "paid", "VIP", "super_admin"]
            current_group = u.get("group", "free")
            if current_group not in group_options:
                current_group = "free"
            new_group = st.selectbox("群組", group_options, index=group_options.index(current_group), key="edit_user_group")

            level_options = ["🥉 銅牌會員", "🥈 銀牌會員", "🥇 金牌會員", "💎 鑽石會員", "👑 傳說會員", "👑 超級管理員"]
            current_level = u.get("level", "🥉 銅牌會員")
            if current_level not in level_options:
                current_level = "🥉 銅牌會員"
            new_level = st.selectbox("等級", level_options, index=level_options.index(current_level), key="edit_user_level")

            new_is_paid = st.checkbox("付費狀態", value=bool(u.get("is_paid", False)), key="edit_user_paid")

        with c2:
            new_password = st.text_input("新密碼(留空 = 不改)", type="password", key="edit_user_pw")
            new_phone = st.text_input("手機號碼", value=u.get("phone", ""), key="edit_user_phone")
            new_exp = st.number_input("經驗值", min_value=0, value=int(u.get("exp", 0)), step=1, key="edit_user_exp")

        new_note = st.text_area("備註", value=u.get("note", ""), key="edit_user_note")

        if st.button("💾 儲存變更", type="primary", key="save_user_btn"):
            users[selected_user]["group"] = new_group
            users[selected_user]["level"] = new_level
            users[selected_user]["is_paid"] = new_is_paid
            users[selected_user]["phone"] = new_phone
            users[selected_user]["note"] = new_note
            users[selected_user]["exp"] = int(new_exp)

            if new_password:
                users[selected_user]["password"] = new_password

            # 根據群組自動調整預測次數限制
            if new_group in ["super_admin", "VIP", "paid"]:
                users[selected_user]["predictions_limit"] = -1
            else:
                users[selected_user]["predictions_limit"] = 2

            success = save_users(users)
            if success:
                st.success(f"✅ 已儲存 {selected_user} 嘅變更")
                st.rerun()
            else:
                st.error("❌ 儲存失敗，請檢查 Supabase 權限")
def admin_downloads():
    st.subheader("📥 下載中心")
    st.caption("喺呢度下載系統嘅重要檔案備份。")

    import os
    from datetime import datetime

    download_files = [
        ("users.json", "用戶資料"),
        ("ai_predictions.json", "AI 預測記錄"),
        ("race_results_clean.csv", "賽果數據"),
        ("racecard_uploaded.csv", "排位表"),
        ("odds_history.csv", "賠率歷史"),
        ("finance.json", "財務記錄"),
        ("promo_codes.json", "優惠碼"),
        ("payment_proofs.json", "付款記錄"),
        ("admin_log.json", "管理員日誌"),
        ("user_activity_log.json", "用戶活動日誌"),
        ("content.json", "公告內容"),
        ("automation.json", "自動化設定"),
        ("lottery_config.json", "抽獎設定"),
        ("lottery_records.json", "抽獎記錄"),
        ("shop_config.json", "商城設定"),
        ("shop_purchases.json", "商城購買記錄"),
        ("predictions.db", "SQLite 資料庫"),
    ]

    for file_name, description in download_files:
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{file_name}**")
        c1.caption(description)

        if os.path.exists(file_name):
            size = os.path.getsize(file_name)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_name)).strftime('%Y-%m-%d %H:%M:%S')
            c2.caption(f"大小：{size/1024:.1f} KB　|　最後更新：{mtime}")
            with open(file_name, "rb") as f:
                c3.download_button(
                    label="📥 下載",
                    data=f,
                    file_name=file_name,
                    key=f"download_{file_name}"
                )
        else:
            c2.caption("暫無備份")
            c3.caption("—")

    st.divider()

    # ===== AI 預測記錄 =====
    st.markdown("### 🤖 AI 預測記錄")
    try:
        from database import load_predictions
        ai_data = load_predictions()
        if not ai_data:
            st.info("📭 暫無預測記錄")
        else:
            st.info(f"✅ 成功讀取 {len(ai_data)} 個預測記錄")
            df_ai = pd.DataFrame([
                {
                    "日期": v.get("date"),
                    "場次": v.get("race"),
                    "頭馬": v.get("top_horse"),
                    "預測時間": str(v.get("predicted_at", ""))[:16]
                }
                for v in ai_data.values()
            ])
            st.dataframe(df_ai, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")

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
# ============================================================
# 💰 付款審核
# ============================================================
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

    st.divider()
    st.markdown(f"### ✅ 已批准({len(approved)} 筆)")
    if not approved.empty:
        display_cols = [c for c in ['username', 'amount', 'vip_days', 'rewarded_at'] if c in approved.columns]
        st.dataframe(approved[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("暫無已批准記錄。")

    if not rejected.empty:
        st.markdown(f"### ❌ 已拒絕({len(rejected)} 筆)")
        display_cols = [c for c in ['username', 'amount', 'vip_days', 'rewarded_at'] if c in rejected.columns]
        st.dataframe(rejected[display_cols], use_container_width=True, hide_index=True)

def admin_course_analysis():
    st.subheader("📊 場地/路程勝率分析")
    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
        df = df.reset_index(drop=True)

        # 名次
        pos_series, pos_name = _get_pos_series(df)
        st.caption(f"📊 使用名次欄位：**{pos_name}**(有效數據：{pos_series.notna().sum()})")

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
    acc = load_accuracy()
    records = acc.get('records', [])
    valid = [r for r in records if r.get('is_hit') is not None]
    if not valid:
        st.info("暫無足夠數據")
        return
    df = pd.DataFrame(valid)
    if 'date' not in df.columns:
        st.info("缺少日期")
        return
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby('month').agg(
        total=('is_hit', 'count'),
        hit=('is_hit', lambda x: (x == True).sum())
    ).reset_index()
    monthly['hit_rate'] = monthly['hit'] / monthly['total']
    st.dataframe(monthly, use_container_width=True)

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
                "percentage": "百分比折扣(如 20% off)",
                "fixed": "固定金額(如 -$50)",
                "free": "完全免費",
                "first_order": "首單優惠",
                "min_spend": "滿減(消費滿 X 減 Y)"
            }.get(x, x)
        )
    with col2:
        dval = st.number_input("折扣數值", min_value=0, value=20, key="pr_dval")
        min_spend = st.number_input("最低消費 (滿減用)", min_value=0, value=100, key="pr_minspend")
        max_uses = st.number_input("每人限用次數", min_value=0, value=1, key="pr_maxuses")
    with col3:
        st.write("")
        st.write("")
        note = st.text_input("備註(選填)", key="pr_note")

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
def admin_accuracy_monitor():
    st.subheader("📈 AI 預測準確率監控(頭 3 名)")

    from database import load_predictions
    ai_data = load_predictions()  # 👈 統一用 ai_data

    if not ai_data:
        st.warning("⚠️ 尚未有任何預測紀錄，請先執行預測")
        return

    st.info(f"✅ 成功讀取 {len(ai_data)} 個預測紀錄")

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
            "🐎 馬匹命中率(預測頭3名中，有幾多匹跑入真實頭3名)",
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
def admin_reward_management():
    st.subheader("❤️ 打賞管理")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    tab1, tab2 = st.tabs(["📋 審核打賞", "⚙️ 打賞設定"])

    # ============================================================
    # 📋 Tab 1：審核打賞
    # ============================================================
    with tab1:
        st.caption("審核用戶打賞，批准後會自動加 VIP 天數。")

        try:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/reward_history?order=rewarded_at.desc&limit=50",
                headers=headers
            )
            records = res.json() if res.status_code == 200 else []
        except Exception as e:
            st.error(f"❌ 讀取打賞記錄失敗：{e}")
            records = []

        if not records:
            st.info("📭 暫無打賞記錄。")
        else:
            df = pd.DataFrame(records)
            if 'status' in df.columns:
                pending = df[df['status'] == 'pending']
                approved = df[df['status'] == 'approved']
                rejected = df[df['status'] == 'rejected']
            else:
                pending = df
                approved = pd.DataFrame()
                rejected = pd.DataFrame()

            st.markdown(f"### 📋 待審核({len(pending)} 筆)")
            if pending.empty:
                st.info("✅ 暫無待審核打賞。")
            else:
                for _, row in pending.iterrows():
                    with st.container():
                        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 2, 1, 1])
                        c1.write(f"👤 **{row.get('username', '未知')}**")
                        c2.write(f"${row.get('amount', 0):.0f}")
                        c3.write(f"+{row.get('vip_days', 0)} 日")
                        c4.caption(f"🕐 {str(row.get('rewarded_at', ''))[:16]}")

                        if c5.button("✅ 批准", key=f"approve_{row['id']}", use_container_width=True):
                            username = row.get('username')
                            vip_days = int(row.get('vip_days', 0))

                            u_res = requests.get(
                                f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
                                headers=headers
                            )
                            if u_res.status_code == 200 and u_res.json():
                                user = u_res.json()[0]
                                expiry = user.get('expiry_date') or datetime.now().strftime('%Y-%m-%d')
                                try:
                                    expiry_dt = datetime.strptime(expiry, '%Y-%m-%d')
                                except Exception:
                                    expiry_dt = datetime.now()
                                new_expiry = (expiry_dt + timedelta(days=vip_days)).strftime('%Y-%m-%d')

                                requests.patch(
                                    f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
                                    headers=headers,
                                    json={
                                        "user_group": "VIP",
                                        "is_paid": True,
                                        "expiry_date": new_expiry
                                    }
                                )

                            requests.patch(
                                f"{SUPABASE_URL}/rest/v1/reward_history?id=eq.{row['id']}",
                                headers=headers,
                                json={"status": "approved"}
                            )
                            st.success(f"✅ 已批准 {username}，加 {vip_days} 日 VIP")
                            st.rerun()

                        if c6.button("❌ 拒絕", key=f"reject_{row['id']}", use_container_width=True):
                            requests.patch(
                                f"{SUPABASE_URL}/rest/v1/reward_history?id=eq.{row['id']}",
                                headers=headers,
                                json={"status": "rejected"}
                            )
                            st.warning(f"已拒絕 {row.get('username', '')} 嘅打賞")
                            st.rerun()

            st.divider()
            st.markdown(f"### ✅ 已批准({len(approved)} 筆)")
            if not approved.empty:
                display_cols = [c for c in ['username', 'amount', 'vip_days', 'rewarded_at'] if c in approved.columns]
                st.dataframe(approved[display_cols], use_container_width=True, hide_index=True)
            else:
                st.info("暫無已批准記錄。")

            if not rejected.empty:
                st.markdown(f"### ❌ 已拒絕({len(rejected)} 筆)")
                display_cols = [c for c in ['username', 'amount', 'vip_days', 'rewarded_at'] if c in rejected.columns]
                st.dataframe(rejected[display_cols], use_container_width=True, hide_index=True)

    # ============================================================
    # ⚙️ Tab 2：打賞設定(修改金額、VIP天數、新增、刪除)
    # ============================================================
    with tab2:
        st.caption("喺呢度新增、修改或刪除打賞選項，前台會即時同步。")

        try:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/reward_config?order=amount.asc",
                headers=headers
            )
            configs = res.json() if res.status_code == 200 else []
        except Exception as e:
            st.error(f"❌ 讀取失敗：{e}")
            configs = []

        if not configs:
            st.info("📭 暫無打賞選項，請喺下面新增。")
            df = pd.DataFrame(columns=['id', 'amount', 'vip_days', 'label', 'enabled'])
        else:
            df = pd.DataFrame(configs)
            for col in ['id', 'amount', 'vip_days', 'label', 'enabled']:
                if col not in df.columns:
                    df[col] = None

        st.markdown("### 📝 編輯現有選項")
        if not df.empty:
            edited = st.data_editor(
                df[['id', 'amount', 'vip_days', 'label', 'enabled']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "amount": st.column_config.NumberColumn("金額 ($)", min_value=1, step=1),
                    "vip_days": st.column_config.NumberColumn("VIP 天數", min_value=1, step=1),
                    "label": st.column_config.TextColumn("顯示標籤", max_chars=30),
                    "enabled": st.column_config.CheckboxColumn("啟用")
                },
                key="reward_config_editor"
            )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 儲存所有修改", type="primary", use_container_width=True):
                    success = 0
                    for _, row in edited.iterrows():
                        try:
                            res = requests.patch(
                                f"{SUPABASE_URL}/rest/v1/reward_config?id=eq.{row['id']}",
                                headers=headers,
                                json={
                                    "amount": float(row['amount']),
                                    "vip_days": int(row['vip_days']),
                                    "label": str(row['label']),
                                    "enabled": bool(row['enabled'])
                                }
                            )
                            if res.status_code in [200, 204]:
                                success += 1
                        except Exception:
                            pass
                    st.success(f"✅ 已更新 {success} 個選項")
                    st.rerun()

            with c2:
                if st.button("🔄 重新載入", use_container_width=True):
                    st.rerun()

            st.markdown("### 🗑️ 刪除選項")
            delete_id = st.selectbox(
                "選擇要刪除嘅選項",
                options=df['id'].tolist(),
                format_func=lambda x: f"ID {x} - {df[df['id']==x]['label'].values[0]} (${df[df['id']==x]['amount'].values[0]})",
                key="delete_reward_select"
            )
            if st.button("❌ 確認刪除", type="secondary"):
                try:
                    requests.delete(
                        f"{SUPABASE_URL}/rest/v1/reward_config?id=eq.{delete_id}",
                        headers=headers
                    )
                    st.success(f"✅ 已刪除選項 ID {delete_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 刪除失敗：{e}")

        st.divider()
        st.markdown("### ➕ 新增打賞選項")
        with st.form("add_reward_form"):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                new_amount = st.number_input("金額 ($)", min_value=1, value=20, step=1)
            with c2:
                new_days = st.number_input("VIP 天數", min_value=1, value=3, step=1)
            with c3:
                new_label = st.text_input("顯示標籤", value="☕ 一杯咖啡", max_chars=30)

            if st.form_submit_button("➕ 新增選項", type="primary"):
                try:
                    payload = {
                        "amount": float(new_amount),
                        "vip_days": int(new_days),
                        "label": new_label,
                        "enabled": True
                    }
                    res = requests.post(
                        f"{SUPABASE_URL}/rest/v1/reward_config",
                        headers=headers,
                        json=payload
                    )
                    if res.status_code in [200, 201, 204]:
                        st.success(f"✅ 已新增：{new_label} (${new_amount} → {new_days} 日 VIP)")
                        st.rerun()
                    else:
                        st.error(f"❌ 新增失敗：{res.text}")
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")

    st.divider()
    st.markdown(f"### ✅ 已批准({len(approved)} 筆)")
    if not approved.empty:
        display_cols = [c for c in ['username', 'amount', 'vip_days', 'rewarded_at'] if c in approved.columns]
        st.dataframe(approved[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("暫無已批准記錄。")

    if not rejected.empty:
        st.markdown(f"### ❌ 已拒絕({len(rejected)} 筆)")
        display_cols = [c for c in ['username', 'amount', 'vip_days', 'rewarded_at'] if c in rejected.columns]
        st.dataframe(rejected[display_cols], use_container_width=True, hide_index=True)
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
             'system_config.json', 'accuracy.json', 'lottery_config.json', 'shop_config.json']
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
        st.success(f"✅ 維護完成，處理 {len(exp)} 位過期用戶")

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
                'paid': '💰 付費用戶(日/月)',
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
        ("📤 付款審核", admin_payment_review),      # 👈 刪除前面個 # 號
        ("❤️ 打賞管理", admin_reward_management),   # 👈 加呢行
        ("📡 監控", admin_monitoring),
        ("📝 內容", admin_content),
        ("🤖 自動維護", admin_auto_maintenance),
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

def login_page():
    st.title("🔐 登入 / 註冊")
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
                    log_user_activity(u, "登入", "登入成功")
                    st.session_state.role = user.get('group', 'free')
                    st.rerun()
                else:
                    st.error("❌ 用戶名或密碼錯誤")
    else:
        st.subheader("📝 註冊新帳號")
        with st.form("register_form"):
            new_user = st.text_input("用戶名稱(最少 3 個字)", key="reg_user")
            phone = st.text_input("手機號碼(可選)", key="reg_phone")
            new_pass = st.text_input("密碼", type="password", key="reg_pass")
            new_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")

            # ===== 邀請碼 =====
            if CONFIG.get("enable_invite_reward", True):
                invite_code_input = st.text_input(
                    "邀請碼(如有)",
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
                            'predictions_limit': CONFIG.get("free_limit", 2),
                            'history': [],
                            'terms_agreed': datetime.now().isoformat(),
                            'invite_code': new_user.upper() + str(random.randint(100, 999)),
                            'invited_by': invited_by,
                            'invite_rewards': 0,
                            'invite_count': 0,
                            'referred_users': [],  # 直接下線列表
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

                                # Level 2：上線(邀請人嘅邀請人)
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

def main():
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
        # 👇 新加嘅「常見問題」按鈕，同後台平排
        if st.button("❓ 常見問題", use_container_width=True, key="faq_btn"):
            st.switch_page("pages/FAQ.py")
    with c4:
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
                    new_pw = st.text_input("新密碼(最少 4 字)", type="password", key="pc_new_pw")
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
    with c5:
        if st.session_state.get('logged_in', False):
            if st.button("🚪 登出", use_container_width=True, key="logout_main"):
                for k in ['logged_in', 'username', 'role']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    st.markdown("---")
    
    # =========================================================================
    # 👇👇👇 重要：倒數卡片(⏰ 距離下場賽事)一定要放喺呢度！ 👇👇👇
    # 你必須將包含「⏰ 距離下場賽事」嘅代碼，原封不動咁貼喺呢度。
    # 記住：呢度嘅代碼前面「唔可以有 with c1: 或者 with c2: 嘅縮排」，佢一定要係最左邊(或者同上面 c1, c2... 對齊)。
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
                        st.success(f"✅ 準備就緒(共 {len(day_races)} 場)")
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
                            status.text(f"⏳ 預測第 {rn} 場中...({i+1}/{len(day_races)})")
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

                st.markdown("#### 🎯 孖寶(連續 2 場)")
                if len(race_list) >= 2:
                    double_start = st.selectbox(
                        "孖寶起始場次", race_list, index=None,
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

                st.markdown("#### 🎯 三寶(連續 3 場)")
                if len(race_list) >= 3:
                    treble_start = st.selectbox(
                        "三寶起始場次", race_list, index=None,
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

                st.markdown("#### 🎯 六環彩(連續 6 場)")
                if len(race_list) >= 6:
                    six_up_start = st.selectbox(
                        "六環彩起始場次", race_list, index=None,
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
                            st.warning(f"⚠️ 由第 {six_up_start} 場開始，唔夠 6 場數據(只有 {len(six_up_races)} 場)")
                else:
                    st.warning("⚠️ 唔夠 6 場賽事，冇六環彩")

                st.divider()

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
                            rename_map = {}
                            if '馬名' in df.columns:
                                rename_map['馬名'] = '馬名'
                            elif 'horse_name' in df.columns:
                                rename_map['horse_name'] = '馬名'
                            if '檔位' in df.columns:
                                rename_map['檔位'] = '檔位'
                            elif 'draw' in df.columns:
                                rename_map['draw'] = '檔位'
                            if '賠率' in df.columns:
                                rename_map['賠率'] = '賠率'
                            elif 'win_odds' in df.columns:
                                rename_map['win_odds'] = '賠率'
                            if '騎師' in df.columns:
                                rename_map['騎師'] = '騎師'
                            elif 'jockey' in df.columns:
                                rename_map['jockey'] = '騎師'
                            if '練馬師' in df.columns:
                                rename_map['練馬師'] = '練馬師'
                            elif 'trainer' in df.columns:
                                rename_map['trainer'] = '練馬師'
                            if '預測勝率' in df.columns:
                                rename_map['預測勝率'] = '勝率'
                            elif '勝率' in df.columns:
                                rename_map['勝率'] = '勝率'
                            valid_cols = [c for c in rename_map.keys() if c in df.columns]
                            df_show = df[valid_cols].head(3).copy()
                            df_show.rename(columns=rename_map, inplace=True)
                            if '勝率' in df_show.columns:
                                df_show['勝率'] = df_show['勝率'].apply(lambda x: f"{x:.1%}")
                            st.dataframe(df_show, use_container_width=True, hide_index=True)

    # ============================================================
    # 🚀 單場預測區塊(按鈕版)
    # ============================================================
    cd, cbtn = st.columns([3, 1])
    with cd:
        date = st.date_input("📅 日期", value=pd.to_datetime("2026-09-06"), key="pd_date")
    with cbtn:
        st.write("")
        run_predict = st.button("🚀 執行預測", type="primary", use_container_width=True, key="pd_btn")

    st.markdown("**🏇 選擇場次：**")
    if 'selected_race' not in st.session_state:
        st.session_state.selected_race = 1

    race_cols = st.columns(6)
    for i in range(11):
        race_num = i + 1
        col_idx = i % 6
        with race_cols[col_idx]:
            if st.session_state.selected_race == race_num:
                if st.button(f"**{race_num}**", key=f"race_btn_{race_num}", use_container_width=True, type="primary"):
                    st.session_state.selected_race = race_num
            else:
                if st.button(f"{race_num}", key=f"race_btn_{race_num}", use_container_width=True):
                    st.session_state.selected_race = race_num
        if col_idx == 5 and i < 10:
            race_cols = st.columns(6)

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
    # 📊 AI 預測表現 & 賽果對比(獨立顯示，唔使預測)
    # ============================================================
    if st.session_state.get('logged_in', False):
        st.divider()
        with st.expander("📊 AI 預測表現 & 賽果對比 (點擊展開)", expanded=False):
            try:
                from database import load_predictions
                ai_data = load_predictions()

                if not ai_data:
                    st.warning("⚠️ 尚未有任何預測紀錄，請先執行預測")
                else:
                    st.info(f"✅ 成功讀取 {len(ai_data)} 個預測紀錄")
                    
                    result_file = "race_results_clean.csv"
                    df_results = pd.DataFrame()
                    if os.path.exists(result_file):
                        try:
                            df_results = pd.read_csv(result_file, encoding='utf-8-sig')
                            required_cols = ['race_date', 'race_no', 'horse_name', 'finish_position']
                            if all(col in df_results.columns for col in required_cols):
                                df_results['horse_name'] = df_results['horse_name'].astype(str).str.strip()
                                df_results['finish_position'] = pd.to_numeric(df_results['finish_position'], errors='coerce')
                                df_results['race_no'] = pd.to_numeric(df_results['race_no'], errors='coerce')
                                df_results = df_results.dropna(subset=['race_no'])
                                df_results['race_no'] = df_results['race_no'].astype(int)
                                df_results['race_date'] = pd.to_datetime(df_results['race_date'], errors='coerce')
                            else:
                                st.error("❌ 賽果檔案缺少必要欄位")
                                df_results = pd.DataFrame()
                        except Exception as e:
                            st.error(f"❌ 讀取賽果失敗：{e}")
                            df_results = pd.DataFrame()
                    else:
                        st.warning("⚠️ 找不到賽果檔案 race_results_clean.csv")

                    pred_list = []
                    for key, value in ai_data.items():
                        if '_' not in key: continue
                        parts = key.split('_')
                        if len(parts) != 2: continue
                        date_str, race_no_str = parts[0], parts[1]
                        if not race_no_str.isdigit(): continue
                        race_no_c = int(race_no_str)
                        if not isinstance(value, dict): continue
                        horse_list = value.get('all_horses', [])
                        if not horse_list or not isinstance(horse_list, list):
                            top = value.get('top_horse')
                            if top: horse_list = [top]
                            else: continue
                        cleaned = [str(h).strip() for h in horse_list if str(h).strip()]
                        for idx, horse in enumerate(cleaned[:4], 1):
                            pred_list.append({'日期': date_str, '場次': race_no_c, '預測名次': idx, '預測馬': horse})

                    if pred_list and not df_results.empty:
                        df_pred = pd.DataFrame(pred_list)
                        df_pred['場次'] = df_pred['場次'].astype(int)
                        df_pred['預測名次'] = df_pred['預測名次'].astype(int)

                        pred_dates = sorted(df_pred['日期'].unique())
                        result_dates = df_results['race_date'].dt.strftime('%Y-%m-%d').unique()
                        available_dates = [d for d in pred_dates if d in result_dates]

                        if available_dates:
                            selected_date = st.selectbox("📅 選擇日期", available_dates, format_func=lambda x: x, key="ai_cmp_date")
                            df_pred_date = df_pred[df_pred['日期'] == selected_date].copy()
                            df_result_date = df_results[df_results['race_date'].dt.strftime('%Y-%m-%d') == selected_date].copy()

                            pred_races = sorted(df_pred_date['場次'].unique())
                            result_races = sorted(df_result_date['race_no'].unique())
                            available_races = [r for r in pred_races if r in result_races]

                            if available_races:
                                selected_race = st.selectbox("🏇 選擇場次", available_races, format_func=lambda x: f"第 {x} 場", key="ai_cmp_race")
                                df_pred_race = df_pred_date[df_pred_date['場次'] == selected_race].copy()
                                df_result_race = df_result_date[df_result_date['race_no'] == selected_race].copy().sort_values('finish_position').head(4)
                                df_result_race = df_result_race.rename(columns={'finish_position': '真實名次', 'horse_name': '真實馬'})

                                real_top3_names = df_result_race['真實馬'].tolist()
                                df_pred_race['結果'] = df_pred_race['預測馬'].apply(lambda x: '命中' if x in real_top3_names else '失準')
                                
                                display_pred = df_pred_race[['預測名次', '預測馬', '結果']].copy()
                                display_pred.columns = ['名次', '預測馬', '結果']
                                display_real = df_result_race[['真實名次', '真實馬']].reset_index(drop=True)
                                display_real.columns = ['真實名次', '真實馬']
                                
                                # 🔥 修正對比邏輯：只按馬名，唔理名次
                                real_top3_names = df_result_race['真實馬'].tolist()
                                
                                df_pred_race['結果'] = df_pred_race['預測馬'].apply(
                                    lambda x: '命中' if x in real_top3_names else '失準'
                                )
                                
                                # 🛠️ 關鍵修正：強制重置索引，確保左右對齊！
                                df_pred_race = df_pred_race.reset_index(drop=True)
                                df_result_race = df_result_race.reset_index(drop=True)
                                
                                # 準備左邊(預測)
                                display_pred = df_pred_race[['預測名次', '預測馬', '結果']].copy()
                                display_pred.columns = ['名次', '預測馬', '結果']
                                display_pred['名次'] = display_pred['名次'].astype(int)  # 轉做整數
                                
                                # 準備右邊(真實)
                                display_real = df_result_race[['真實名次', '真實馬']].copy()
                                display_real.columns = ['真實名次', '真實馬']
                                display_real['真實名次'] = display_real['真實名次'].astype(int)  # 轉做整數
                                
                                # 左右合併(因為索引已經重置，所以會完美對齊)
                                display_df = pd.concat([display_pred, display_real], axis=1)

                                st.write(f"📊 {selected_date} 第 {selected_race} 場 預測 vs 賽果")

                                def highlight_row(row):
                                    if row['結果'] == '命中': return ['background-color: #d4edda; color: black'] * len(row)
                                    elif row['結果'] == '失準': return ['background-color: #f8d7da; color: black'] * len(row)
                                    return ['background-color: white; color: black'] * len(row)

                                st.dataframe(display_df.style.apply(highlight_row, axis=1), use_container_width=True, hide_index=True)
                            else:
                                st.info(f"ℹ️ {selected_date} 沒有可比對嘅場次")
                        else:
                            st.info("ℹ️ 沒有日期同時有預測同賽果數據")
                    else:
                        st.info("ℹ️ 請確保已有預測紀錄及賽果數據")
            except Exception as e:
                st.error(f"❌ 讀取預測紀錄失敗：{e}")
    # ===== 打賞功能 =====
    st.divider()
    st.subheader("❤️ 打賞支持")
    if st.session_state.get('logged_in', False):
        st.caption("你嘅支持係我哋繼續開發嘅動力！打賞後會自動增加 VIP 天數。")
        
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        try:
            res = requests.get(f"{SUPABASE_URL}/rest/v1/reward_config?enabled=eq.true&order=amount.asc", headers=headers)
            configs = res.json() if res.status_code == 200 else []
        except Exception:
            configs = []
        
        if not configs:
            st.info("暫未開放打賞，敬請期待！")
        else:
            cols = st.columns(len(configs))
            for i, cfg in enumerate(configs):
                with cols[i]:
                    st.markdown(f"### {cfg.get('label', '打賞')}")
                    st.markdown(f"**${cfg['amount']:.0f}**")
                    st.caption(f"送 {cfg['vip_days']} 日 VIP")
                    if st.button(f"打賞 ${cfg['amount']:.0f}", key=f"reward_{cfg['id']}", use_container_width=True):
                        st.session_state['selected_reward'] = cfg
            
            if 'selected_reward' in st.session_state:
                cfg = st.session_state['selected_reward']
                st.divider()
                st.info(f"你選擇咗：**{cfg['label']}**(${cfg['amount']:.0f} → {cfg['vip_days']} 日 VIP)")
                st.markdown("**付款方式：FPS 轉數快**")
                st.code("FPS ID: 你的電話號碼或 FPS ID", language=None)
                st.markdown("付款後，請撳下面個掣，管理員會盡快審核。")
                
                if st.button("✅ 我已經付款", type="primary"):
                    headers_post = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "username": st.session_state.get('username', 'unknown'),
                        "amount": cfg['amount'],
                        "vip_days": cfg['vip_days'],
                        "rewarded_at": datetime.now().isoformat(),
                        "status": "pending"
                    }
                    requests.post(f"{SUPABASE_URL}/rest/v1/reward_history", headers=headers_post, json=payload)
                    st.success("✅ 已提交！管理員審核後會自動加 VIP 天數。")
                    if 'selected_reward' in st.session_state:
                        del st.session_state['selected_reward']
    else:
        st.info("請先登入以使用打賞功能")

    st.divider()
    st.warning("⚠️ 免責聲明：本系統預測僅供參考，不構成投注建議。賽馬活動涉及風險，用戶應量力而為。用戶必須年滿18歲。")
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · v16.1")
    st.caption("💬 Telegram：@bryhjdjbrbxibvrjskofndhiebdpaq")


if __name__ == '__main__':
    main()
