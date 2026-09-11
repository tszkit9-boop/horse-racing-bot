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

st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    "enable_registration": True, "enable_payment": True, "enable_admin": True,
    "enable_lottery": True, "enable_shop": True,
    "currency": "HKD", "free_limit": 2, "admin_password": "z54060437K",
    "price_day": 18, "price_month": 128, "price_quarter": 328,
    "daily_virtual_coin": 1000, "virtual_coin_enabled": True,
    "enable_invite_reward": True,
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
                    u['predictions_limit'] = CONFIG.get("free_limit", 2)
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
    return load_json(LOTTERY_FILE, {"prizes": []})

def save_lottery_config(c):
    return save_json(LOTTERY_FILE, c)

def load_shop_config():
    return load_json(SHOP_FILE, {"items": []})

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

def generate_pool_recommendations(df):
    if df.empty:
        return "⚠️ 無數據"
    names = df['horse_name'].tolist()
    probs = df['預測勝率'].tolist()

    def sc(idxs):
        s = 1.0
        for i in idxs:
            s *= probs[i]
        return s / len(idxs)

    rec = "【獨贏】\n"
    for _, r in df.head(3).iterrows():
        rec += f"  {r['horse_name']}（{r['預測勝率']:.1%}）\n"

    rec += "\n【位置】\n"
    for _, r in df.head(4).iterrows():
        rec += f"  {r['horse_name']}（{r['預測勝率']:.1%}）\n"

    rec += "\n【連贏】\n"
    pairs = sorted(
        [(sc([i, j]), i, j)
         for i in range(min(len(names), 5))
         for j in range(i + 1, min(len(names), 6))],
        reverse=True
    )
    for _, i, j in pairs[:5]:
        rec += f"  {names[i]} + {names[j]}\n"

    rec += "\n【位置Q】\n"
    qp = sorted(
        [(sc([i, j]), i, j)
         for i in range(min(len(names), 6))
         for j in range(i + 1, min(len(names), 8))
         if j < len(names)],
        reverse=True
    )
    for _, i, j in qp[:6]:
        rec += f"  {names[i]} + {names[j]}\n"

    rec += "\n【三重彩 / 單T】\n"
    tc = sorted(
        [(sc([i, j, k]), i, j, k)
         for i in range(min(len(names), 4))
         for j in range(min(len(names), 5))
         for k in range(min(len(names), 6))
         if len({i, j, k}) == 3],
        reverse=True
    )
    for _, i, j, k in tc[:5]:
        rec += f"  {names[i]} > {names[j]} > {names[k]}\n"

    rec += "\n【四重彩】\n"
    qt = sorted(
        [(sc([i, j, k, l]), i, j, k, l)
         for i in range(min(len(names), 4))
         for j in range(min(len(names), 5))
         for k in range(min(len(names), 6))
         for l in range(min(len(names), 7))
         if len({i, j, k, l}) == 4],
        reverse=True
    )
    for _, i, j, k, l in qt[:3]:
        rec += f"  {names[i]} > {names[j]} > {names[k]} > {names[l]}\n"

    return rec

def run_prediction(date_str, race_no):
    if not os.path.exists("racecard_uploaded.csv"):
        st.error("❌ 找不到 racecard_uploaded.csv")
        return None, None

    try:
        df = pd.read_csv("racecard_uploaded.csv", encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None, None

    rename_map = {
        '馬名': 'horse_name', '檔位': 'draw', '場次': 'race_no',
        '比賽日期': 'race_date', '騎師': 'jockey', '練馬師': 'trainer',
        '負磅': 'weight', '馬號': 'horse_id', '賠率': 'win_odds'
    }
    existing = [c for c in rename_map if c in df.columns]
    if existing:
        df.rename(columns={c: rename_map[c] for c in existing}, inplace=True)

    if 'race_date' not in df.columns:
        st.error("❌ 缺少 '比賽日期'")
        return None, None

    df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
    df = df.dropna(subset=['race_date'])
    df['race_date_str'] = df['race_date'].dt.strftime('%Y-%m-%d')

    available_dates = sorted(df['race_date_str'].unique())
    if not available_dates:
        st.error("❌ 無可用日期")
        return None, None
    if date_str not in available_dates:
        date_str = available_dates[-1]

    df_date = df[df['race_date_str'] == date_str]
    if 'race_no' not in df_date.columns:
        st.error("❌ 缺少 '場次'")
        return None, None

    if race_no not in df_date['race_no'].unique():
        avail = sorted(df_date['race_no'].unique())
        if avail:
            race_no = avail[0]
        else:
            st.error("❌ 無場次")
            return None, None

    filtered = df_date[df_date['race_no'] == race_no]
    if filtered.empty:
        st.error("❌ 無馬匹數據")
        return None, None

    st.success(f"✅ 成功載入 {date_str} 第 {race_no} 場，共 {len(filtered)} 匹馬")

    if 'win_odds' in filtered.columns:
        win_odds = pd.to_numeric(filtered['win_odds'], errors='coerce').fillna(4.0).replace(0, 4.0)
    else:
        win_odds = pd.Series([4.0] * len(filtered))

    inv = 1 / win_odds
    final_pred = inv / inv.sum()

    result_cols = [c for c in ['horse_name', 'draw', 'weight', 'jockey', 'trainer'] if c in filtered.columns]
    result_df = filtered[result_cols].copy()
    result_df['預測勝率'] = final_pred.values
    result_df['值博指數'] = result_df['預測勝率'] * 10
    result_df['信心指數'] = result_df['預測勝率'].apply(
        lambda x: '⭐⭐⭐ 高' if x > 0.2 else '⭐⭐ 中' if x > 0.1 else '⭐ 低'
    )
    result_df = result_df.sort_values('預測勝率', ascending=False)

    ai_file = "ai_predictions.json"
    ai_data = load_json(ai_file) if os.path.exists(ai_file) else {}
    key = f"{date_str}_{race_no}"
    ai_data[key] = {
        "date": date_str,
        "race": race_no,
        "top_horse": result_df.iloc[0]['horse_name'],
        "top_prob": float(result_df.iloc[0]['預測勝率']),
        "all_horses": result_df['horse_name'].tolist(),
        "predicted_at": datetime.now().isoformat()
    }
    with open(ai_file, 'w', encoding='utf-8') as f:
        json.dump(ai_data, f, ensure_ascii=False, indent=2)

    return result_df, generate_pool_recommendations(result_df)

def _rank_from_csv(col_keywords):
    try:
        df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]

        pos_col = None
        for c in df.columns:
            if str(c).lower() in ['pla', '名次', 'finish_position']:
                pos_col = c
                break

        target_col = None
        for c in df.columns:
            if any(k in str(c).lower() for k in col_keywords):
                target_col = c
                break

        if not pos_col or not target_col:
            st.error(f"❌ 搵唔到欄位！名次: {pos_col}, 目標: {target_col}")
            return None

        ts = df[target_col]
        if isinstance(ts, pd.DataFrame):
            ts = ts.iloc[:, 0]
        ps = df[pos_col]
        if isinstance(ps, pd.DataFrame):
            ps = ps.iloc[:, 0]

        temp = pd.DataFrame({
            'name': ts.astype(str).str.strip(),
            'finish_position': pd.to_numeric(
                ps.astype(str).str.extract(r'(\d+)')[0],
                errors='coerce'
            )
        })
        temp = temp.dropna(subset=['finish_position'])
        temp = temp[~temp['name'].str.lower().isin(['nan', 'none', ''])]

        if temp.empty:
            st.warning("⚠️ 過濾後數據為空！")
            return None

        total = temp.groupby('name').size().reset_index(name='總出賽')
        wins = temp[temp['finish_position'] == 1].groupby('name').size().reset_index(name='勝出')
        stats = pd.merge(total, wins, on='name', how='left').fillna({'勝出': 0})
        stats['勝率'] = (stats['勝出'] / stats['總出賽']).apply(lambda x: f"{x:.1%}")
        return stats.sort_values('勝出', ascending=False)
    except Exception as e:
        st.error(f"讀取失敗: {e}")
        return None

def admin_horse_ranking():
    st.subheader("🏇 馬匹勝率排行榜")
    stats = _rank_from_csv(['horse_name', '馬名'])
    if stats is not None:
        stats = stats.rename(columns={'name': '馬匹'})
        st.success(f"✅ 共 {len(stats)} 匹馬")
        st.dataframe(stats.head(30), use_container_width=True)

def admin_jockey_ranking():
    st.subheader("🏇 騎師勝率排行榜")
    stats = _rank_from_csv(['jockey'])
    if stats is not None:
        jmap = load_json("jockey_mapping.json") if os.path.exists("jockey_mapping.json") else {}
        stats['騎師'] = stats['name'].map(jmap).fillna(stats['name'])
        st.success(f"✅ 共 {len(stats)} 位騎師")
        st.dataframe(stats[['騎師', '總出賽', '勝出', '勝率']].head(30), use_container_width=True)

def admin_trainer_ranking():
    st.subheader("🏇 練馬師勝率排行榜")
    stats = _rank_from_csv(['trainer'])
    if stats is not None:
        tmap = load_json("trainer_mapping.json") if os.path.exists("trainer_mapping.json") else {}
        stats['練馬師'] = stats['name'].map(tmap).fillna(stats['name'])
        st.success(f"✅ 共 {len(stats)} 位練馬師")
        st.dataframe(stats[['練馬師', '總出賽', '勝出', '勝率']].head(30), use_container_width=True)

def admin_lottery_config():
    st.subheader("🎰 抽獎設定")
    config = load_lottery_config()
    prizes = config.get("prizes", [])
    st.write(f"目前有 **{len(prizes)}** 個獎品")
    if prizes:
        try:
            st.dataframe(pd.DataFrame(prizes), use_container_width=True)
        except Exception:
            pass

    st.divider()
    st.subheader("➕ 新增獎品")
    col1, col2, col3 = st.columns(3)
    with col1:
        p_name = st.text_input("獎品名稱", key="lot_name")
        p_type = st.selectbox(
            "獎品類型",
            ["virtual_coin", "vip_days", "free_predictions", "promo_code", "custom", "nothing"],
            key="lot_type"
        )
    with col2:
        p_value = st.number_input("數值", min_value=0, value=100, key="lot_value")
        p_weight = st.number_input("中獎機率（權重）", min_value=1, value=10, key="lot_weight")
    with col3:
        p_desc = st.text_input("描述", key="lot_desc")

    if st.button("➕ 新增獎品", key="add_lot"):
        prizes.append({
            "name": p_name, "type": p_type, "value": p_value,
            "weight": p_weight, "description": p_desc
        })
        config["prizes"] = prizes
        if save_lottery_config(config):
            st.success("✅ 已新增獎品！")
            st.rerun()
        else:
            st.error("❌ 儲存失敗")

    if prizes:
        st.divider()
        st.subheader("✏️ 編輯獎品")
        for i, p in enumerate(prizes):
            with st.expander(f"{p.get('name', '獎品')}（權重 {p.get('weight', 0)}）"):
                _w = _safe_int(p.get('weight', 10), 10)
                _v = _safe_int(p.get('value', 0), 0)
                nw = st.number_input("中獎機率", min_value=1, value=max(1, _w), key=f"ew_{i}")
                nv = st.number_input("數值", min_value=0, value=max(0, _v), key=f"ev_{i}")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("💾 儲存", key=f"sp_{i}"):
                        prizes[i]['weight'] = nw
                        prizes[i]['value'] = nv
                        config["prizes"] = prizes
                        save_lottery_config(config)
                        st.success("✅ 已儲存")
                        st.rerun()
                with cb:
                    if st.button("🗑️ 刪除", key=f"dp_{i}"):
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

def show_lottery_interface(username):
    st.subheader("🎰 每日抽獎")
    if not username:
        st.info("請先登入")
        return

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
    today = datetime.now().strftime('%Y-%m-%d')
    if user.get('last_lottery_date') == today:
        st.warning("⚠️ 今日已抽過獎，聽日再嚟！")
        return

    if st.button("🎲 抽獎！", type="primary", use_container_width=True):
        weights = [_safe_int(p.get('weight', 1), 1) for p in prizes]
        if sum(weights) <= 0:
            weights = [1] * len(prizes)
        chosen = random.choices(prizes, weights=weights, k=1)[0]
        ptype = chosen.get('type', 'nothing')
        pval = _safe_int(chosen.get('value', 0), 0)
        pname = chosen.get('name', '獎品')

        if ptype == 'virtual_coin':
            users[username]['virtual_balance'] = user.get('virtual_balance', 0) + pval
            st.success(f"🎉 恭喜你抽到 **{pname}**：${pval} 虛擬幣！")
        elif ptype == 'vip_days':
            users[username]['group'] = 'VIP'
            users[username]['predictions_limit'] = -1
            st.success(f"🎉 恭喜你抽到 **{pname}**：VIP {pval} 天！")
        elif ptype == 'free_predictions':
            if users[username].get('predictions_limit', 0) != -1:
                users[username]['predictions_limit'] = users[username].get('predictions_limit', 0) + pval
            st.success(f"🎉 恭喜你抽到 **{pname}**：{pval} 次免費預測！")
        elif ptype == 'promo_code':
            code = generate_promo_code()
            promos = load_promos()
            promos[code] = {
                "used": False,
                "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                "discount_type": "percentage",
                "discount_value": 20
            }
            save_promos(promos)
            st.success(f"🎉 恭喜你抽到優惠碼：**{code}**")
        else:
            st.info(f"你抽到：{pname}")

        users[username]['last_lottery_date'] = today
        save_users(users)

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
        st.info("暫無用戶")
        return
    df = pd.DataFrame.from_dict(users, orient='index')
    cols = [c for c in ['username', 'group', 'level', 'exp', 'total_usage', 'is_paid', 'virtual_balance'] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True)

def admin_manage_predictions():
    st.subheader("📊 管理用戶預測次數")
    users = load_users()
    if not users:
        st.info("暫無用戶")
        return
    sel = st.selectbox("選擇用戶", list(users.keys()), key="mp_user")
    if sel:
        cl = users[sel].get('predictions_limit', CONFIG['free_limit'])
        cu = users[sel].get('free_usage', 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("用戶", sel)
        c2.metric("剩餘次數", cl - cu if cl != -1 else "無限")
        c3.metric("已使用", cu)
        st.divider()
        act = st.radio("操作", ["增加次數", "減少次數", "設定為指定次數"], horizontal=True, key="mp_act")
        if act == "增加次數":
            a = st.number_input("增加", min_value=1, value=1, key="mp_add")
            if st.button("✅ 增加", key="mp_do_add"):
                users[sel]['predictions_limit'] = cl + a if cl != -1 else -1
                save_users(users)
                st.success(f"✅ 已增加 {a} 次")
                st.rerun()
        elif act == "減少次數":
            a = st.number_input("減少", min_value=1, value=1, key="mp_red")
            if st.button("✅ 減少", key="mp_do_red"):
                if cl == -1:
                    st.warning("無限無法減少")
                elif cl - a < 0:
                    st.error("不能低於 0")
                else:
                    users[sel]['predictions_limit'] = cl - a
                    save_users(users)
                    st.success(f"✅ 已減少 {a} 次")
                    st.rerun()
        else:
            a = st.number_input("設定（-1 = 無限）", min_value=-1, value=cl if cl != -1 else 10, key="mp_set")
            if st.button("✅ 設定", key="mp_do_set"):
                users[sel]['predictions_limit'] = a
                save_users(users)
                st.success("✅ 已設定")
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
    st.info("此功能需要更詳細的數據，暫未開放。")

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

def admin_promo_codes():
    st.subheader("🎟️ 優惠碼管理")
    promos = load_promos()
    c1, c2 = st.columns(2)
    with c1:
        if promos:
            st.dataframe(pd.DataFrame.from_dict(promos, orient='index'), use_container_width=True)
        else:
            st.info("暫無")
    with c2:
        dur = st.number_input("有效期 (天)", min_value=1, value=30, key="pr_dur")
        dt = st.selectbox("類型", ["percentage", "fixed", "free"], key="pr_dt")
        dv = st.number_input("折扣數值", min_value=0, value=20, key="pr_dv")
        if st.button("產生", key="pr_gen"):
            code = generate_promo_code()
            promos[code] = {
                "used": False,
                "expiry": (datetime.now() + timedelta(days=dur)).isoformat(),
                "discount_type": dt,
                "discount_value": dv
            }
            save_promos(promos)
            st.success(f"✅ `{code}`")
            st.rerun()

def admin_accuracy_monitor():
    st.subheader("📈 預測準確率監控")
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        st.info("暫無預測記錄")
        return
    df = pd.DataFrame(records)
    total = len(df)
    hit = df[df['is_hit'] == True].shape[0] if 'is_hit' in df.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("總預測", total)
    c2.metric("命中", hit)
    c3.metric("命中率", f"{hit/total:.2%}" if total > 0 else "0%")

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
    st.info("此功能暫未開放。")

def admin_security():
    st.subheader("🔐 安全與權限")
    logs = load_json(LOG_FILE)
    if logs.get('logs'):
        st.dataframe(pd.DataFrame(logs['logs'][-20:]), use_container_width=True)
    else:
        st.info("暫無日誌")

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
        ("📤 付款審核", admin_payment_review),
        ("📡 監控", admin_monitoring),
        ("📝 內容", admin_content),
        ("🤖 自動維護", admin_auto_maintenance),
        ("🤖 自動化", admin_automation),
        ("🔐 安全", admin_security),
        ("🎰 抽獎設定", admin_lottery_config),
        ("🛒 商城設定", admin_shop_config),
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
                    st.session_state.role = user.get('group', 'free')
                    st.rerun()
                else:
                    st.error("❌ 用戶名或密碼錯誤")
    else:
        with st.form("reg_form"):
            nu = st.text_input("新用戶名（最少 3 字）", key="reg_user")
            np1 = st.text_input("密碼", type="password", key="reg_p1")
            np2 = st.text_input("確認密碼", type="password", key="reg_p2")
            ag = st.checkbox("✅ 我已閱讀並同意服務條款", key="reg_agree")
            if st.form_submit_button("註冊"):
                if len(nu) < 3:
                    st.error("❌ 用戶名至少 3 字")
                elif np1 != np2:
                    st.error("❌ 密碼不一致")
                elif len(np1) < 4:
                    st.error("❌ 密碼至少 4 字")
                elif not ag:
                    st.error("❌ 請同意服務條款")
                else:
                    users = load_users()
                    if nu in users:
                        st.error("❌ 用戶名已被使用")
                    else:
                        users[nu] = {
                            'password': np1, 'phone': '', 'is_paid': False,
                            'paid_date': None, 'expiry_date': None,
                            'free_usage': 0, 'total_usage': 0,
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'note': '', 'group': 'free', 'plan': None,
                            'predictions_limit': CONFIG["free_limit"],
                            'history': [],
                            'terms_agreed': datetime.now().isoformat(),
                            'invite_code': nu.upper() + str(random.randint(100, 999)),
                            'invited_by': None, 'invite_rewards': 0, 'invite_count': 0,
                            'level': '🥉 銅牌會員', 'exp': 0, 'badges': [],
                            'virtual_balance': CONFIG.get('daily_virtual_coin', 1000),
                            'last_claim_date': '', 'bets': [], 'last_lottery_date': ""
                        }
                        save_users(users)
                        st.success("✅ 註冊成功！請登入")
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

    c1, c2, c3 = st.columns([5, 1, 1])
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
        if st.session_state.logged_in:
            if st.button("🚪 登出", use_container_width=True, key="logout_main"):
                for k in ['logged_in', 'username', 'role']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    st.markdown("---")
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
    cd, cr, cbtn = st.columns([2, 2, 1])
    with cd:
        date = st.date_input("📅 日期", value=pd.to_datetime("2026-09-06"), key="pd_date")
    with cr:
        race_no = st.selectbox("🏇 場次", list(range(1, 12)), index=0, key="pd_race")
    with cbtn:
        if st.button("🚀 執行預測", type="primary", use_container_width=True, key="pd_btn"):
            with st.spinner("預測中..."):
                result, pool = run_prediction(date.strftime("%Y-%m-%d"), race_no)
                if result is not None and not result.empty:
                    st.success("✅ 預測完成！")
                    if pool:
                        st.info(pool)
                    st.dataframe(result, use_container_width=True)

    # ============================================================
    # 🤖 AI 預測表現 & 賽果對比（全寬，喺預測下面）
    # ============================================================
    st.divider()
    with st.expander("🤖 AI 預測表現 & 賽果對比（點擊展開）", expanded=False):
        ai_file = "ai_predictions.json"
        predictions = {}
        if os.path.exists(ai_file):
            try:
                with open(ai_file, 'r', encoding='utf-8') as f:
                    predictions = json.load(f)
                st.info(f"✅ 成功讀取 {len(predictions)} 個預測紀錄")
            except Exception as e:
                st.error(f"❌ 讀取預測紀錄失敗：{e}")
                predictions = {}
        else:
            st.warning("⚠️ 尚未有任何預測紀錄，請先執行預測")

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

        pred_list = []
        if predictions:
            for key, value in predictions.items():
                if '_' not in key:
                    continue
                parts = key.split('_')
                if len(parts) != 2:
                    continue
                date_str, race_no_str = parts[0], parts[1]
                if not race_no_str.isdigit():
                    continue
                race_no_c = int(race_no_str)
                if not isinstance(value, dict):
                    continue
                horse_list = value.get('all_horses', [])
                if not horse_list or not isinstance(horse_list, list):
                    top = value.get('top_horse')
                    if top:
                        horse_list = [top]
                    else:
                        continue
                cleaned = [str(h).strip() for h in horse_list if str(h).strip()]
                for idx, horse in enumerate(cleaned[:4], 1):
                    pred_list.append({
                        '日期': date_str,
                        '場次': race_no_c,
                        '預測名次': idx,
                        '預測馬': horse
                    })

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
                    df_result_race = df_result_date[
                        df_result_date['race_no'] == selected_race
                    ].copy()
                    df_result_race = df_result_race.sort_values('finish_position').head(4)
                    df_result_race = df_result_race.rename(columns={
                        'finish_position': '真實名次',
                        'horse_name': '真實馬'
                    })

                    df_compare = df_pred_race.merge(
                        df_result_race[['真實名次', '真實馬']],
                        left_on='預測名次',
                        right_on='真實名次',
                        how='left'
                    )
                    df_compare['結果'] = df_compare.apply(
                        lambda row: '命中' if row['預測馬'] == row['真實馬'] else '失準',
                        axis=1
                    )

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

    st.divider()
    st.warning("⚠️ 免責聲明：本系統預測僅供參考，不構成投注建議。賽馬活動涉及風險，用戶應量力而為。用戶必須年滿18歲。")
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · v16.1")
    st.caption("💬 Telegram：@bryhjdjbrbxibvrjskofndhiebdpaq")


if __name__ == '__main__':
    main()
