#/usr/bin/env python
# -*- coding utf-8 -*-
"""賽馬預測系統 v160 - 完整可用版"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import random
import time
from datetime import datetime timedelta
import pytz
import warnings
warnings.filterwarnings('ignore')

try
    import plotlyexpress as px
    import plotlygraph_objects as go
    HAS_PLOTLY = True
except ImportError
    HAS_PLOTLY = False

# 第 24-29 行你原本嘅設定保留)
st.set_page_config(
    page_title="🏇 賽馬預測系統",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)
<style>
    div[data-testid="stToolbar"] { display none important }
    #MainMenu { display none important }
    footer { display none important }
    header { display none important }
</style>
""" unsafe_allow_html=True)
CONFIG_FILE = 'system_configjson'
DEFAULT_CONFIG = {
    "enable_registration" True "enable_payment" True "enable_admin" True
    "enable_lottery" True "enable_shop" True
    "currency" "HKD" "free_limit" 2 "admin_password" "z54060437K"
    "price_day" 18 "price_month" 128 "price_quarter" 328
    "daily_virtual_coin" 1000 "virtual_coin_enabled" True
    "enable_invite_reward" True    
    "invite_rewards" {
        "level1" 5   # 直接邀請人+5 次預測
        "level2" 2   # 上線A 邀請 BB 邀請 C → A 得 2 次)
        "level3" 1   # 上上線+1 次
    }
    # ===== 🎯 彩池設定 =====
    "pool_config" {
        "win" {"enabled" True "required_group" "free" "label" "獨贏"}
        "place" {"enabled" True "required_group" "free" "label" "位置"}
        "quinella" {"enabled" True "required_group" "free" "label" "連贏"}
        "quinella_place" {"enabled" True "required_group" "free" "label" "位置Q"}
        "tierce" {"enabled" True "required_group" "paid" "label" "三重彩"}
        "trio" {"enabled" True "required_group" "paid" "label" "單T"}
        "quartet" {"enabled" True "required_group" "VIP" "label" "四重彩"}
        "exacta" {"enabled" True "required_group" "VIP" "label" "二重彩"}
        "first4" {"enabled" True "required_group" "VIP" "label" "四連環"}
        "double" {"enabled" True "required_group" "VIP" "label" "孖寶"}
        "treble" {"enabled" True "required_group" "VIP" "label" "三寶"}
        "six_up" {"enabled" True "required_group" "VIP" "label" "六環彩"}
    }
}

def load_jsonfp default=None)
    if default is None
        default = {}
    if ospathexistsfp)
        try
            with openfp 'r' encoding='utf-8') as f
                return jsonloadf)
        except Exception
            return default
    return default

def save_jsonfp data)
    try
        with openfp 'w' encoding='utf-8') as f
            jsondumpdata f ensure_ascii=False indent=2)
        return True
    except Exception
        return False

def load_system_config)
    if ospathexistsCONFIG_FILE)
        try
            with openCONFIG_FILE 'r' encoding='utf-8') as f
                config = jsonloadf)
            for k v in DEFAULT_CONFIGitems)
                if k not in config
                    config[k] = v
            return config
        except Exception
            return DEFAULT_CONFIGcopy)
    else
        with openCONFIG_FILE 'w' encoding='utf-8') as f
            jsondumpDEFAULT_CONFIG f ensure_ascii=False indent=2)
        return DEFAULT_CONFIGcopy)

def save_system_configconfig)
    try
        with openCONFIG_FILE 'w' encoding='utf-8') as f
            jsondumpconfig f ensure_ascii=False indent=2)
        return True
    except Exception
        return False

CONFIG = load_system_config)

USER_DATA_FILE = 'usersjson'
FINANCE_FILE = 'financejson'
PROMO_FILE = 'promo_codesjson'
LOG_FILE = 'admin_logjson'
ACCURACY_FILE = 'accuracyjson'
CONTENT_FILE = 'contentjson'
PAYMENT_PROOFS_FILE = 'payment_proofsjson'
LOTTERY_FILE = 'lottery_configjson'
SHOP_FILE = 'shop_configjson'

import requests
import json
import random
from datetime import datetime

SUPABASE_URL = "https//fewanagxvezelufmuggqsupabaseco"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"

@stcache_datattl=60)  # 👈 加呢行快取 60 秒
def load_users)
    headers = {
        "apikey" SUPABASE_KEY
        "Authorization" f"Bearer {SUPABASE_KEY}"
    }
    try
        res = requestsgetf"{SUPABASE_URL}/rest/v1/usersselect=*" headers=headers)
        if resstatus_code == 200
            raw_users = resjson)
            result = {}
            for row in raw_users
                result[row["username"]] = {
                    "password" rowget"password" "")
                    "phone" rowget"phone" "")
                    "invite_code" rowget"invite_code" "")
                    "invited_by" rowget"invited_by" "")
                    "referred_users" jsonloadsrow["referred_users"]) if rowget"referred_users") else []
                    "invite_count" rowget"invite_count" 0)
                    "invite_rewards" rowget"invite_rewards" 0)
                    "group" rowget"user_group" "free")
                    "level" rowget"level" "🥉 銅牌會員")
                    "virtual_balance" rowget"virtual_balance" 1000)
                    "lottery_chances" rowget"lottery_chances" 0)
                    "last_lottery_reset" rowget"last_lottery_reset" "")
                    "created_at" rowget"created_at" "")
                    "history" jsonloadsrow["history"]) if rowget"history") else []
                    "is_paid" rowget"is_paid" False)
                    "predictions_limit" rowget"predictions_limit" -1)
                    "total_usage" rowget"total_usage" 0)
                    "badges" jsonloadsrow["badges"]) if rowget"badges") else []
                    "exp" rowget"exp" 0)
                    "plan" rowget"plan")
                    "paid_date" rowget"paid_date")
                    "expiry_date" rowget"expiry_date")
                    "terms_agreed" rowget"terms_agreed")
                    "bets" jsonloadsrow["bets"]) if rowget"bets") else []
                }
            
            # 如果 Supabase 冇 admin就建立一個
            if "admin" not in result
                result["admin"] = {
                    "username" "admin"
                    "password" "z54060437K"
                    "group" "super_admin"
                    "is_paid" True
                    "predictions_limit" -1
                    "free_usage" 0
                    "total_usage" 0
                    "created_at" datetimenow)strftime'%Y-%m-%d %H%M%S')
                    "history" [] "badges" [] "level" "👑 超級管理員" "exp" 0
                    "virtual_balance" 10000 "last_claim_date" "" "last_lottery_date" ""
                    "invite_code" "ADMIN001" "invite_count" 0 "invite_rewards" 0
                    "phone" "" "note" "系統超級管理員" "plan" None "paid_date" None
                    "expiry_date" None "terms_agreed" datetimenow)isoformat) "bets" []
                }
                save_usersresult)
            else
                # 補齊缺失欄位保留原本邏輯)
                for uid u in resultitems)
                    defaults = {
                        'plan' None 'paid_date' None 'expiry_date' None
                        'phone' '' 'note' '' 'history' [] 'free_usage' 0
                        'total_usage' 0 'terms_agreed' None 'invited_by' None
                        'invite_rewards' 0 'invite_count' 0
                        'level' '🥉 銅牌會員' 'exp' 0 'badges' []
                        'virtual_balance' 1000 'last_claim_date' ''
                        'bets' [] 'last_lottery_date' ''
                    }
                    for k v in defaultsitems)
                        if k not in u
                            u[k] = v
                    if 'invite_code' not in u or not u['invite_code']
                        u['invite_code'] = uidupper) + strrandomrandint100 999))
                    if 'predictions_limit' not in u
                        if uget'group') in ['super_admin' 'VIP' 'paid']
                            u['predictions_limit'] = -1
                        else
                            u['predictions_limit'] = 2
                save_usersresult)
            return result
        else
            return {}
    except Exception as e
        return {}

def save_usersusers)
    """將所有用戶儲存到 Supabase"""
    headers = {
        "apikey" SUPABASE_KEY
        "Authorization" f"Bearer {SUPABASE_KEY}"
        "Content-Type" "application/json"
        "Prefer" "resolution=merge-duplicates"
    }
    for username data in usersitems)
        payload = {
            "username" username
            "password" dataget"password" "")
            "phone" dataget"phone" "")
            "invite_code" dataget"invite_code" "")
            "invited_by" dataget"invited_by" "")
            "referred_users" jsondumpsdataget"referred_users" []) ensure_ascii=False)
            "invite_count" dataget"invite_count" 0)
            "invite_rewards" dataget"invite_rewards" 0)
            "user_group" dataget"group" "free")
            "level" dataget"level" "🥉 銅牌會員")
            "virtual_balance" dataget"virtual_balance" 0)
            "lottery_chances" dataget"lottery_chances" 0)
            "last_lottery_reset" dataget"last_lottery_reset" "")
            "created_at" dataget"created_at" "")
            "history" jsondumpsdataget"history" []) ensure_ascii=False)
            "is_paid" dataget"is_paid" False)
            "predictions_limit" dataget"predictions_limit" -1)
            "total_usage" dataget"total_usage" 0)
            "badges" jsondumpsdataget"badges" []) ensure_ascii=False)
            "exp" dataget"exp" 0)
            "plan" dataget"plan")
            "paid_date" dataget"paid_date")
            "expiry_date" dataget"expiry_date")
            "terms_agreed" dataget"terms_agreed")
            "bets" jsondumpsdataget"bets" []) ensure_ascii=False)
        }
        try
            res = requestspostf"{SUPABASE_URL}/rest/v1/users" headers=headers json=payload)
            if resstatus_code not in [200 201 204]
                sterrorf"❌ 寫入失敗{restext}")
        except Exception as e
            sterrorf"❌ 寫入錯誤{e}")
    return users

def save_usersusers)
    """將所有用戶儲存到 Supabase"""
    headers = {
        "apikey" SUPABASE_KEY
        "Authorization" f"Bearer {SUPABASE_KEY}"
        "Content-Type" "application/json"
        "Prefer" "resolution=merge-duplicates"
    }
    for username data in usersitems)
        payload = {
            "username" username
            "password" dataget"password" "")
            "phone" dataget"phone" "")
            "invite_code" dataget"invite_code" "")
            "invited_by" dataget"invited_by" "")
            "referred_users" jsondumpsdataget"referred_users" []) ensure_ascii=False)
            "invite_count" dataget"invite_count" 0)
            "invite_rewards" dataget"invite_rewards" 0)
            "user_group" dataget"group" "free")
            "level" dataget"level" "🥉 銅牌會員")
            "virtual_balance" dataget"virtual_balance" 0)
            "lottery_chances" dataget"lottery_chances" 0)
            "last_lottery_reset" dataget"last_lottery_reset" "")
            "created_at" dataget"created_at" "")
            "history" jsondumpsdataget"history" []) ensure_ascii=False)
        }
        try
            res = requestspostf"{SUPABASE_URL}/rest/v1/users" headers=headers json=payload)
            if resstatus_code not in [200 201 204]
                sterrorf"❌ 寫入失敗{restext}")
        except Exception as e
            sterrorf"❌ 寫入錯誤{e}")
    
    return True

def authenticateusername password)
    users = load_users)
    if username in users and users[username]get'password') == password
        return users[username]
    return None

def log_admin_actionadmin action)
    logs = load_jsonLOG_FILE)
    if 'logs' not in logs
        logs['logs'] = []
    logs['logs']append{
        'time' datetimenow)strftime'%Y-%m-%d %H%M%S')
        'admin' admin
        'action' action
    })
    save_jsonLOG_FILE logs)
def log_user_activityusername action detail="")
    """記錄用戶活動"""
    log_file = "user_activity_logjson"
    try
        if ospathexistslog_file)
            with openlog_file 'r' encoding='utf-8') as f
                logs = jsonloadf)
        else
            logs = {"records" []}
    except Exception
        logs = {"records" []}

    if "records" not in logs
        logs["records"] = []

    logs["records"]append{
        "time" datetimenow)strftime'%Y-%m-%d %H%M%S')
        "username" username
        "action" action
        "detail" detail
    })

    # 只保留最近 5000 條
    logs["records"] = logs["records"][-5000]

    try
        with openlog_file 'w' encoding='utf-8') as f
            jsondumplogs f ensure_ascii=False indent=2)
    except Exception
        pass

def load_finance)
    return load_jsonFINANCE_FILE)

def save_financef)
    return save_jsonFINANCE_FILE f)

def load_promos)
    return load_jsonPROMO_FILE)

def save_promosp)
    return save_jsonPROMO_FILE p)

def load_accuracy)
    return load_jsonACCURACY_FILE)

def save_accuracya)
    return save_jsonACCURACY_FILE a)

def load_payment_proofs)
    return load_jsonPAYMENT_PROOFS_FILE)

def save_payment_proofsd)
    return save_jsonPAYMENT_PROOFS_FILE d)

def load_lottery_config)
    default_config = {
        "prizes" [
            {"name" "100 虛擬幣" "type" "virtual_coin" "value" 100 "weight" 5 "description" "送 100 虛擬幣"}
            {"name" "500 虛擬幣" "type" "virtual_coin" "value" 500 "weight" 2 "description" "送 500 虛擬幣"}
            {"name" "1000 虛擬幣" "type" "virtual_coin" "value" 1000 "weight" 1 "description" "送 1000 虛擬幣"}
            {"name" "VIP 1 天" "type" "vip_days" "value" 1 "weight" 10 "description" "1 天 VIP 體驗"}
            {"name" "免費預測 3 次" "type" "free_predictions" "value" 3 "weight" 20 "description" "額外 3 次預測"}
            {"name" "20% 折扣優惠碼" "type" "promo_code" "value" 20 "weight" 10 "description" "購物 8 折"}
            {"name" "謝謝參與" "type" "nothing" "value" 0 "weight" 30 "description" "下次再嚟"}
        ]
    }
    
    if ospathexists"lottery_configjson")
        try
            with open"lottery_configjson" "r" encoding='utf-8') as f
                config = jsonloadf)
            if configget"prizes")
                return config
        except Exception
            pass
            
    # 如果檔案唔存在、讀取失敗或者係空嘅就寫入預設值
    with open"lottery_configjson" "w" encoding='utf-8') as f
        jsondumpdefault_config f ensure_ascii=False indent=2)
    return default_config
    return save_jsonLOTTERY_FILE c)

def load_shop_config)
    default_config = {
        "items" [
            {"name" "額外 5 次預測" "type" "predictions" "price" 500 "stock" 100 "description" "增加 5 次預測機會"}
            {"name" "VIP 7 天體驗" "type" "vip_days" "price" 3000 "stock" 50 "description" "7 天 VIP 權限"}
            {"name" "神秘盲盒" "type" "mystery_box" "price" 1000 "stock" 20 "description" "隨機獲得獎品"}
        ]
    }
    
    if ospathexists"shop_configjson")
        try
            with open"shop_configjson" "r" encoding='utf-8') as f
                config = jsonloadf)
            if configget"items")
                return config
        except Exception
            pass
            
    # 如果檔案唔存在、讀取失敗或者係空嘅就寫入預設值
    with open"shop_configjson" "w" encoding='utf-8') as f
        jsondumpdefault_config f ensure_ascii=False indent=2)
    return default_config

def save_shop_configc)
    return save_jsonSHOP_FILE c)

def generate_promo_code)
    return ''joinrandomchoices'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' k=8))

def get_plan_daysplan)
    return {'day' 1 'month' 30 'quarter' 90}getplan 0)

def get_plan_nameplan)
    return {'day' '日費' 'month' '月費' 'quarter' '季費'}getplan '未知')

def get_plan_priceplan)
    return {'day' CONFIG['price_day'] 'month' CONFIG['price_month'] 'quarter' CONFIG['price_quarter']}getplan 0)

def _safe_intv default=0)
    try
        return intfloatv))
    except Exception
        return default

def submit_payment_requestusername plan final_price discount_desc promo_code_used)
    proof = load_payment_proofs)
    if 'proof_records' not in proof
        proof['proof_records'] = []
    new_id = lenproof['proof_records']) + 1
    proof['proof_records']append{
        "id" new_id "username" username "plan" plan
        "plan_name" get_plan_nameplan) "final_price" final_price
        "discount_desc" discount_desc "promo_code" promo_code_used
        "submitted_at" datetimenow)isoformat) "status" "pending"
    })
    save_payment_proofsproof)
    return True "申請已提交"

def get_all_pending_requests)
    proof = load_payment_proofs)
    return [
        {"username" rget'username' '') "request" r}
        for r in proofget'proof_records' [])
        if rget'status') == 'pending'
    ]

def approve_payment_requestusername request_id admin_username)
    proof = load_payment_proofs)
    for req in proofget'proof_records' [])
        if reqget'id') == request_id and reqget'status') == 'pending'
            users = load_users)
            if username in users
                plan = reqget'plan' 'month')
                days = get_plan_daysplan) or 30
                expiry = datetimenow) + timedeltadays=days))strftime'%Y-%m-%d %H%M%S')
                users[username]['is_paid'] = True
                users[username]['group'] = 'VIP'
                users[username]['paid_date'] = datetimenow)strftime'%Y-%m-%d %H%M%S')
                users[username]['expiry_date'] = expiry
                users[username]['plan'] = plan
                users[username]['predictions_limit'] = -1
                save_usersusers)
                req['status'] = 'approved'
                req['approved_by'] = admin_username
                req['approved_at'] = datetimenow)isoformat)
                save_payment_proofsproof)
                return True f"已批准 {username}到期日 {expiry}"
            return False "用戶不存在"
    return False "找不到該申請"

def reject_payment_requestusername request_id admin_username)
    proof = load_payment_proofs)
    for req in proofget'proof_records' [])
        if reqget'id') == request_id and reqget'status') == 'pending'
            req['status'] = 'rejected'
            req['rejected_by'] = admin_username
            req['rejected_at'] = datetimenow)isoformat)
            save_payment_proofsproof)
            return True "已拒絕該申請"
    return False "找不到該申請"

def generate_pool_recommendationsdf user_group='free')
    if dfempty
        return "⚠️ 無數據"

    config = load_system_config)
    pool_config = configget'pool_config' {})

    if not pool_config
        pool_config = {
            "win" {"enabled" True "required_group" "free" "label" "獨贏"}
            "place" {"enabled" True "required_group" "free" "label" "位置"}
            "quinella" {"enabled" True "required_group" "free" "label" "連贏"}
            "quinella_place" {"enabled" True "required_group" "free" "label" "位置Q"}
            "tierce" {"enabled" True "required_group" "paid" "label" "三重彩"}
            "trio" {"enabled" True "required_group" "paid" "label" "單T"}
            "quartet" {"enabled" True "required_group" "VIP" "label" "四重彩"}
            "exacta" {"enabled" True "required_group" "VIP" "label" "二重彩"}
            "first4" {"enabled" True "required_group" "VIP" "label" "四連環"}
            "double" {"enabled" True "required_group" "VIP" "label" "孖寶"}
            "treble" {"enabled" True "required_group" "VIP" "label" "三寶"}
            "six_up" {"enabled" True "required_group" "VIP" "label" "六環彩"}
        }

    group_levels = {'free' 0 'paid' 1 'VIP' 2 'super_admin' 99}
    user_level = group_levelsgetuser_group 0)

    df_sorted = dfsort_values'預測勝率' ascending=False)reset_indexdrop=True)
    names = df_sorted['馬名']tolist)
    probs = df_sorted['預測勝率']tolist)

    def get_win)
        if lennames) >= 1
            return f"  {names[0]}{probs[0]1%})"
        return ""

    def get_place)
        if lennames) >= 2
            return f"  {names[0]}{probs[0]1%})+ {names[1]}{probs[1]1%})"
        elif lennames) >= 1
            return f"  {names[0]}{probs[0]1%})"
        return ""

    def get_quinella)
        if lennames) >= 2
            return f"  {names[0]} + {names[1]}"
        return ""

    def get_quinella_place)
        if lennames) >= 2
            return f"  {names[0]} + {names[1]}"
        return ""

    def get_tierce)
        if lennames) >= 3
            return f"  {names[0]} > {names[1]} > {names[2]}"
        return ""

    def get_trio)
        if lennames) >= 3
            return f"  {names[0]} + {names[1]} + {names[2]}"
        return ""

    def get_quartet)
        if lennames) >= 4
            return f"  {names[0]} > {names[1]} > {names[2]} > {names[3]}"
        return ""

    def get_exacta)
        if lennames) >= 2
            return f"  {names[0]} > {names[1]}"
        return ""

    def get_first4)
        if lennames) >= 4
            return f"  {names[0]} + {names[1]} + {names[2]} + {names[3]}"
        return ""

    def get_double)
        return "  ⚠️ 需要 2 場賽事數據孖寶)"

    def get_treble)
        return "  ⚠️ 需要 3 場賽事數據三寶)"

    def get_six_up)
        return "  ⚠️ 需要 6 場賽事數據六環彩)"

    generators = {
        'win' get_win 'place' get_place 'quinella' get_quinella
        'quinella_place' get_quinella_place 'tierce' get_tierce
        'trio' get_trio 'quartet' get_quartet 'exacta' get_exacta
        'first4' get_first4 'double' get_double 'treble' get_treble
        'six_up' get_six_up
    }

    rec_lines = []
    for key cfg in pool_configitems)
        if not cfgget'enabled' True)
            continue
        required = cfgget'required_group' 'free')
        if user_level < group_levelsgetrequired 0)
            rec_linesappendf"【{cfgget'label' key)}】🔒 需要更高級會員")
            continue
        gen = generatorsgetkey)
        if gen
            content = gen)
            if content
                rec_linesappendf"【{cfgget'label' key)}】\n{content}")

    if not rec_lines
        return "⚠️ 所有彩池已關閉或未開放"
    return "\n\n"joinrec_lines)

    return "\n\n"joinrec_lines)
    for _ i j k l in qt[3]
        rec += f"  {names[i]} > {names[j]} > {names[k]} > {names[l]}\n"

    return rec

@stcache_resource
def load_ml_models)
    """載入 XGBoost + CatBoost + Ranking 模型"""
    import pickle
    xgb_model = None
    cat_model = None
    rank_model = None

    try
        with open'hk_racing_modelpkl' 'rb') as f
            obj = pickleloadf)
            xgb_model = obj[0] if isinstanceobj tuple) else obj
    except Exception as e
        printf"XGBoost 載入失敗{e}")

    try
        from catboost import CatBoostClassifier
        cat_model = CatBoostClassifier)
        cat_modelload_model'hk_catboost_modelcbm')
    except Exception as e
        printf"CatBoost 載入失敗{e}")

    try
        with open'hk_ranking_modelpkl' 'rb') as f
            obj = pickleloadf)
            rank_model = obj[0] if isinstanceobj tuple) else obj
    except Exception as e
        printf"Ranking 載入失敗{e}")

    return xgb_model cat_model rank_model


def _repair_racecarddf)
    """自動修復混合格式嘅 racecard CSV"""
    # 讀取原始檔案唔用 header)
    df_raw = pdread_csv"racecard_uploadedcsv" encoding='utf-8-sig' header=None dtype=str)

    std_cols = ['horse_id' 'horse_name' 'draw' 'weight' 'jockey'
                'trainer' 'race_no' 'race_date' 'win_odds']

    # 中文格式欄位順序馬號馬名檔位負磅騎師練馬師場次比賽日期賠率
    cn_cols = ['horse_id' 'horse_name' 'draw' 'weight' 'jockey'
               'trainer' 'race_no' 'race_date' 'win_odds']

    # 英文格式欄位順序race_daterace_nohorse_nohorse_namedrawweightjockeytrainerwin_odds
    en_cols = ['race_date' 'race_no' 'horse_id' 'horse_name'
               'draw' 'weight' 'jockey' 'trainer' 'win_odds']

    parts = []

    for _ row in df_rawiterrows)
        first_val = strrow[0])strip)

        # 跳過 header 行
        if first_vallower) in ['馬號' 'race_date' 'nan' '']
            continue

        # 中文格式第一列係純數字馬號)
        if first_valisdigit)
            row_df = pdDataFrame[rowvalues] columns=cn_cols)
            partsappendrow_df)

        # 英文格式第一列係日期YYYY-MM-DD)
        elif lenfirst_val) == 10 and first_val[4] == '-' and first_val[7] == '-'
            row_df = pdDataFrame[rowvalues] columns=en_cols)
            partsappendrow_df)

    if not parts
        return pdDataFramecolumns=std_cols)

    result = pdconcatparts ignore_index=True)
    result = result[std_cols]
    return result


def _build_featuresrace_df history_df)
    # 為排位表每匹馬計算特徵
    import numpy as np
    import os

    history_df = history_dfcopy)
    history_df['race_date'] = pdto_datetimehistory_df['race_date'] errors='coerce')
    history_df = history_dfdropnasubset=['race_date'])
    history_df['finish_position'] = pdto_numerichistory_df['finish_position'] errors='coerce')
    history_df = history_dfdropnasubset=['finish_position'])

    result = race_dfcopy)

    # ========================================================
    # 🛡️ 終極修復用「馬名」將排位表嘅馬號對照成真實馬匹編號
    # ========================================================
    if 'horse_name' in resultcolumns and 'horse_name' in history_dfcolumns and 'horse_id' in history_dfcolumns
        # 清理空格
        history_df['horse_name'] = history_df['horse_name']astypestr)strstrip)
        history_df['horse_id'] = history_df['horse_id']astypestr)strstrip)
        result['horse_name'] = result['horse_name']astypestr)strstrip)
        
        # 建立「馬名 -> 真實馬匹編號」對照表
        name_to_id_map = history_dfdrop_duplicates'horse_name')set_index'horse_name')['horse_id']to_dict)
        
        # 將 result 入面嘅 horse_id1-14號)替換成真實編號例如 H196)
        result['horse_id'] = result['horse_name']mapname_to_id_map)fillnaresult['horse_id'])astypestr)strstrip)
    # ========================================================

    # 初始化所有特徵
    feature_cols = [
        'draw' 'weight' 'distance' 'Rtg' 'avg_rank_last3'
        'jockey_win_rate_50' 'trainer_win_rate_50'
        'distance_win_rate' 'distance_avg_rank'
        'win_odds' 'weight_change' 'jockey_trainer_win_rate'
        'course_win_rate' 'course_avg_rank'
        'days_since_last_run' 'odds_rank_in_race'
        'rtg_change' 'jockey_horse_win_rate'
        'races_last14days' 'going_win_rate'
        'trial_win_rate' 'sire_win_rate' 'sire_course_win_rate'
        'early_pace' 'finish_speed'
        'last_trial_rank' 'last_trial_time'
        'jockey_win_rate_5' 'jockey_win_rate_10' 'draw_win_rate'
        'days_since_injury' 'injury_30d' 'injury_60d' 'injury_90d'
        'total_injuries' 'injury_severity'
    ]
    for c in feature_cols
        if c not in resultcolumns
            result[c] = 00

    # 填充基本欄位
    if 'draw' in race_dfcolumns
        result['draw'] = pdto_numericrace_df['draw'] errors='coerce')fillna0)
    if 'weight' in race_dfcolumns
        result['weight'] = pdto_numericrace_df['weight'] errors='coerce')fillna0)
    if 'distance' in race_dfcolumns
        result['distance'] = pdto_numericrace_df['distance'] errors='coerce')fillna0)
    if 'rtg' in race_dfcolumns
        result['Rtg'] = pdto_numericrace_df['rtg'] errors='coerce')fillna0)
    if 'win_odds' in race_dfcolumns
        result['win_odds'] = pdto_numericrace_df['win_odds'] errors='coerce')fillna0)

    # 賠率排名
    if 'win_odds' in resultcolumns
        result['odds_rank_in_race'] = result['win_odds']rankmethod='min' ascending=True)fillna0)

    # 歷史統計
    if not history_dfempty
        # 騎師勝率
        if 'jockey' in history_dfcolumns and 'jockey' in resultcolumns
            jockey_stats = history_dfgroupby'jockey')apply
                lambda g g['finish_position'] == 1)sum) / maxleng) 1)
            to_dict)
            result['jockey_win_rate_50'] = result['jockey']mapjockey_stats)fillna0)

        # 練馬師勝率
        if 'trainer' in history_dfcolumns and 'trainer' in resultcolumns
            trainer_stats = history_dfgroupby'trainer')apply
                lambda g g['finish_position'] == 1)sum) / maxleng) 1)
            to_dict)
            result['trainer_win_rate_50'] = result['trainer']maptrainer_stats)fillna0)

        # 馬匹近3場平均名次
        if 'horse_id' in history_dfcolumns and 'horse_id' in resultcolumns
            def _avg3g)
                g = gsort_values'race_date')tail3)
                return g['finish_position']mean) if leng) > 0 else 99
            avg3 = history_dfgroupby'horse_id')apply_avg3)to_dict)
            result['avg_rank_last3'] = result['horse_id']mapavg3)fillna99)

            # 馬匹同路程勝率
            if 'distance' in history_dfcolumns and 'distance' in resultcolumns
                def _dist_winrow)
                    sub = history_df[history_df['horse_id'] == row['horse_id']) &
                                     history_df['distance'] == row['distance'])]
                    return 0 if lensub) == 0 else sub['finish_position'] == 1)sum) / lensub)
                result['distance_win_rate'] = resultapply_dist_win axis=1)

            # 騎練組合勝率
            if 'jockey' in history_dfcolumns and 'trainer' in history_dfcolumns
                def _jt_winrow)
                    sub = history_df[history_df['jockey'] == row['jockey']) &
                                     history_df['trainer'] == row['trainer'])]
                    return 0 if lensub) == 0 else sub['finish_position'] == 1)sum) / lensub)
                result['jockey_trainer_win_rate'] = resultapply_jt_win axis=1)

            # 出賽相隔日數
            last_run = history_dfgroupby'horse_id')['race_date']max)to_dict)
            result['days_since_last_run'] = result['horse_id']map
                lambda h datetimenow) - last_run[h])days if h in last_run else 999
            fillna999)

    # 填充剩餘特徵
    for c in feature_cols
        result[c] = pdto_numericresult[c] errors='coerce')fillna0)

    return result

def run_predictiondate_str race_no)
    # 用真正 ML 模型預測（統一 36 特徵版）
    if not ospathexists"racecard_uploadedcsv")
        sterror"❌ 找不到 racecard_uploadedcsv")
        return None None

    try
        race_df = pdread_csv"racecard_uploadedcsv" encoding='utf-8-sig')
        race_df = _repair_racecardrace_df)
    except Exception as e
        sterrorf"❌ 讀取失敗{e}")
        return None None

    rename_map = {
        '馬名' 'horse_name' '檔位' 'draw' '場次' 'race_no'
        '比賽日期' 'race_date' '騎師' 'jockey' '練馬師' 'trainer'
        '負磅' 'weight' '馬號' 'horse_id' '賠率' 'win_odds'
        '路程' 'distance' '評分' 'rtg'
    }
    existing = [c for c in rename_map if c in race_dfcolumns]
    if existing
        race_dfrenamecolumns={c rename_map[c] for c in existing} inplace=True)

    if 'race_date' not in race_dfcolumns
        sterror"❌ 缺少 '比賽日期'")
        return None None

    race_df['race_date'] = pdto_datetimerace_df['race_date'] errors='coerce')
    race_df = race_dfdropnasubset=['race_date'])
    race_df['race_date_str'] = race_df['race_date']dtstrftime'%Y-%m-%d')
    race_df['race_no'] = pdto_numericrace_df['race_no'] errors='coerce')fillna0)astypeint)

    available_dates = sortedrace_df['race_date_str']unique))
    if not available_dates
        sterror"❌ 無可用日期")
        return None None

    if date_str not in available_dates
        stwarningf"⚠️ {date_str} 冇數據自動改用 {available_dates[-1]}")
        date_str = available_dates[-1]

    try
        race_no = intrace_no)
    except Exception
        race_no = 1

    df_date = race_df[race_df['race_date_str'] == date_str]
    if 'race_no' not in df_datecolumns
        sterror"❌ 缺少 '場次'")
        return None None

    avail_races = sorteddf_date['race_no']unique))
    if race_no not in avail_races
        stwarningf"⚠️ {date_str} 冇第 {race_no} 場改用第 {avail_races[0]} 場")
        race_no = avail_races[0]

    filtered = df_date[df_date['race_no'] == race_no]copy)reset_indexdrop=True)
    if filteredempty
        sterrorf"❌ {date_str} 第 {race_no} 場冇馬匹數據")
        return None None

    stsuccessf"✅ 成功載入 {date_str} 第 {race_no} 場共 {lenfiltered)} 匹馬")

    history_df = pdDataFrame)
    if ospathexists"ALL_DATA_MERGEDcsv")
        try
            history_df = pdread_csv"ALL_DATA_MERGEDcsv" encoding='utf-8-sig' low_memory=False)
            history_dfcolumns = [strc)replace'\ufeff' '')strip) for c in history_dfcolumns]
            if 'finish_position' not in history_dfcolumns and 'Pla' in history_dfcolumns
                history_df['finish_position'] = history_df['Pla']
        except Exception as e
            stwarningf"⚠️ 讀取歷史數據失敗{e}")

    with stspinner"🔧 計算特徵中")
        features_df = _build_featuresfiltered history_df)

    xgb_model cat_model rank_model = load_ml_models)

    features_36 = ['draw' 'weight' 'distance' 'Rtg' 'avg_rank_last3'
                   'jockey_win_rate_50' 'trainer_win_rate_50'
                   'distance_win_rate' 'distance_avg_rank' 'win_odds'
                   'weight_change' 'jockey_trainer_win_rate'
                   'course_win_rate' 'course_avg_rank'
                   'days_since_last_run' 'odds_rank_in_race'
                   'rtg_change' 'jockey_horse_win_rate'
                   'races_last14days' 'going_win_rate'
                   'trial_win_rate' 'sire_win_rate' 'sire_course_win_rate'
                   'early_pace' 'finish_speed' 'last_trial_rank'
                   'last_trial_time' 'jockey_win_rate_5' 'jockey_win_rate_10'
                   'draw_win_rate' 'days_since_injury' 'injury_30d'
                   'injury_60d' 'injury_90d' 'total_injuries' 'injury_severity']

    pred_xgb = None
    pred_cat = None
    pred_rank = None
    models_used = []

    # ===== XGBoost強制用 36 特徵)=====
    if xgb_model is not None
        try
            X_xgb = features_df[features_36]fillna0)values
            pred_xgb = xgb_modelpredict_probaX_xgb)[ 1]
            models_usedappend"XGBoost36特徵)")
        except Exception as e
            stwarningf"⚠️ XGBoost 失敗{e}")

    # ===== CatBoost強制用 36 特徵)=====
    if cat_model is not None
        try
            X_cat = features_df[features_36]fillna0)values
            pred_cat = cat_modelpredict_probaX_cat)[ 1]
            models_usedappend"CatBoost36特徵)")
        except Exception as e
            stwarningf"⚠️ CatBoost 失敗{e}")

    # ===== Ranking強制用 36 特徵)=====
    if rank_model is not None
        try
            X_rank = features_df[features_36]fillna0)values
            pred_rank = rank_modelpredictX_rank)
            pred_rank = nparraypred_rank dtype=float)
            if pred_rankmax) > pred_rankmin)
                pred_rank = pred_rank - pred_rankmin)) / pred_rankmax) - pred_rankmin))
            models_usedappend"Ranking36特徵)")
        except Exception as e
            stwarningf"⚠️ Ranking 失敗{e}")

    # ===== 融合優先從 system_config 讀取權重)=====
    all_preds = [p for p in [pred_xgb pred_cat pred_rank] if p is not None]
    if all_preds
        import json
        try
            with open"system_configjson" "r" encoding="utf-8") as f
                sys_config = jsonloadf)
            w_xgb = sys_configget"xgb_weight" 03)
            w_cat = sys_configget"cat_weight" 05)
            w_rank = 02 # 默認 Rank 權重
            # 如果 system_config 寫 25/1就自動轉換為比例
            if w_xgb > 1 or w_cat > 1
                total = w_xgb + w_cat + w_rank
                w_xgb = w_xgb / total
                w_cat = w_cat / total
                w_rank = w_rank / total
        except Exception
            w_xgb w_cat w_rank = 03 05 02

        weights = []
        if pred_xgb is not None weightsappendw_xgb)
        if pred_cat is not None weightsappendw_cat)
        if pred_rank is not None weightsappendw_rank)

        weights = nparrayweights) / sumweights)

        pred_proba = npzeroslenfiltered))
        for i p in enumerateall_preds)
            pred_proba += weights[i] * p

        stsuccessf"✅ 使用模型{' 'joinmodels_used)}權重XGB {weights[0]2f} / Cat {weights[1]2f})")
    else
        stwarning"⚠️ 冇可用模型改用賠率估算")
        win_odds = pdto_numericfilteredget'win_odds' 40) errors='coerce')fillna40)replace0 40)
        inv = 1 / win_odds
        pred_proba = inv / invsum))values

    pred_proba = pred_proba / pred_probasum)

    # 提取馬號
    id_col = None
    for col in ['horse_id' '馬號' 'horse_no']
        if col in filteredcolumns
            id_col = col
            break

    if id_col
        result_df = filtered[[id_col 'horse_name']]copy)
        result_df = result_dfrenamecolumns={id_col '馬號'})
    else
        result_df = filtered[['horse_name']]copy)
        result_dfinsert0 '馬號' range1 lenresult_df) + 1))

    for c in ['draw' 'weight' 'jockey' 'trainer']
        if c in filteredcolumns
            result_df[c] = filtered[c]

    result_df = result_dfrenamecolumns={
        'horse_name' '馬名' 'draw' '檔位' 'weight' '負磅'
        'jockey' '騎師' 'trainer' '練馬師'
    })
    result_df['預測勝率'] = pred_proba
    result_df['值博指數'] = result_df['預測勝率'] * 10
    result_df['信心指數'] = result_df['預測勝率']apply
        lambda x '⭐⭐⭐ 高' if x > 02 else '⭐⭐ 中' if x > 01 else '⭐ 低'
    
    result_df = result_dfsort_values'預測勝率' ascending=False)reset_indexdrop=True)

    # 儲存
    # 儲存到 SQLite
    # 儲存到 Supabase
    from database import save_prediction
    key = f"{date_str}_{race_no}"
    save_predictionkey {
        "date" date_str "race" race_no
        "top_horse" result_dfiloc[0]['馬名']
        "top_prob" floatresult_dfiloc[0]['預測勝率'])
        "all_horses" result_df['馬名']tolist)
        "model_used" models_used
        "predicted_at" datetimenow)isoformat)
    })

    user_group = stsession_stateget'role' 'free')
    return result_df generate_pool_recommendationsresult_df user_group)

def _find_data_coldf keywords)
    # 搵一個有數據嘅欄位（唔止名要對，仲要有實際值）
    for c in dfcolumns
        cl = strc)lower)strip)
        if anyklower) in cl for k in keywords)
            # 檢查呢個欄位係咪真係有數據
            non_empty = df[c]dropna)astypestr)strstrip)
            non_empty = non_empty[~non_emptyisin['' 'nan' 'None' '-' 'NaN'])]
            if lennon_empty) > 10  # 至少要 10 條有數據先算
                return c
    return None


def _find_pos_coldf)
    """搵名次欄位"""
    for c in dfcolumns
        cl = strc)lower)strip)
        if cl in ['pla' 'plc' '名次' 'finish_position' 'finishing_position'
                  'pos' 'position' 'rank' 'place' 'finish']
            non_empty = df[c]dropna)astypestr)strstrip)
            non_empty = non_empty[~non_emptyisin['' 'nan' 'None' '-'])]
            if lennon_empty) > 10
                return c
    # 模糊搜尋
    for c in dfcolumns
        cl = strc)lower)
        if 'pla' in cl or '名次' in cl or 'finish' in cl
            non_empty = df[c]dropna)astypestr)strstrip)
            non_empty = non_empty[~non_emptyisin['' 'nan' 'None' '-'])]
            if lennon_empty) > 10
                return c
    return None


def _rank_from_csvcol_keywords)
    """無敵版自動搵出有數據嘅欄位"""
    # 讀取 CSV
    df = None
    for fp in ["ALL_DATA_MERGEDcsv" "HKCJ_FULL_YEAR_DATAcsv"]
        if not ospathexistsfp)
            continue
        for enc in ['utf-8-sig' 'utf-8' 'big5' 'gbk']
            try
                df = pdread_csvfp encoding=enc low_memory=False)
                stcaptionf"📁 讀取{fp}{lendf)} 行)")
                break
            except Exception
                continue
        if df is not None
            break

    if df is None
        sterror"❌ 搵唔到 ALL_DATA_MERGEDcsv 或 HKCJ_FULL_YEAR_DATAcsv")
        return None

    dfcolumns = [strc)replace'\ufeff' '')strip) for c in dfcolumns]
    df = dfloc[ ~dfcolumnsduplicated)]

    pos_col = _find_pos_coldf)
    target_col = _find_data_coldf col_keywords)

    if not pos_col or not target_col
        sterrorf"❌ 搵唔到有數據嘅欄位名次 `{pos_col}`目標 `{target_col}`")
        with stexpander"🔍 診斷所有欄位 + 非空數量" expanded=True)
            info = []
            for c in dfcolumns
                non_empty = df[c]dropna)astypestr)strstrip)
                non_empty = non_empty[~non_emptyisin['' 'nan' 'None' '-'])]
                infoappend{'欄位' c '非空數量' lennon_empty)})
            stdataframepdDataFrameinfo) use_container_width=True)
        return None

    # 提取數據
    ts = df[target_col]
    if isinstancets pdDataFrame)
        ts = tsiloc[ 0]
    ps = df[pos_col]
    if isinstanceps pdDataFrame)
        ps = psiloc[ 0]

    # 轉名次做數字
    pos_str = psastypestr)strstrip)
    pos_num = pdto_numericpos_str errors='coerce')
    if pos_numnotna)sum) == 0
        pos_num = pdto_numericpos_strstrextractr'\d+)')[0] errors='coerce')
    if pos_numnotna)sum) == 0
        def _px)
            x = strx)strip)lower)
            for s in ['st' 'nd' 'rd' 'th']
                x = xreplaces '')
            try
                return floatxstrip))
            except Exception
                return None
        pos_num = pos_strapply_p)

    temp = pdDataFrame{'name' tsastypestr)strstrip) 'finish_position' pos_num})
    temp = tempdropnasubset=['finish_position'])
    temp = temp[~temp['name']strlower)isin['nan' 'none' '' '-' '未知'])]

    if tempempty
        stwarning"⚠️ 過濾後數據為空")
        with stexpander"🔍 診斷點擊展開)" expanded=True)
            stwritef"**使用欄位**名次=`{pos_col}`目標=`{target_col}`")
            stwritef"**名次樣本**{pshead10)tolist)}")
            stwritef"**目標樣本**{tshead10)tolist)}")
            stwritef"**名次轉換後有效**{pos_numnotna)sum)} / {lenpos_num)}")
        return None

    total = tempgroupby'name')size)reset_indexname='總出賽')
    wins = temp[temp['finish_position'] == 1]groupby'name')size)reset_indexname='勝出')
    stats = pdmergetotal wins on='name' how='left')fillna{'勝出' 0})
    stats['勝出'] = stats['勝出']astypeint)
    stats['勝率'] = stats['勝出'] / stats['總出賽'])applylambda x f"{x1%}")
    return statssort_values'勝出' ascending=False)


def _get_pos_seriesdf)
    """自动选择名次欄位优先 Pla如果冇就用 finish_position"""
    # 試 Pla用位置索引避免隱藏字元)
    pla_idx = None
    for i c in enumeratedfcolumns)
        if strc)strip)lower) == 'pla'
            pla_idx = i
            break
    if pla_idx is None
        pla_idx = 2  # 預設第 3 列

    pos = pdto_numericdfiloc[ pla_idx] errors='coerce')
    if posnotna)sum) >= 100
        return pos f'Pla 第 {pla_idx} 列)'

    # 如果 Pla 唔得試 finish_position
    if 'finish_position' in dfcolumns
        pos = pdto_numericdf['finish_position'] errors='coerce')
        if posnotna)sum) >= 100
            return pos 'finish_position'

    return pos '未知'

def admin_horse_ranking)
    stsubheader"🏇 馬匹勝率排行榜")

    import os
    import pandas as pd

    result_file = "race_results_cleancsv"
    if not ospathexistsresult_file)
        stwarning"⚠️ 找不到 race_results_cleancsv")
        return

    try
        df = pdread_csvresult_file encoding='utf-8-sig')
        dfcolumns = [strc)replace'\ufeff' '')strip) for c in dfcolumns]
    except Exception as e
        sterrorf"❌ 讀取失敗{e}")
        return

    # 🛡️ 智能偵測欄位名支援中英文)
    name_col = None
    for c in ['horse_name' '馬名' '馬匹名稱' 'Name']
        if c in dfcolumns
            name_col = c
            break

    pos_col = None
    for c in ['finish_position' 'Pla' '名次' '最終名次']
        if c in dfcolumns
            pos_col = c
            break

    if name_col is None or pos_col is None
        stwritef"可用欄位{dfcolumnstolist)}")
        stwarning"⚠️ 賽果檔案缺少「馬名」或「名次」欄位請檢查 CSV 格式。")
        return

    # 清理數據
    df[name_col] = df[name_col]astypestr)strstrip)
    df[pos_col] = pdto_numericdf[pos_col] errors='coerce')
    df = dfdropnasubset=[pos_col name_col])
    df = df[df[name_col] = '']

    # 計算每匹馬嘅出賽次數、勝出次數、勝率
    stats = dfgroupbyname_col)agg
        總出賽=pos_col 'count')
        勝出=pos_col lambda x x == 1)sum))
    reset_index)

    stats['勝率'] = stats['勝出'] / stats['總出賽']
    stats = statssort_values'勝出' ascending=False)reset_indexdrop=True)
    stats = stats[stats['總出賽'] >= 1]

    stsuccessf"✅ 共 {lenstats)} 匹馬有效數據{lendf)} 條)")

    # 格式化顯示
    stats_display = statscopy)
    stats_display['勝率'] = stats_display['勝率']applylambda x f"{x1%}")
    stats_displaycolumns = ['馬名' '總出賽' '勝出' '勝率']

    stdataframestats_display use_container_width=True hide_index=True height=600)
def admin_jockey_ranking)
    stsubheader"🏇 騎師勝率排行榜")

    # 🛡️ 騎師中英文對照表
    JOCKEY_MAP = {
        "Z Purton" "潘頓"
        "H Bowman" "布文"
        "A Atzeni" "艾兆禮"
        "L Ferraris" "霍宏聲"
        "B Avdulla" "艾道拿"
        "K Teetan" "田泰安"
        "K C Leung" "梁家俊"
        "M F Poon" "潘明輝"
        "M Chadwick" "蔡明紹"
        "H Bentley" "班德禮"
        "J Moreira" "莫雷拉"
        "C Y Ho" "何澤堯"
        "A Badel" "巴度"
        "B Shinn" "寶遜"
        "L Hewitson" "希威森"
        "Y L Chung" "鍾易禮"
        "A Hamelin" "賀銘年"
        "E C W Wong" "黃智弘"
        "H T Mo" "巫顯東"
        "M L Yeung" "楊明綸"
        "C L Chau" "周俊樂"
        "M Barzalona" "巴米高"
        "K De Melo" "簡能"
        "J Orman" "奧爾民"
        "R Kingscote" "金誠剛"
        "H Y Yuen" "袁幸堯"
        "P N Wong" "黃寶妮"
        "M Newnham" "廖康銘"
        "D Eustace" "游達榮"
        "B Crawford" "桂福特"
        "D J Whyte" "韋達"
        "D J Hall" "賀賢"
        "A S Cruz" "告東尼"
        "C S Shum" "沈集成"
        "C Fownes" "方嘉柏"
        "J Size" "蔡約翰"
        "F C Lor" "羅富全"
        "K W Lui" "呂健威"
        "P F Yiu" "姚本輝"
        "W Y So" "蘇偉賢"
        "K L Man" "文家良"
        "T P Yung" "容天鵬"
        "Y S Tsui" "徐雨石"
        "C W Chang" "鄭俊偉"
        "C H Yip" "葉楚航"
        "M Newnham" "廖康銘"
        "J Richards" "黎昭昇"
        "D A Hayes" "大衛希斯"
        "P C Ng" "伍鵬志"
        "K H Ting" "丁冠豪"
        "D Whyte" "韋達"
        "G Mosse" "巫斯義"
        "T Marquand" "馬昆"
        "A K Chan" "陳嘉熙"
        "S De Sousa" "蘇兆輝"
        "N Callan" "高力"
        "R Moore" "莫雅"
        "P Beggy" "貝治"
        "A Kirby" "柯比"
        "J McDonald" "麥道朗"
        "H Doyle" "杜苑欣"
        "R Ryan" "羅理雅"
        "W Buick" "布宜學"
        "O Murphy" "莫菲"
        "T Berry" "貝利"
        "C Soumillon" "蘇銘倫"
        "J Doyle" "杜滿樂"
        "F Minarik" "米奈克"
        "T Marquand" "馬昆"
    }

    try
        df = pdread_csv"ALL_DATA_MERGEDcsv" encoding='utf-8-sig' low_memory=False)
        dfcolumns = [strc)replace'\ufeff' '')strip) for c in dfcolumns]

        # 🛡️ 智能偵測名次欄位
        pos_candidates = ['finish_position' 'Pla' '名次' '最終名次']
        pos_col = None
        max_valid = 0
        for c in pos_candidates
            if c in dfcolumns
                valid = pdto_numericdf[c] errors='coerce')notna)sum)
                if valid > max_valid
                    max_valid = valid
                    pos_col = c

        # 🛡️ 智能偵測騎師欄位優先中文如果冇就用英文)
        jockey_candidates = ['jockey_cn' '騎師' 'jockey' '騎師名']
        jockey_col = None
        max_valid = 0
        for c in jockey_candidates
            if c in dfcolumns
                valid = df[c]astypestr)strstrip)replace['nan' 'none' ''] pdNA)notna)sum)
                if valid > max_valid
                    max_valid = valid
                    jockey_col = c

        if pos_col is None or jockey_col is None
            stwarning"⚠️ 賽果檔案缺少「騎師」或「名次」欄位")
            stwritef"可用欄位{dfcolumnstolist)}")
            return

        temp = pdDataFrame)
        temp['騎師'] = df[jockey_col]astypestr)strstrip)
        temp['名次'] = pdto_numericdf[pos_col] errors='coerce')
        temp = tempdropnasubset=['名次'])
        temp = temp[~temp['騎師']strlower)isin['nan' 'none' ''])]

        if tempempty
            stwarning"⚠️ 過濾後數據為空")
            return

        total = temp['騎師']value_counts)
        wins = temp[temp['名次'] == 1]['騎師']value_counts)
        stats = pdDataFrame{'騎師' totalindex '總出賽' totalvalues})
        stats['勝出'] = stats['騎師']mapwins)fillna0)astypeint)
        stats['勝率'] = stats['勝出'] / stats['總出賽'])applylambda x f"{x1%}")

        # 🛡️ 將英文名轉做中文名
        stats['騎師'] = stats['騎師']applylambda x JOCKEY_MAPgetx x))

        stats = statssort_values'勝出' ascending=False)reset_indexdrop=True)

        stsuccessf"✅ 共 {lenstats)} 位騎師")
        stdataframestatshead30) use_container_width=True hide_index=True)
    except Exception as e
        sterrorf"讀取失敗{e}")
        import traceback
        stcodetracebackformat_exc))
def admin_trainer_ranking)
    stsubheader"🏇 練馬師勝率排行榜")
    try
        df = pdread_csv"ALL_DATA_MERGEDcsv" encoding='utf-8-sig' low_memory=False)
        dfcolumns = [strc)replace'\ufeff' '')strip) for c in dfcolumns]

        pos_series pos_name = _get_pos_seriesdf)
        stcaptionf"📊 使用名次欄位**{pos_name}**有效數據{pos_seriesnotna)sum)})")

        temp = pdDataFrame)
        temp['練馬師'] = df['trainer']astypestr)strstrip)
        temp['名次'] = pos_series
        temp = tempdropnasubset=['名次'])
        temp = temp[~temp['練馬師']strlower)isin['nan' 'none' ''])]

        if tempempty
            stwarning"⚠️ 過濾後數據為空")
            return

        total = temp['練馬師']value_counts)
        wins = temp[temp['名次'] == 1]['練馬師']value_counts)
        stats = pdDataFrame{'練馬師' totalindex '總出賽' totalvalues})
        stats['勝出'] = stats['練馬師']mapwins)fillna0)astypeint)
        stats['勝率'] = stats['勝出'] / stats['總出賽'])applylambda x f"{x1%}")
        stats = statssort_values'勝出' ascending=False)reset_indexdrop=True)

        tmap = {}
        if ospathexists"trainer_mappingjson")
            try
                tmap = load_json"trainer_mappingjson")
            except Exception
                pass
        if tmap
            stats['練馬師'] = stats['練馬師']maptmap)fillnastats['練馬師'])

        stsuccessf"✅ 共 {lenstats)} 位練馬師")
        stdataframestatshead30) use_container_width=True)
    except Exception as e
        sterrorf"讀取失敗{e}")
def admin_lottery_config)
    stsubheader"🎰 抽獎設定")
    config = load_lottery_config)
    prizes = configget"prizes" [])
    stwritef"目前有 **{lenprizes)}** 個獎品")

    # ===== 現有獎品表 =====
    if prizes
        _type_cn = {
            "virtual_coin" "🪙 虛擬幣"
            "vip_days" "👑 VIP"
            "free_predictions" "🔮 預測"
            "promo_code" "🎟️ 優惠碼"
            "custom" "🎁 自訂"
            "nothing" "😅 無獎"
        }
        rows = []
        for p in prizes
            rowsappend{
                "獎品" pget'name' '')
                "類型" _type_cngetpget'type' '') pget'type' ''))
                "數值" pget'value' 0)
                "權重" pget'weight' 0)
                "描述" pget'description' '')
            })
        stdataframepdDataFramerows) use_container_width=True hide_index=True)

    stdivider)
    stsubheader"➕ 新增獎品")

    # ===== 表單 =====
    col1 col2 col3 = stcolumns[2 1 1])
    with col1
        p_name = sttext_input"獎品名稱" key="lot_name")
    with col2
        p_value = stnumber_input"數值" min_value=0 value=100 key="lot_value")
    with col3
        p_weight = stnumber_input"權重" min_value=1 value=10 key="lot_weight")

    col_type col_desc = stcolumns[1 2])
    with col_type
        p_type = stselectbox
            "獎品類型"
            ["virtual_coin" "vip_days" "free_predictions" "promo_code" "custom" "nothing"]
            format_func=lambda x {
                "virtual_coin" "🪙 虛擬幣"
                "vip_days" "👑 VIP"
                "free_predictions" "🔮 預測"
                "promo_code" "🎟️ 優惠碼"
                "custom" "🎁 自訂"
                "nothing" "😅 無獎"
            }getx x)
            key="lot_type"
        
    with col_desc
        p_desc = sttext_input"描述" key="lot_desc")

    if stbutton"➕ 新增獎品" key="add_lot_v2" use_container_width=True)
        prizesappend{
            "name" p_name
            "type" p_type
            "value" p_value
            "weight" p_weight
            "description" p_desc
        })
        config["prizes"] = prizes
        if save_lottery_configconfig)
            stsuccess"✅ 已新增獎品")
            strerun)
        else
            sterror"❌ 儲存失敗")

    # ===== 編輯獎品 =====
    if prizes
        stdivider)
        stsubheader"✏️ 編輯獎品")
        for i p in enumerateprizes)
            with stexpanderf"{pget'name' '獎品')}權重 {pget'weight' 0)})")
                _w = _safe_intpget'weight' 10) 10)
                _v = _safe_intpget'value' 0) 0)
                ec1 ec2 = stcolumns2)
                with ec1
                    nw = stnumber_input"中獎機率" min_value=1 value=max1 _w) key=f"ew_{i}")
                with ec2
                    nv = stnumber_input"數值" min_value=0 value=max0 _v) key=f"ev_{i}")
                ca cb = stcolumns2)
                with ca
                    if stbutton"💾 儲存" key=f"sp_{i}" use_container_width=True)
                        prizes[i]['weight'] = nw
                        prizes[i]['value'] = nv
                        config["prizes"] = prizes
                        save_lottery_configconfig)
                        stsuccess"✅ 已儲存")
                        strerun)
                with cb
                    if stbutton"🗑️ 刪除" key=f"dp_{i}" use_container_width=True)
                        prizespopi)
                        config["prizes"] = prizes
                        save_lottery_configconfig)
                        stsuccess"✅ 已刪除")
                        strerun)
def admin_shop_config)
    stsubheader"🛒 商城設定")
    config = load_shop_config)
    items = configget"items" [])
    stwritef"目前有 **{lenitems)}** 件商品")
    if items
        try
            stdataframepdDataFrameitems) use_container_width=True)
        except Exception
            pass

    stdivider)
    stsubheader"➕ 新增商品")
    col1 col2 col3 = stcolumns3)
    with col1
        i_name = sttext_input"商品名稱" key="shop_name")
        i_type = stselectbox
            "商品類型"
            ["predictions" "vip_days" "lottery_draws" "title" "mystery_box"]
            key="shop_type"
        
    with col2
        i_price = stnumber_input"價格" min_value=0 value=100 key="shop_price")
        i_stock = stnumber_input"庫存" min_value=0 value=100 key="shop_stock")
    with col3
        i_desc = sttext_input"描述" key="shop_desc")

    if stbutton"➕ 新增商品" key="add_shop")
        itemsappend{
            "name" i_name "type" i_type "price" i_price
            "stock" i_stock "description" i_desc
        })
        config["items"] = items
        if save_shop_configconfig)
            stsuccess"✅ 已新增商品")
            strerun)
        else
            sterror"❌ 儲存失敗")

    if items
        stdivider)
        stsubheader"✏️ 直接編輯商品表格")
        try
            edited = stdata_editor
                pdDataFrameitems)
                use_container_width=True
                key="shop_editor"
                num_rows="dynamic"
            
            if stbutton"💾 儲存所有變更" key="save_shop")
                config["items"] = editedto_dictorient='records')
                save_shop_configconfig)
                stsuccess"✅ 已儲存")
                strerun)
        except Exception as e
            sterrorf"編輯器錯誤{e}")


        if submitted
            if not plan_choice
                sterror"❌ 請選擇方案")
                return
            username = stsession_stateget'username')
            if not username
                sterror"❌ 請先登入")
                return

            original_price = get_plan_priceplan_choice)
            final_price = original_price
            discount_desc = ""
            promo_code_used = None

            if promo_input
                promos = load_promos)
                promo_data = promosgetpromo_inputstrip))
                if promo_data and not promo_dataget'used' False)
                    expiry = promo_dataget'expiry')
                    valid = True
                    if expiry
                        try
                            if datetimefromisoformatexpiry) < datetimenow)
                                valid = False
                        except Exception
                            pass
                    if valid
                        dtype = promo_dataget'discount_type' 'percentage')
                        dval = promo_dataget'discount_value' 0)
                        if dtype == 'percentage'
                            final_price = original_price * 1 - dval / 100)
                            discount_desc = f"{dval}% 折扣"
                        elif dtype == 'fixed'
                            final_price = max0 original_price - dval)
                            discount_desc = f"減 ${dval}"
                        elif dtype == 'free'
                            final_price = 0
                            discount_desc = "全免"
                        final_price = roundfinal_price 2)
                        promo_code_used = promo_inputstrip)
                        stsuccessf"✅ 優惠碼已套用折扣後${final_price}")
                else
                    stwarning"⚠️ 優惠碼無效")            
            # 如果用到優惠碼立即標記為已使用
            if promo_code_used
                promos = load_promos)
                if promo_code_used in promos
                    promos[promo_code_used]['used'] = True
                    promos[promo_code_used]['used_by'] = username
                    promos[promo_code_used]['used_at'] = datetimenow)isoformat)
                    save_promospromos)

            success msg = submit_payment_requestusername plan_choice final_price discount_desc promo_code_used)
            if success
                stsuccessmsg)
                stinfof"方案{get_plan_nameplan_choice)}金額${final_price}")
                stinfo"📩 提交後請 Telegram 通知管理員")
def show_lottery_interfaceusername)
    stsubheader"🎰 每日抽獎")
    if not username
        stinfo"請先登入")
        return

    # 倒數計時
    try
        hk_tz = pytztimezone"Asia/Hong_Kong")
        now = datetimenowhk_tz)
        tm = now + timedeltadays=1))replacehour=0 minute=0 second=0 microsecond=0)
        secs = inttm - now)total_seconds))
        h m s = secs // 3600 secs % 3600) // 60 secs % 60
        stinfof"⏰ 距離下次重置**{h} 小時 {m} 分 {s} 秒**")
    except Exception
        pass

    config = load_lottery_config)
    prizes = configget"prizes" [])
    if not prizes
        stwarning"暫無獎品請管理員新增")
        return

    users = load_users)
    user = usersgetusername {})

    # ===== 🔥 每日自動重置抽獎次數 =====
    today = datetimenow)strftime'%Y-%m-%d')
    if userget'last_lottery_reset' '') = today
        # 每日免費派發 1 次抽獎機會可自行調整)
        daily_chances = 1
        user['lottery_chances'] = userget'lottery_chances' 0) + daily_chances
        user['last_lottery_reset'] = today
        users[username] = user
        save_usersusers)
        stsuccessf"🎁 每日重置你獲得 {daily_chances} 次抽獎機會")
        strerun)

    lottery_chances = userget'lottery_chances' 0)

    # 顯示抽獎次數
    stmarkdownf"""
    <div style="background linear-gradient135deg #667eea #764ba2)
                padding 18px 22px border-radius 14px color white
                text-align center margin-bottom 16px">
        <div style="font-size 14px opacity 09">🎟️ 你嘅抽獎機會</div>
        <div style="font-size 48px font-weight 800 line-height 12">{lottery_chances}</div>
        <div style="font-size 12px opacity 08">次</div>
    </div>
    """ unsafe_allow_html=True)

    if lottery_chances <= 0
        stwarning"⚠️ 你冇抽獎次數啦請聽日再嚟或者聯絡管理員增加。")
        return

    # 初始化 session state
    if 'lottery_rolling' not in stsession_state
        stsession_statelottery_rolling = False
    if 'lottery_result' not in stsession_state
        stsession_statelottery_result = None

    # ===== 抽獎動畫區域 =====
    animation_placeholder = stempty)

    if stsession_statelottery_rolling
        icons = ["🎁" "🎰" "💎" "🏆" "🎊" "⭐" "🍀" "🎯"]
        for i in range12)
            icon = icons[i % lenicons)]
            animation_placeholdermarkdownf"""
            <div style="background linear-gradient135deg #ffecd2 #fcb69f)
                        padding 40px border-radius 16px text-align center
                        border 3px dashed #ff6b6b">
                <div style="font-size 80px animation spin 03s linear infinite">{icon}</div>
                <div style="font-size 20px font-weight bold color #d63447 margin-top 10px">
                    抽獎中
                </div>
            </div>
            """ unsafe_allow_html=True)
            timesleep015)

    # 顯示中獎結果
    if stsession_statelottery_result is not None
        result = stsession_statelottery_result
        stmarkdownf"""
        <div style="background linear-gradient135deg #f9d423 #ff4e50)
                    padding 30px border-radius 16px text-align center
                    color white box-shadow 0 8px 25px rgba255788004)
                    animation pop 05s ease-out">
            <div style="font-size 70px">{result['icon']}</div>
            <div style="font-size 24px font-weight 800 margin-top 10px">
                🎉 恭喜中獎
            </div>
            <div style="font-size 32px font-weight 900 margin-top 12px
                        text-shadow 2px 2px 4px rgba00003)">
                {result['name']}
            </div>
            <div style="font-size 18px opacity 095 margin-top 10px">
                {result['desc']}
            </div>
        </div>
        <style>
            @keyframes pop {{
                0% {{ transform scale05) opacity 0 }}
                70% {{ transform scale105) }}
                100% {{ transform scale1) opacity 1 }}
            }}
            @keyframes spin {{
                0% {{ transform rotate0deg) }}
                100% {{ transform rotate360deg) }}
            }}
        </style>
        """ unsafe_allow_html=True)

        stballoons)
        stsnow)

        if stbutton"🔄 再抽一次" use_container_width=True key="roll_again")
            stsession_statelottery_result = None
            strerun)

    # ===== 抽獎按鈕 =====
    elif not stsession_statelottery_rolling
        if stbutton"🎲 開始抽獎" type="primary" use_container_width=True key="start_lottery")
            stsession_statelottery_rolling = True
            strerun)

    # ===== 執行抽獎邏輯 =====
    if stsession_statelottery_rolling
        # 扣一次抽獎次數
        users[username]['lottery_chances'] = lottery_chances - 1

        # 抽獎
        weights = [_safe_intpget'weight' 1) 1) for p in prizes]
        if sumweights) <= 0
            weights = [1] * lenprizes)
        chosen = randomchoicesprizes weights=weights k=1)[0]
        ptype = chosenget'type' 'nothing')
        pval = _safe_intchosenget'value' 0) 0)
        pname = chosenget'name' '獎品')

        icon = "🎁"
        desc = ""

        if ptype == 'virtual_coin'
            users[username]['virtual_balance'] = userget'virtual_balance' 0) + pval
            icon = "💰"
            desc = f"+${pval} 虛擬幣"
        elif ptype == 'vip_days'
            users[username]['group'] = 'VIP'
            users[username]['predictions_limit'] = -1
            icon = "👑"
            desc = f"VIP {pval} 天"
        elif ptype == 'free_predictions'
            if users[username]get'predictions_limit' 0) = -1
                users[username]['predictions_limit'] = users[username]get'predictions_limit' 0) + pval
            icon = "🔮"
            desc = f"{pval} 次免費預測"
        elif ptype == 'promo_code'
            code = generate_promo_code)
            promos = load_promos)
            promos[code] = {
                "used" False
                "expiry" datetimenow) + timedeltadays=30))isoformat)
                "discount_type" "percentage"
                "discount_value" 20
                "source" "lottery"
                "created_by" username
            }
            save_promospromos)
            icon = "🎟️"
            desc = f"優惠碼{code}"
            pname = f"優惠碼 {code}"
        elif ptype == 'nothing'
            icon = "😅"
            desc = "冇中獎下次再嚟"
        else
            icon = "🎁"
            desc = chosenget'description' '')

        save_usersusers)
        timesleep15)

        stsession_statelottery_result = {
            'name' pname
            'desc' desc
            'icon' icon
        }
        stsession_statelottery_rolling = False
        strerun)

    # ===== 獎品一覽 =====
    stdivider)
    with stexpander"🎁 獎品一覽" expanded=False)
        rows = []
        for p in prizes
            rowsappend{
                "獎品" pget'name' '')
                "類型" pget'type' '')
                "數值" pget'value' 0)
                "中獎機率" f"{pget'weight' 0)}"
            })
        stdataframepdDataFramerows) use_container_width=True hide_index=True)

def show_shop_interfaceusername)
    stsubheader"🛒 虛擬商城")
    if not username
        stinfo"請先登入")
        return

    users = load_users)
    user = usersgetusername {})
    balance = userget'virtual_balance' 0)
    stmetric"💎 你嘅虛擬幣結餘" f"${balance0f}")

    config = load_shop_config)
    items = configget"items" [])
    if not items
        stinfo"暫無商品")
        return

    for i item in enumerateitems)
        col1 col2 col3 = stcolumns[3 2 1])
        with col1
            stmarkdownf"**{itemget'name' '商品')}**")
            stcaptionitemget'description' ''))
        with col2
            stwritef"💰 ${itemget'price' 0)}")
            stcaptionf"庫存{itemget'stock' 0)}")
        with col3
            if stbutton"🛒 購買" key=f"buy_{i}")
                price = _safe_intitemget'price' 0) 0)
                stock = _safe_intitemget'stock' 0) 0)
                if stock <= 0
                    sterror"❌ 已售罄")
                elif balance < price
                    sterror"❌ 餘額不足")
                else
                    users[username]['virtual_balance'] = balance - price
                    items[i]['stock'] = stock - 1
                    config['items'] = items
                    save_shop_configconfig)
                    save_usersusers)
                    stsuccessf"✅ 已購買 {itemget'name')}")
                    strerun)
        stdivider)
def admin_dashboard)
    stsubheader"📊 系統儀表板")
    users = load_users)
    acc = load_accuracy)
    finance = load_finance)
    records = accget'records' [])
    proof = load_payment_proofs)
    today = datetimenow)date)
    c1 c2 c3 c4 c5 c6 = stcolumns6)
    c1metric"👤 總用戶" lenusers))
    c2metric"📈 今日新增" sum1 for u in usersvalues) if uget'created_at' '')startswithstrtoday))))
    c3metric"💰 總收入" f"${financeget'total_income' 0)2f}")
    c4metric"📊 總預測" lenrecords))
    total = len[r for r in records if rget'is_hit') is not None])
    hit = sum1 for r in records if rget'is_hit') is True)
    c5metric"🎯 命中率" f"{hit/total2%}" if total > 0 else "0%")
    pending = len[p for p in proofget'proof_records' []) if pget'status') == 'pending'])
    c6metric"⏳ 待審核" pending)

def admin_user_management)
    stsubheader"👥 用戶管理")

    users = load_users)

    if not users
        sterror"❌ 讀取用戶失敗請檢查 Supabase 連線")
        return

    stinfof"✅ 成功載入 {lenusers)} 個用戶")

    # ===== 顯示用戶列表 =====
    df_users = pdDataFrame[
        {
            "用戶名" u
            "群組" dget"group" "free")
            "等級" dget"level" "🥉 銅牌會員")
            "虛擬幣" dget"virtual_balance" 0)
            "付費" "✅" if dget"is_paid") else "❌"
        }
        for u d in usersitems)
    ])
    stdataframedf_users use_container_width=True hide_index=True)

    stdivider)

    # ===== 編輯用戶 =====
    stsubheader"✏️ 編輯用戶")
    selected_user = stselectbox"選擇要編輯嘅用戶" listuserskeys)) key="edit_user_select")

    if selected_user
        u = users[selected_user]

        c1 c2 = stcolumns2)
        with c1
            group_options = ["free" "paid" "VIP" "super_admin"]
            current_group = uget"group" "free")
            if current_group not in group_options
                current_group = "free"
            new_group = stselectbox"群組" group_options index=group_optionsindexcurrent_group) key="edit_user_group")

            level_options = ["🥉 銅牌會員" "🥈 銀牌會員" "🥇 金牌會員" "💎 鑽石會員" "👑 傳說會員" "👑 超級管理員"]
            current_level = uget"level" "🥉 銅牌會員")
            if current_level not in level_options
                current_level = "🥉 銅牌會員"
            new_level = stselectbox"等級" level_options index=level_optionsindexcurrent_level) key="edit_user_level")

            new_is_paid = stcheckbox"付費狀態" value=booluget"is_paid" False)) key="edit_user_paid")

        with c2
            new_password = sttext_input"新密碼留空 = 不改)" type="password" key="edit_user_pw")
            new_phone = sttext_input"手機號碼" value=uget"phone" "") key="edit_user_phone")
            new_exp = stnumber_input"經驗值" min_value=0 value=intuget"exp" 0)) step=1 key="edit_user_exp")

        new_note = sttext_area"備註" value=uget"note" "") key="edit_user_note")

        if stbutton"💾 儲存變更" type="primary" key="save_user_btn")
            users[selected_user]["group"] = new_group
            users[selected_user]["level"] = new_level
            users[selected_user]["is_paid"] = new_is_paid
            users[selected_user]["phone"] = new_phone
            users[selected_user]["note"] = new_note
            users[selected_user]["exp"] = intnew_exp)

            if new_password
                users[selected_user]["password"] = new_password

            # 根據群組自動調整預測次數限制
            if new_group in ["super_admin" "VIP" "paid"]
                users[selected_user]["predictions_limit"] = -1
            else
                users[selected_user]["predictions_limit"] = 2

            success = save_usersusers)
            if success
                stsuccessf"✅ 已儲存 {selected_user} 嘅變更")
                strerun)
            else
                sterror"❌ 儲存失敗請檢查 Supabase 權限")
def admin_downloads)
    stsubheader"📥 下載中心")
    stcaption"喺呢度下載系統嘅重要檔案備份。")

    import os
    from datetime import datetime

    download_files = [
        "usersjson" "用戶資料")
        "ai_predictionsjson" "AI 預測記錄")
        "race_results_cleancsv" "賽果數據")
        "racecard_uploadedcsv" "排位表")
        "odds_historycsv" "賠率歷史")
        "financejson" "財務記錄")
        "promo_codesjson" "優惠碼")
        "payment_proofsjson" "付款記錄")
        "admin_logjson" "管理員日誌")
        "user_activity_logjson" "用戶活動日誌")
        "contentjson" "公告內容")
        "automationjson" "自動化設定")
        "lottery_configjson" "抽獎設定")
        "lottery_recordsjson" "抽獎記錄")
        "shop_configjson" "商城設定")
        "shop_purchasesjson" "商城購買記錄")
        "predictionsdb" "SQLite 資料庫")
    ]

    for file_name description in download_files
        c1 c2 c3 = stcolumns[3 2 1])
        c1writef"**{file_name}**")
        c1captiondescription)

        if ospathexistsfile_name)
            size = ospathgetsizefile_name)
            mtime = datetimefromtimestampospathgetmtimefile_name))strftime'%Y-%m-%d %H%M%S')
            c2captionf"大小{size/10241f} KB　|　最後更新{mtime}")
            with openfile_name "rb") as f
                c3download_button
                    label="📥 下載"
                    data=f
                    file_name=file_name
                    key=f"download_{file_name}"
                
        else
            c2caption"暫無備份")
            c3caption"—")

    stdivider)

    # ===== AI 預測記錄 =====
    stmarkdown"### 🤖 AI 預測記錄")
    try
        from database import load_predictions
        ai_data = load_predictions)
        if not ai_data
            stinfo"📭 暫無預測記錄")
        else
            stinfof"✅ 成功讀取 {lenai_data)} 個預測記錄")
            df_ai = pdDataFrame[
                {
                    "日期" vget"date")
                    "場次" vget"race")
                    "頭馬" vget"top_horse")
                    "預測時間" strvget"predicted_at" ""))[16]
                }
                for v in ai_datavalues)
            ])
            stdataframedf_ai use_container_width=True hide_index=True)
    except Exception as e
        sterrorf"❌ 讀取失敗{e}")

def admin_manage_predictions)
    stsubheader"📊 管理用戶次數")
    users = load_users)
    if not users
        stinfo"暫無用戶")
        return

    sel = stselectbox"👤 揀用戶" listuserskeys)) key="mp_user")
    if not sel
        return

    user = users[sel]
    lottery_chances = userget'lottery_chances' 0)
    cur_bal = userget'virtual_balance' 0)

    stinfof"你而家揀緊**{sel}**　|　🎰 抽獎 {lottery_chances} 次　|　💰 虛擬幣 ${cur_bal0f}")

    col1 col2 = stcolumns2)

    with col1
        stmarkdown"**🎰 加抽獎次數**")
        add_lottery = stnumber_input"次數" min_value=1 value=1 key="add_lot")
        if stbutton"➕ 加抽獎" use_container_width=True key="do_add_lot")
            users[sel]['lottery_chances'] = lottery_chances + add_lottery
            save_usersusers)
            stsuccessf"✅ 已幫 {sel} 加 {add_lottery} 次")
            strerun)

    with col2
        stmarkdown"**💰 送虛擬幣**")
        add_coin = stnumber_input"金額" min_value=1 value=100 step=100 key="add_coin")
        if stbutton"🎁 送幣" use_container_width=True key="do_add_coin")
            users[sel]['virtual_balance'] = cur_bal + add_coin
            save_usersusers)
            stsuccessf"✅ 已送 ${add_coin0f} 俾 {sel}")

def admin_analytics)
    stsubheader"📊 數據分析")
    users = load_users)
    if not users
        stinfo"暫無用戶")
        return
    df = pdDataFramefrom_dictusers orient='index')
    if 'created_at' in dfcolumns and HAS_PLOTLY
        df['created_at'] = pdto_datetimedf['created_at'] errors='coerce')
        df = dfdropnasubset=['created_at'])
        df['date'] = df['created_at']dtdate
        daily = dfgroupby'date')size)reset_indexname='new')sort_values'date')
        daily['cum'] = daily['new']cumsum)
        fig = pxlinedaily x='date' y=['new' 'cum'] title='用戶增長')
        stplotly_chartfig use_container_width=True)
# ============================================================
# 💰 付款審核
# ============================================================
def admin_payment_review)
    stsubheader"📤 付款審核")
    pending = get_all_pending_requests)
    if not pending
        stinfo"✅ 目前沒有待審核付款")
        return
    for item in pending
        u = item['username']
        req = item['request']
        c1 c2 c3 c4 = stcolumns[2 2 1 1])
        c1writef"👤 **{u}**")
        c2writef"📌 {reqget'plan_name')}　💰 ${reqget'final_price')}")
        if c3button"✅ 批准" key=f"ap_{reqget'id')}")
            ok msg = approve_payment_requestu req['id'] stsession_stateget'username' 'admin'))
            if ok
                stsuccessmsg)
            else
                sterrormsg)
            strerun)
        if c4button"❌ 拒絕" key=f"rj_{reqget'id')}")
            ok msg = reject_payment_requestu req['id'] stsession_stateget'username' 'admin'))
            if ok
                stwarningmsg)
            else
                sterrormsg)
            strerun)
        stdivider)

    stdivider)
    stmarkdownf"### ✅ 已批准{lenapproved)} 筆)")
    if not approvedempty
        display_cols = [c for c in ['username' 'amount' 'vip_days' 'rewarded_at'] if c in approvedcolumns]
        stdataframeapproved[display_cols] use_container_width=True hide_index=True)
    else
        stinfo"暫無已批准記錄。")

    if not rejectedempty
        stmarkdownf"### ❌ 已拒絕{lenrejected)} 筆)")
        display_cols = [c for c in ['username' 'amount' 'vip_days' 'rewarded_at'] if c in rejectedcolumns]
        stdataframerejected[display_cols] use_container_width=True hide_index=True)

def admin_course_analysis)
    stsubheader"📊 場地/路程勝率分析")
    try
        df = pdread_csv"ALL_DATA_MERGEDcsv" encoding='utf-8-sig' low_memory=False)
        dfcolumns = [strc)replace'\ufeff' '')strip) for c in dfcolumns]
        df = dfreset_indexdrop=True)

        # 名次
        pos_series pos_name = _get_pos_seriesdf)
        stcaptionf"📊 使用名次欄位**{pos_name}**有效數據{pos_seriesnotna)sum)})")

        # 搵場地欄位
        track_col = None
        for c in dfcolumns
            if 'RC/Track' in strc) or 'track' in strc)lower) or 'course' in strc)lower) or '場地' in strc)
                track_col = c
                break

        # 搵路程欄位
        dist_col = None
        for c in dfcolumns
            if strc)lower) in ['dist' 'dist' 'distance'] or '路程' in strc)
                dist_col = c
                break

        stwritef"**場地欄位**`{track_col}`　**路程欄位**`{dist_col}`")

        # ===== 場地分析 =====
        if track_col
            stdivider)
            stmarkdown"### 🏟️ 場地勝率分析")

            temp = df[[track_col]]copy)
            tempcolumns = ['場地']
            temp['名次'] = pos_seriesvalues
            temp['場地'] = temp['場地']astypestr)strstrip)
            temp = tempdropnasubset=['名次'])
            temp = temp[~temp['場地']strlower)isin['nan' 'none' '' '-'])]

            if not tempempty
                total = temp['場地']value_counts)
                wins = temp[temp['名次'] == 1]['場地']value_counts)
                stats = pdDataFrame{'場地' totalindex '總出賽' totalvalues})
                stats['勝出'] = stats['場地']mapwins)fillna0)astypeint)
                stats['勝率'] = stats['勝出'] / stats['總出賽'])applylambda x f"{x1%}")
                stats = statssort_values'勝出' ascending=False)reset_indexdrop=True)
                statsindex = statsindex + 1
                stdataframestats use_container_width=True)
            else
                stinfo"冇場地數據")

        # ===== 路程分析 =====
        if dist_col
            stdivider)
            stmarkdown"### 📏 路程勝率分析")

            temp = df[[dist_col]]copy)
            tempcolumns = ['路程']
            temp['名次'] = pos_seriesvalues
            temp['路程'] = pdto_numerictemp['路程'] errors='coerce')
            temp = tempdropnasubset=['名次' '路程'])
            temp['路程'] = temp['路程']astypeint)astypestr) + ' 米'

            if not tempempty
                total = temp['路程']value_counts)
                wins = temp[temp['名次'] == 1]['路程']value_counts)
                stats = pdDataFrame{'路程' totalindex '總出賽' totalvalues})
                stats['勝出'] = stats['路程']mapwins)fillna0)astypeint)
                stats['勝率'] = stats['勝出'] / stats['總出賽'])applylambda x f"{x1%}")
                stats = statssort_values'勝出' ascending=False)reset_indexdrop=True)
                statsindex = statsindex + 1
                stdataframestats use_container_width=True)
            else
                stinfo"冇路程數據")

        # ===== 場地 + 路程組合 =====
        if track_col and dist_col
            stdivider)
            stmarkdown"### 🎯 場地 × 路程 組合分析")

            temp = df[[track_col dist_col]]copy)
            tempcolumns = ['場地' '路程']
            temp['名次'] = pos_seriesvalues
            temp['場地'] = temp['場地']astypestr)strstrip)
            temp['路程'] = pdto_numerictemp['路程'] errors='coerce')
            temp = tempdropnasubset=['名次' '路程'])
            temp = temp[~temp['場地']strlower)isin['nan' 'none' '' '-'])]
            temp['路程'] = temp['路程']astypeint)astypestr) + '米'
            temp['組合'] = temp['場地'] + ' | ' + temp['路程']

            if not tempempty
                total = temp['組合']value_counts)
                wins = temp[temp['名次'] == 1]['組合']value_counts)
                stats = pdDataFrame{'場地 | 路程' totalindex '總出賽' totalvalues})
                stats['勝出'] = stats['場地 | 路程']mapwins)fillna0)astypeint)
                stats['勝率'] = stats['勝出'] / stats['總出賽'])applylambda x f"{x1%}")
                stats = statssort_values'勝出' ascending=False)reset_indexdrop=True)
                statsindex = statsindex + 1
                stdataframestatshead30) use_container_width=True)
    except Exception as e
        sterrorf"讀取失敗{e}")
        import traceback
        stcodetracebackformat_exc))

def admin_monthly_report)
    stsubheader"📅 每月命中率報告")
    acc = load_accuracy)
    records = accget'records' [])
    valid = [r for r in records if rget'is_hit') is not None]
    if not valid
        stinfo"暫無足夠數據")
        return
    df = pdDataFramevalid)
    if 'date' not in dfcolumns
        stinfo"缺少日期")
        return
    df['date'] = pdto_datetimedf['date'] errors='coerce')
    df = dfdropnasubset=['date'])
    df['month'] = df['date']dtto_period'M')astypestr)
    monthly = dfgroupby'month')agg
        total='is_hit' 'count')
        hit='is_hit' lambda x x == True)sum))
    reset_index)
    monthly['hit_rate'] = monthly['hit'] / monthly['total']
    stdataframemonthly use_container_width=True)

def admin_finance)
    stsubheader"💰 財務管理")
    f = load_finance)
    c1 c2 c3 = stcolumns3)
    c1metric"總收入" f"${fget'total_income' 0)2f}")
    c2metric"本月" f"${fget'monthly_income' 0)2f}")
    c3metric"今年" f"${fget'yearly_income' 0)2f}")
    with stexpander"➕ 新增收入")
        a = stnumber_input"金額" min_value=00 step=100 key="fin_amt")
        d = sttext_input"描述" key="fin_desc")
        if stbutton"記錄" key="fin_add")
            for k in ['total_income' 'monthly_income' 'yearly_income']
                f[k] = fgetk 0) + a
            save_financef)
            stsuccess"✅ 已記錄")
            strerun)

def _is_promo_validpromo)
    if promoget'used' False)
        return False
    expiry = promoget'expiry')
    if not expiry
        return True
    try
        return datetimefromisoformatexpiry) >= datetimenow)
    except Exception
        return False


def admin_promo_codes)
    stsubheader"🎟️ 優惠碼管理")
    promos = load_promos)

    # ===== 統計 =====
    if promos
        total = lenpromos)
        used = sum1 for p in promosvalues) if pget'used' False))
        active = sum1 for p in promosvalues) if not pget'used' False) and _is_promo_validp))
        expired = sum1 for p in promosvalues) if not pget'used' False) and not _is_promo_validp))
        total_discount = sumpget'discount_amount' 0) for p in promosvalues) if pget'used' False))

        c1 c2 c3 c4 c5 = stcolumns5)
        c1metric"🎟️ 總數" total)
        c2metric"✅ 已使用" used)
        c3metric"🟢 有效" active)
        c4metric"🔴 已過期" expired)
        c5metric"💰 總折扣" f"${total_discount0f}")
    else
        total = used = active = expired = 0

    stdivider)

    # ===== 產生新優惠碼 =====
    stsubheader"➕ 產生新優惠碼")
    col1 col2 col3 = stcolumns3)
    with col1
        duration = stnumber_input"有效期 天)" min_value=1 value=30 key="pr_dur")
        quantity = stnumber_input"數量" min_value=1 value=1 max_value=100 key="pr_qty")
        dtype = stselectbox
            "折扣類型"
            ["percentage" "fixed" "free" "first_order" "min_spend"]
            key="pr_dtype"
            format_func=lambda x {
                "percentage" "百分比折扣如 20% off)"
                "fixed" "固定金額如 -$50)"
                "free" "完全免費"
                "first_order" "首單優惠"
                "min_spend" "滿減消費滿 X 減 Y)"
            }getx x)
        
    with col2
        dval = stnumber_input"折扣數值" min_value=0 value=20 key="pr_dval")
        min_spend = stnumber_input"最低消費 滿減用)" min_value=0 value=100 key="pr_minspend")
        max_uses = stnumber_input"每人限用次數" min_value=0 value=1 key="pr_maxuses")
    with col3
        stwrite"")
        stwrite"")
        note = sttext_input"備註選填)" key="pr_note")

    if stbutton"🎟️ 產生優惠碼" type="primary" use_container_width=True key="pr_gen")
        new_codes = []
        for _ in rangeintquantity))
            code = generate_promo_code)
            promos[code] = {
                "used" False
                "expiry" datetimenow) + timedeltadays=duration))isoformat)
                "created_at" datetimenow)isoformat)
                "discount_type" dtype
                "discount_value" dval
                "min_spend" min_spend
                "max_uses_per_user" max_uses
                "used_by" []
                "discount_amount" 0
                "note" note
            }
            new_codesappendcode)
        save_promospromos)
        stsuccessf"✅ 已產生 {lennew_codes)} 個優惠碼")
        stcode"\n"joinnew_codes))
        strerun)

    stdivider)

    # ===== 篩選清單 =====
    if promos
        stsubheader"📋 優惠碼清單")
        filter_option = stradio
            "篩選"
            ["全部" "有效" "已使用" "已過期"]
            horizontal=True
            key="pr_filter"
        

        filtered = {}
        for code p in promositems)
            is_used = pget'used' False)
            is_valid = _is_promo_validp)
            if filter_option == "全部"
                filtered[code] = p
            elif filter_option == "有效" and not is_used and is_valid
                filtered[code] = p
            elif filter_option == "已使用" and is_used
                filtered[code] = p
            elif filter_option == "已過期" and not is_used and not is_valid
                filtered[code] = p

        if filtered
            rows = []
            for code p in filtereditems)
                expiry = pget'expiry' '')
                days_left = "永久"
                if expiry
                    try
                        exp_dt = datetimefromisoformatexpiry)
                        delta = exp_dt - datetimenow))days
                        days_left = f"{delta} 天" if delta >= 0 else "已過期"
                    except Exception
                        pass

                used_by = pget'used_by' [])
                used_by_str = " "joinused_by) if used_by else "-"
                status = "✅ 已使用" if pget'used' False) else "🟢 有效" if _is_promo_validp) else "🔴 過期")

                rowsappend{
                    "優惠碼" code
                    "類型" pget'discount_type' '')
                    "數值" pget'discount_value' 0)
                    "狀態" status
                    "剩餘" days_left
                    "使用者" used_by_str
                    "備註" pget'note' '')
                })

            stdataframepdDataFramerows) use_container_width=True hide_index=True)
        else
            stinfof"冇符合「{filter_option}」嘅優惠碼")

    stdivider)

    # ===== 快速操作 =====
    stsubheader"⚡ 快速操作")
    ca cb cc = stcolumns3)
    with ca
        if stbutton"🧹 清理過期優惠碼" use_container_width=True key="pr_clean")
            before = lenpromos)
            promos = {k v for k v in promositems)
                      if vget'used' False) or _is_promo_validv)}
            save_promospromos)
            stsuccessf"✅ 已清理 {before - lenpromos)} 個過期優惠碼")
            strerun)
    with cb
        if promos
            rows = []
            for code p in promositems)
                rowsappend{
                    "優惠碼" code
                    "類型" pget'discount_type' '')
                    "數值" pget'discount_value' 0)
                    "過期日" pget'expiry' '')
                    "已使用" pget'used' False)
                    "備註" pget'note' '')
                })
            csv = pdDataFramerows)to_csvindex=False)encode'utf-8-sig')
            stdownload_button
                "📥 下載優惠碼 CSV"
                data=csv
                file_name=f"promo_codes_{datetimenow)strftime'%Y%m%d')}csv"
                mime="text/csv"
                use_container_width=True
                key="pr_dl_btn"
            
    with cc
        confirm_clear = stcheckbox"確認清空" key="pr_confirm_clear")
        if stbutton"🗑️ 清空所有優惠碼" use_container_width=True key="pr_clear_all")
            if confirm_clear
                save_promos{})
                stsuccess"✅ 已清空所有優惠碼")
                strerun)
            else
                stwarning"請先勾選「確認清空」")
def admin_accuracy_monitor)
    stsubheader"📈 AI 預測準確率監控頭 3 名)")

    from database import load_predictions
    ai_data = load_predictions)  # 👈 統一用 ai_data

    if not ai_data
        stwarning"⚠️ 尚未有任何預測紀錄請先執行預測")
        return

    stinfof"✅ 成功讀取 {lenai_data)} 個預測紀錄")

    result_file = "race_results_cleancsv"
    if not ospathexistsresult_file)
        stwarning"⚠️ 未有賽果檔案")
        return

    try
        results_df = pdread_csvresult_file encoding='utf-8-sig')
        results_df['race_date'] = pdto_datetimeresults_df['race_date'] errors='coerce')
        results_df = results_dfdropnasubset=['race_date'])
        results_df['race_date_str'] = results_df['race_date']dtstrftime'%Y-%m-%d')
        results_df['race_no'] = pdto_numericresults_df['race_no'] errors='coerce')
        results_df['finish_position'] = pdto_numericresults_df['finish_position'] errors='coerce')
        results_df['horse_name'] = results_df['horse_name']astypestr)strstrip)
        results_df['horse_name'] = results_df['horse_name']strreplacer'\[A-Z]\d+\)' '' regex=True)strstrip)
        
        # 👇👇👇 新增如果 CSV 冇場地欄位自動根據日期推算 👇👇👇
        if 'venue' not in results_dfcolumns and 'racecourse' not in results_dfcolumns and '馬場' not in results_dfcolumns
            # 0=Monday 1=Tuesday 2=Wednesday 3=Thursday 4=Friday 5=Saturday 6=Sunday
            results_df['venue'] = results_df['race_date']apply
                lambda d 'HV' if dweekday) == 2 else 'ST' if dweekday) in [5 6] else '未知')
            
        else
            # 如果有現成欄位就直接用
            for col in ['venue' 'racecourse' '馬場']
                if col in results_dfcolumns
                    results_df['venue'] = results_df[col]
                    break
        # 👆👆👆 新增部分完結 👆👆👆
                
    except Exception as e
        sterrorf"❌ 讀取賽果失敗{e}")
        return

    real_top3 = {}
    venue_map = {}
    
    for _ row in results_dfiterrows)
        if pdisnarow['race_no']) or pdisnarow['finish_position'])
            continue
        key = f"{row['race_date_str']}_{introw['race_no'])}"
        
        # 記錄場地
        if key not in venue_map
            venue_map[key] = rowget'venue' '未知')
        
        if key not in real_top3
            real_top3[key] = []
        if row['finish_position'] <= 3
            real_top3[key]append{
                'horse' row['horse_name']
                'pos' introw['finish_position'])
            })

    compare_rows = []
    combo_hit = 0
    total_with_result = 0
    pending_count = 0
    horse_hit = 0
    horse_total = 0

    for key pred in ai_dataitems)
        date_str = predget'date')
        race_no = predget'race')
        all_horses = predget'all_horses' [])

        pred_top3 = all_horses[3] if lenall_horses) >= 3 else all_horses
        pred_top3_str = " "joinpred_top3)

        lookup_key = f"{date_str}_{race_no}"
        current_venue = venue_mapgetlookup_key '未知')
        
        if lookup_key not in real_top3 or not real_top3[lookup_key]
            compare_rowsappend{
                '日期' date_str
                '場次' race_no
                '場地' current_venue
                '預測頭3名' pred_top3_str
                '真實頭3名' '⏳ 未有賽果'
                '命中數' '-'
                '結果' '⏳ 待定'
            })
            pending_count += 1
            continue

        real_top3_list = real_top3[lookup_key]
        real_names = [r['horse'] for r in real_top3_list]
        real_str = " "join[f"{r['horse']}{r['pos']})" for r in real_top3_list])

        hits = [h for h in pred_top3 if h in real_names]
        hit_count = lenhits)

        total_with_result += 1
        horse_total += lenpred_top3)
        horse_hit += hit_count

        if hit_count > 0
            combo_hit += 1
            result_str = f"✅ 命中 {hit_count} 匹"
        else
            result_str = "❌ 全部失準"

        compare_rowsappend{
            '日期' date_str
            '場次' race_no
            '場地' current_venue
            '預測頭3名' pred_top3_str
            '真實頭3名' real_str
            '命中數' hit_count
            '結果' result_str
        })

    c1 c2 c3 c4 = stcolumns4)
    c1metric"📊 總預測" lenai_data))
    c2metric"✅ 已比對" total_with_result)
    c3metric"🎯 命中場次" combo_hit)
    if total_with_result > 0
        combo_rate = combo_hit / total_with_result
        c4metric"📈 場次命中率" f"{combo_rate1%}")
    else
        c4metric"📈 場次命中率" "N/A")

    if horse_total > 0
        stmetric
            "🐎 馬匹命中率預測頭3名中有幾多匹跑入真實頭3名)"
            f"{horse_hit}/{horse_total} = {horse_hit/horse_total1%}"
        

    if pending_count > 0
        stcaptionf"⏳ 仲有 {pending_count} 場未出賽果")
        
    # ===== 分場地命中率 =====
    stmarkdown"---")
    stsubheader"📍 分場地命中率")
    venue_stats = {}
    for row in compare_rows
        v = row['場地']
        if row['結果'] == '⏳ 待定'
            continue
        if v not in venue_stats
            venue_stats[v] = {'total' 0 'hit' 0}
        venue_stats[v]['total'] += 1
        if row['命中數'] = '-' and introw['命中數']) > 0
            venue_stats[v]['hit'] += 1
            
    if venue_stats
        vc1 vc2 = stcolumns2)
        for idx v stats) in enumeratevenue_statsitems))
            if stats['total'] > 0
                rate = stats['hit'] / stats['total']
                if idx == 0
                    vc1metricf"{v} 命中率" f"{rate1%}" f"{stats['hit']}/{stats['total']} 場")
                else
                    vc2metricf"{v} 命中率" f"{rate1%}" f"{stats['hit']}/{stats['total']} 場")
    else
        stinfo"暫時未有足夠數據計算分場地命中率")
        
    # ===== 命中率走勢圖 =====
    stmarkdown"---")
    stsubheader"📉 命中率走勢圖")
    if compare_rows
        df_trend = pdDataFramecompare_rows)
        df_trend = df_trend[df_trend['結果'] = '⏳ 待定']
        
        if not df_trendempty
            trend_data = []
            for date group in df_trendgroupby'日期')
                total = lengroup)
                hit_races = lengroup[group['命中數']applylambda x intx) if strx)isdigit) else 0) > 0])
                if total > 0
                    trend_dataappend{
                        '日期' date
                        '場次命中率' hit_races / total
                    })
            
            df_trend_final = pdDataFrametrend_data)sort_values'日期')
            fig = pxlinedf_trend_final x='日期' y='場次命中率' markers=True title='每日場次命中率走勢')
            figupdate_layoutyaxis_tickformat='0%' xaxis_title='日期' yaxis_title='命中率')
            stplotly_chartfig use_container_width=True)
    else
        stinfo"暫無足夠數據顯示走勢圖")

    # ===== 明細表 =====
    if compare_rows
        stsubheader"📋 預測頭3名 vs 真實頭3名")
        df = pdDataFramecompare_rows)sort_values['日期' '場次'] ascending=[False True])

        def _colorrow)
            if row['結果'] == '⏳ 待定'
                return ['background-color #fff3cd'] * lenrow)
            elif '✅' in strrow['結果'])
                return ['background-color #d4edda'] * lenrow)
            else
                return ['background-color #f8d7da'] * lenrow)

        stdataframedfstyleapply_color axis=1) use_container_width=True hide_index=True)

    # ===== 7 管理員操作 =====
    stdivider)
    stsubheader"🔧 管理操作")
    if stbutton"🔄 重新整理" use_container_width=True key="refresh_acc")
        strerun)

def admin_subscription)
    stsubheader"⏰ 訂閱管理")
    users = load_users)
    paid = {u d for u d in usersitems) if dget'is_paid' False) or dget'group') in ['VIP' 'super_admin']}
    if not paid
        stinfo"暫無付費用戶")
    else
        df = pdDataFramefrom_dictpaid orient='index')
        for c in ['is_paid' 'group' 'plan' 'paid_date' 'expiry_date']
            if c not in dfcolumns
                df[c] = None
        stdataframedf[['is_paid' 'group' 'plan' 'paid_date' 'expiry_date']] use_container_width=True)
    stdivider)
    if stbutton"🔍 檢查並終止過期會員" key="check_exp")
        users = load_users)
        today = datetimenow)
        exp = []
        for uid u in usersitems)
            if uget'group') == 'VIP' and uget'expiry_date')
                try
                    if pdto_datetimeu['expiry_date']) < today
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        u['plan'] = None
                        expappenduid)
                except Exception
                    pass
        if exp
            save_usersusers)
            stsuccessf"✅ 已降級 {lenexp)} 位{' 'joinexp)}")
        else
            stinfo"✅ 沒有過期會員")

def admin_payment_review)
    stsubheader"📤 付款審核")
    pending = get_all_pending_requests)
    if not pending
        stinfo"✅ 目前沒有待審核付款")
        return
    for item in pending
        u = item['username']
        req = item['request']
        c1 c2 c3 c4 = stcolumns[2 2 1 1])
        c1writef"👤 **{u}**")
        c2writef"📌 {reqget'plan_name')}　💰 ${reqget'final_price')}")
        if c3button"✅ 批准" key=f"ap_{reqget'id')}")
            ok msg = approve_payment_requestu req['id'] stsession_stateget'username' 'admin'))
            if ok
                stsuccessmsg)
            else
                sterrormsg)
            strerun)
        if c4button"❌ 拒絕" key=f"rj_{reqget'id')}")
            ok msg = reject_payment_requestu req['id'] stsession_stateget'username' 'admin'))
            if ok
                stwarningmsg)
            else
                sterrormsg)
            strerun)
        stdivider)
def admin_reward_management)
    stsubheader"❤️ 打賞管理")

    headers = {
        "apikey" SUPABASE_KEY
        "Authorization" f"Bearer {SUPABASE_KEY}"
        "Content-Type" "application/json"
    }

    tab1 tab2 = sttabs["📋 審核打賞" "⚙️ 打賞設定"])

    # ============================================================
    # 📋 Tab 1審核打賞
    # ============================================================
    with tab1
        stcaption"審核用戶打賞批准後會自動加 VIP 天數。")

        try
            res = requestsget
                f"{SUPABASE_URL}/rest/v1/reward_historyorder=rewarded_atdesc&limit=50"
                headers=headers
            
            records = resjson) if resstatus_code == 200 else []
        except Exception as e
            sterrorf"❌ 讀取打賞記錄失敗{e}")
            records = []

        if not records
            stinfo"📭 暫無打賞記錄。")
        else
            df = pdDataFramerecords)
            if 'status' in dfcolumns
                pending = df[df['status'] == 'pending']
                approved = df[df['status'] == 'approved']
                rejected = df[df['status'] == 'rejected']
            else
                pending = df
                approved = pdDataFrame)
                rejected = pdDataFrame)

            stmarkdownf"### 📋 待審核{lenpending)} 筆)")
            if pendingempty
                stinfo"✅ 暫無待審核打賞。")
            else
                for _ row in pendingiterrows)
                    with stcontainer)
                        c1 c2 c3 c4 c5 c6 = stcolumns[2 1 1 2 1 1])
                        c1writef"👤 **{rowget'username' '未知')}**")
                        c2writef"${rowget'amount' 0)0f}")
                        c3writef"+{rowget'vip_days' 0)} 日")
                        c4captionf"🕐 {strrowget'rewarded_at' ''))[16]}")

                        if c5button"✅ 批准" key=f"approve_{row['id']}" use_container_width=True)
                            username = rowget'username')
                            vip_days = introwget'vip_days' 0))

                            u_res = requestsget
                                f"{SUPABASE_URL}/rest/v1/usersusername=eq{username}"
                                headers=headers
                            
                            if u_resstatus_code == 200 and u_resjson)
                                user = u_resjson)[0]
                                expiry = userget'expiry_date') or datetimenow)strftime'%Y-%m-%d')
                                try
                                    expiry_dt = datetimestrptimeexpiry '%Y-%m-%d')
                                except Exception
                                    expiry_dt = datetimenow)
                                new_expiry = expiry_dt + timedeltadays=vip_days))strftime'%Y-%m-%d')

                                requestspatch
                                    f"{SUPABASE_URL}/rest/v1/usersusername=eq{username}"
                                    headers=headers
                                    json={
                                        "user_group" "VIP"
                                        "is_paid" True
                                        "expiry_date" new_expiry
                                    }
                                

                            requestspatch
                                f"{SUPABASE_URL}/rest/v1/reward_historyid=eq{row['id']}"
                                headers=headers
                                json={"status" "approved"}
                            
                            stsuccessf"✅ 已批准 {username}加 {vip_days} 日 VIP")
                            strerun)

                        if c6button"❌ 拒絕" key=f"reject_{row['id']}" use_container_width=True)
                            requestspatch
                                f"{SUPABASE_URL}/rest/v1/reward_historyid=eq{row['id']}"
                                headers=headers
                                json={"status" "rejected"}
                            
                            stwarningf"已拒絕 {rowget'username' '')} 嘅打賞")
                            strerun)

            stdivider)
            stmarkdownf"### ✅ 已批准{lenapproved)} 筆)")
            if not approvedempty
                display_cols = [c for c in ['username' 'amount' 'vip_days' 'rewarded_at'] if c in approvedcolumns]
                stdataframeapproved[display_cols] use_container_width=True hide_index=True)
            else
                stinfo"暫無已批准記錄。")

            if not rejectedempty
                stmarkdownf"### ❌ 已拒絕{lenrejected)} 筆)")
                display_cols = [c for c in ['username' 'amount' 'vip_days' 'rewarded_at'] if c in rejectedcolumns]
                stdataframerejected[display_cols] use_container_width=True hide_index=True)

    # ============================================================
    # ⚙️ Tab 2打賞設定修改金額、VIP天數、新增、刪除)
    # ============================================================
    with tab2
        stcaption"喺呢度新增、修改或刪除打賞選項前台會即時同步。")

        try
            res = requestsget
                f"{SUPABASE_URL}/rest/v1/reward_configorder=amountasc"
                headers=headers
            
            configs = resjson) if resstatus_code == 200 else []
        except Exception as e
            sterrorf"❌ 讀取失敗{e}")
            configs = []

        if not configs
            stinfo"📭 暫無打賞選項請喺下面新增。")
            df = pdDataFramecolumns=['id' 'amount' 'vip_days' 'label' 'enabled'])
        else
            df = pdDataFrameconfigs)
            for col in ['id' 'amount' 'vip_days' 'label' 'enabled']
                if col not in dfcolumns
                    df[col] = None

        stmarkdown"### 📝 編輯現有選項")
        if not dfempty
            edited = stdata_editor
                df[['id' 'amount' 'vip_days' 'label' 'enabled']]
                use_container_width=True
                hide_index=True
                column_config={
                    "id" stcolumn_configNumberColumn"ID" disabled=True)
                    "amount" stcolumn_configNumberColumn"金額 $)" min_value=1 step=1)
                    "vip_days" stcolumn_configNumberColumn"VIP 天數" min_value=1 step=1)
                    "label" stcolumn_configTextColumn"顯示標籤" max_chars=30)
                    "enabled" stcolumn_configCheckboxColumn"啟用")
                }
                key="reward_config_editor"
            

            c1 c2 = stcolumns2)
            with c1
                if stbutton"💾 儲存所有修改" type="primary" use_container_width=True)
                    success = 0
                    for _ row in editediterrows)
                        try
                            res = requestspatch
                                f"{SUPABASE_URL}/rest/v1/reward_configid=eq{row['id']}"
                                headers=headers
                                json={
                                    "amount" floatrow['amount'])
                                    "vip_days" introw['vip_days'])
                                    "label" strrow['label'])
                                    "enabled" boolrow['enabled'])
                                }
                            
                            if resstatus_code in [200 204]
                                success += 1
                        except Exception
                            pass
                    stsuccessf"✅ 已更新 {success} 個選項")
                    strerun)

            with c2
                if stbutton"🔄 重新載入" use_container_width=True)
                    strerun)

            stmarkdown"### 🗑️ 刪除選項")
            delete_id = stselectbox
                "選擇要刪除嘅選項"
                options=df['id']tolist)
                format_func=lambda x f"ID {x} - {df[df['id']==x]['label']values[0]} ${df[df['id']==x]['amount']values[0]})"
                key="delete_reward_select"
            
            if stbutton"❌ 確認刪除" type="secondary")
                try
                    requestsdelete
                        f"{SUPABASE_URL}/rest/v1/reward_configid=eq{delete_id}"
                        headers=headers
                    
                    stsuccessf"✅ 已刪除選項 ID {delete_id}")
                    strerun)
                except Exception as e
                    sterrorf"❌ 刪除失敗{e}")

        stdivider)
        stmarkdown"### ➕ 新增打賞選項")
        with stform"add_reward_form")
            c1 c2 c3 = stcolumns[2 2 3])
            with c1
                new_amount = stnumber_input"金額 $)" min_value=1 value=20 step=1)
            with c2
                new_days = stnumber_input"VIP 天數" min_value=1 value=3 step=1)
            with c3
                new_label = sttext_input"顯示標籤" value="☕ 一杯咖啡" max_chars=30)

            if stform_submit_button"➕ 新增選項" type="primary")
                try
                    payload = {
                        "amount" floatnew_amount)
                        "vip_days" intnew_days)
                        "label" new_label
                        "enabled" True
                    }
                    res = requestspost
                        f"{SUPABASE_URL}/rest/v1/reward_config"
                        headers=headers
                        json=payload
                    
                    if resstatus_code in [200 201 204]
                        stsuccessf"✅ 已新增{new_label} ${new_amount} → {new_days} 日 VIP)")
                        strerun)
                    else
                        sterrorf"❌ 新增失敗{restext}")
                except Exception as e
                    sterrorf"❌ 新增失敗{e}")

    stdivider)
    stmarkdownf"### ✅ 已批准{lenapproved)} 筆)")
    if not approvedempty
        display_cols = [c for c in ['username' 'amount' 'vip_days' 'rewarded_at'] if c in approvedcolumns]
        stdataframeapproved[display_cols] use_container_width=True hide_index=True)
    else
        stinfo"暫無已批准記錄。")

    if not rejectedempty
        stmarkdownf"### ❌ 已拒絕{lenrejected)} 筆)")
        display_cols = [c for c in ['username' 'amount' 'vip_days' 'rewarded_at'] if c in rejectedcolumns]
        stdataframerejected[display_cols] use_container_width=True hide_index=True)
def admin_user_activity)
    stsubheader"👤 用戶記錄")
    stcaption"記錄用戶嘅登入、預測、抽獎、購買、付款等活動。")

    log_file = "user_activity_logjson"

    if not ospathexistslog_file)
        stinfo"📭 暫無任何用戶活動記錄")
        return

    try
        with openlog_file 'r' encoding='utf-8') as f
            data = jsonloadf)
    except Exception as e
        sterrorf"❌ 讀取失敗{e}")
        return

    records = dataget"records" [])
    if not records
        stinfo"📭 暫無任何用戶活動記錄")
        return

    stmarkdown"### 📊 活動統計")
    df_all = pdDataFramerecords)
    c1 c2 c3 = stcolumns3)
    c1metric"📋 總記錄數" lendf_all))
    c2metric"👥 活躍用戶" df_all['username']nunique))
    today_str = datetimenow)strftime'%Y-%m-%d')
    c3metric"📅 今日記錄" lendf_all[df_all['time']strstartswithtoday_str)]))

    stdivider)
    stmarkdown"### 🔍 篩選")

    col1 col2 col3 = stcolumns3)
    with col1
        user_filter = stselectbox
            "選擇用戶"
            ["全部"] + sorteddf_all['username']unique)tolist))
            key="act_user_filter"
        
    with col2
        action_filter = stselectbox
            "活動類型"
            ["全部"] + sorteddf_all['action']unique)tolist))
            key="act_action_filter"
        
    with col3
        limit = stnumber_input"顯示最近幾多條" min_value=10 max_value=5000 value=100 step=10 key="act_limit")

    df_filtered = df_allcopy)
    if user_filter = "全部"
        df_filtered = df_filtered[df_filtered['username'] == user_filter]
    if action_filter = "全部"
        df_filtered = df_filtered[df_filtered['action'] == action_filter]

    df_filtered = df_filteredtailintlimit))iloc[-1]reset_indexdrop=True)
    df_filteredindex = df_filteredindex + 1

    stwritef"**顯示 {lendf_filtered)} 條記錄**")

    df_display = df_filtered[['time' 'username' 'action' 'detail']]copy)
    df_displaycolumns = ['時間' '用戶' '活動' '詳情']
    stdataframedf_display use_container_width=True)

    csv_data = df_displayto_csvindex=False)encode'utf-8-sig')
    stdownload_button
        label="📥 下載用戶記錄 CSV"
        data=csv_data
        file_name=f"user_activity_{datetimenow)strftime'%Y%m%d')}csv"
        mime="text/csv"
        use_container_width=True
        key="dl_user_activity"
    

def admin_monitoring)
    stsubheader"📡 系統監控")
    files = ['ALL_DATA_MERGEDcsv' 'HKCJ_FULL_YEAR_DATAcsv' 'usersjson'
             'system_configjson' 'accuracyjson' 'lottery_configjson' 'shop_configjson']
    for f in files
        if ospathexistsf)
            stsuccessf"✅ {f} {ospathgetsizef)/10241f} KB)")
        else
            sterrorf"❌ {f} 不存在")

def admin_content)
    stsubheader"📝 內容管理")
    content = load_jsonCONTENT_FILE)
    with stexpander"📢 發佈公告")
        t = sttext_input"標題" key="ct_title")
        x = sttext_area"內容" key="ct_txt")
        if stbutton"📤 發佈" key="ct_pub")
            if 'announcements' not in content
                content['announcements'] = []
            content['announcements']append{
                "id" lencontent['announcements']) + 1
                "title" t "content" x
                "created_at" datetimenow)strftime'%Y-%m-%d %H%M%S')
                "status" "active"
            })
            save_jsonCONTENT_FILE content)
            stsuccess"✅ 已發佈")
            strerun)

def admin_auto_maintenance)
    stsubheader"🤖 自動維護")
    if stbutton"🚀 執行維護" type="primary" use_container_width=True key="run_maint")
        users = load_users)
        today = datetimenow)
        exp = []
        for uid u in usersitems)
            if uget'group') == 'VIP' and uget'expiry_date')
                try
                    if pdto_datetimeu['expiry_date']) < today
                        u['group'] = 'free'
                        u['is_paid'] = False
                        u['predictions_limit'] = CONFIG["free_limit"]
                        expappenduid)
                except Exception
                    pass
        if exp
            save_usersusers)
        stsuccessf"✅ 維護完成處理 {lenexp)} 位過期用戶")

def admin_automation)
    stsubheader"🤖 自動化工具")
    stmarkdown"### ⚙️ 自動化排程")
    stinfo"以下自動化任務由 GitHub Actions 定時執行唔需要人手操作。")

    automation_data = [
        {"Workflow" "retrain_modelsyml" "執行時間" "每星期日 0800" "用途" "自動重新訓練 AI 模型"}
        {"Workflow" "update_resultsyml" "執行時間" "星期日/一/四 0800" "用途" "自動爬取賽果"}
        {"Workflow" "update_racecardyml" "執行時間" "星期三 1700、星期六日 1100" "用途" "自動爬取排位表"}
        {"Workflow" "update_ai_accuracyyml" "執行時間" "每日 2000" "用途" "自動更新 AI 命中率"}
    ]
    stdataframeautomation_data use_container_width=True hide_index=True)

    stmarkdown"---")
    stcaption"💡 提示如果想手動觸發可以喺 GitHub 倉庫嘅 Actions 頁面撳 Run workflow。")

def admin_security)
    stsubheader"🔐 安全與權限")
    
    import os json
    log_file = "admin_logjson"
    if ospathexistslog_file)
        try
            with openlog_file "r" encoding="utf-8") as f
                logs = jsonloadf)
            if logs
                stmarkdown"### 📋 管理員操作日誌")
                df_logs = pdDataFramelogs)
                stdataframedf_logs use_container_width=True hide_index=True)
            else
                stinfo"📭 暫無操作記錄。")
        except Exception as e
            stwarningf"讀取日誌時出錯{e}")
    else
        stinfo"📭 暫無日誌檔案。")
def admin_pool_config)
    stsubheader"🎯 彩池設定")
    stcaption"可以獨立開關每個彩池同設定最低會員級別。")

    config = load_system_config)
    pool_config = configget'pool_config' {})

    # 如果未有彩池設定用預設值
    if not pool_config
        pool_config = {
            "win" {"enabled" True "required_group" "free" "label" "獨贏"}
            "place" {"enabled" True "required_group" "free" "label" "位置"}
            "quinella" {"enabled" True "required_group" "free" "label" "連贏"}
            "quinella_place" {"enabled" True "required_group" "free" "label" "位置Q"}
            "tierce" {"enabled" True "required_group" "paid" "label" "三重彩"}
            "trio" {"enabled" True "required_group" "paid" "label" "單T"}
            "quartet" {"enabled" True "required_group" "VIP" "label" "四重彩"}
            "exacta" {"enabled" True "required_group" "VIP" "label" "二重彩"}
            "first4" {"enabled" True "required_group" "VIP" "label" "四連環"}
            "double" {"enabled" True "required_group" "VIP" "label" "孖寶"}
            "treble" {"enabled" True "required_group" "VIP" "label" "三寶"}
            "six_up" {"enabled" True "required_group" "VIP" "label" "六環彩"}
        }

    stmarkdown"### 📊 彩池列表")

    # 顯示表格式設定
    updated_config = {}

    for key cfg in pool_configitems)
        col1 col2 col3 = stcolumns[2 1 2])

        with col1
            stmarkdownf"**{cfgget'label' key)}**")
            stcaptionf"`{key}`")

        with col2
            enabled = stcheckbox
                "啟用"
                value=cfgget'enabled' True)
                key=f"pool_enabled_{key}"
            

        with col3
            group_options = ['free' 'paid' 'VIP']
            group_labels = {
                'free' '🆓 普通用戶'
                'paid' '💰 付費用戶日/月)'
                'VIP' '👑 VIP / 季費 / 年費'
            }
            current_group = cfgget'required_group' 'free')
            if current_group not in group_options
                current_group = 'free'
            required_group = stselectbox
                "最低會員級別"
                group_options
                index=group_optionsindexcurrent_group)
                format_func=lambda x group_labels[x]
                key=f"pool_group_{key}"
            

        updated_config[key] = {
            "enabled" enabled
            "required_group" required_group
            "label" cfgget'label' key)
        }

        stdivider)

    if stbutton"💾 儲存彩池設定" type="primary" use_container_width=True key="save_pool_cfg")
        config['pool_config'] = updated_config
        if save_system_configconfig)
            stsuccess"✅ 彩池設定已儲存")
            timesleep1)
            strerun)
        else
            sterror"❌ 儲存失敗")


def _get_pool_config_default)
    """回傳預設彩池設定"""
    return {
        "win" {"enabled" True "required_group" "free" "label" "獨贏"}
        "place" {"enabled" True "required_group" "free" "label" "位置"}
        "quinella" {"enabled" True "required_group" "free" "label" "連贏"}
        "quinella_place" {"enabled" True "required_group" "free" "label" "位置Q"}
        "tierce" {"enabled" True "required_group" "paid" "label" "三重彩"}
        "trio" {"enabled" True "required_group" "paid" "label" "單T"}
        "quartet" {"enabled" True "required_group" "VIP" "label" "四重彩"}
        "exacta" {"enabled" True "required_group" "VIP" "label" "二重彩"}
        "first4" {"enabled" True "required_group" "VIP" "label" "四連環"}
        "double" {"enabled" True "required_group" "VIP" "label" "孖寶"}
        "treble" {"enabled" True "required_group" "VIP" "label" "三寶"}
        "six_up" {"enabled" True "required_group" "VIP" "label" "六環彩"}
    }

def admin_system_settings)
    stsubheader"⚙️ 系統設定")
    config = load_system_config)
    c1 c2 = stcolumns2)
    with c1
        er = stcheckbox"開放註冊" value=configget"enable_registration" True) key="s_er")
        ep = stcheckbox"啟用付款" value=configget"enable_payment" True) key="s_ep")
        ea = stcheckbox"啟用後台" value=configget"enable_admin" True) key="s_ea")
        el = stcheckbox"啟用抽獎" value=configget"enable_lottery" True) key="s_el")
        es = stcheckbox"啟用商城" value=configget"enable_shop" True) key="s_es")
        pd_ = stnumber_input"日費" min_value=0 value=_safe_intconfigget"price_day" 18) 18) step=1 key="s_pd")
        pm = stnumber_input"月費" min_value=0 value=_safe_intconfigget"price_month" 128) 128) step=1 key="s_pm")
        pq = stnumber_input"季費" min_value=0 value=_safe_intconfigget"price_quarter" 328) 328) step=1 key="s_pq")
    with c2
        fl = stnumber_input"免費預測次數" min_value=0 value=_safe_intconfigget"free_limit" 2) 2) step=1 key="s_fl")
        cur = sttext_input"貨幣單位" value=configget"currency" "HKD") key="s_cur")
        ap = sttext_input"管理員密碼" value=configget"admin_password" "") type="password" key="s_ap")
        vc = stcheckbox"啟用虛擬幣" value=configget"virtual_coin_enabled" True) key="s_vc")
        dvc = stnumber_input"每日派幣" min_value=0 value=_safe_intconfigget"daily_virtual_coin" 1000) 1000) step=100 key="s_dvc")
    if stbutton"💾 儲存設定" type="primary" key="save_sys")
        merged = dictconfig)
        mergedupdate{
            "enable_registration" er "enable_payment" ep "enable_admin" ea
            "enable_lottery" el "enable_shop" es
            "price_day" pd_ "price_month" pm "price_quarter" pq
            "free_limit" fl "currency" cur
            "admin_password" ap "virtual_coin_enabled" vc
            "daily_virtual_coin" dvc
        })
        if save_system_configmerged)
            stsuccess"✅ 已儲存")
            timesleep1)
            strerun)
        else
            sterror"❌ 儲存失敗")

def admin_page)
    if 'admin_authenticated' not in stsession_state
        stsession_stateadmin_authenticated = False

    if not stsession_stateadmin_authenticated
        sttitle"🔐 後台管理 - 身份驗證")
        pw = sttext_input"管理員密碼" type="password" key="adm_pw")
        c1 c2 = stcolumns2)
        with c1
            if stbutton"🔓 解鎖後台" type="primary" key="unlock")
                if pw == CONFIG["admin_password"]
                    stsession_stateadmin_authenticated = True
                    stsession_stateadmin_username = "admin"
                    strerun)
                else
                    sterror"❌ 密碼錯誤")
        with c2
            if stbutton"⬅️ 返回主頁" key="back_home")
                stsession_stateshow_admin = False
                strerun)
        return

    sttitle"🔐 後台管理")
    stinfof"👤 管理員{stsession_stateget'admin_username' 'admin')}")
    if stbutton"🚪 登出後台" key="logout_adm")
        stsession_stateadmin_authenticated = False
        stsession_stateshow_admin = False
        strerun)
    stdivider)

    tabs_def = [
        "📊 儀表板" admin_dashboard)
        "👥 用戶管理" admin_user_management)
        "📥 下載中心" admin_downloads)
        "📊 次數管理" admin_manage_predictions)
        "📊 數據分析" admin_analytics)
        "🏇 馬匹排行榜" admin_horse_ranking)
        "👨‍🏫 騎師排行榜" admin_jockey_ranking)
        "👨‍🏫 練馬師排行榜" admin_trainer_ranking)
        "📊 場地/路程分析" admin_course_analysis)
        "📅 每月報告" admin_monthly_report)
        "💰 財務" admin_finance)
        "🎟️ 優惠碼" admin_promo_codes)
        "📈 預測監控" admin_accuracy_monitor)
        "⏰ 訂閱管理" admin_subscription)
        "📤 付款審核" admin_payment_review)      # 👈 刪除前面個 # 號
        "❤️ 打賞管理" admin_reward_management)   # 👈 加呢行
        "📡 監控" admin_monitoring)
        "📝 內容" admin_content)
        "🤖 自動維護" admin_auto_maintenance)
        "🤖 自動化" admin_automation)
        "🔐 安全" admin_security)        
        "👤 用戶記錄" admin_user_activity)
        "🎰 抽獎設定" admin_lottery_config)
        "🛒 商城設定" admin_shop_config)
        "🎯 彩池設定" admin_pool_config)
        "⚙️ 系統設定" admin_system_settings)
    ]

    tabs = sttabs[t[0] for t in tabs_def])
    for i name fn) in enumeratetabs_def)
        with tabs[i]
            try
                fn)
            except Exception as e
                sterrorf"⚠️ 呢個分頁載入失敗{e}")
                import traceback
                stcodetracebackformat_exc))

def display_race_calendar)
    try
        hk_tz = pytztimezone"Asia/Hong_Kong")
        now_hk = datetimenowhk_tz)
        wd = now_hkweekday)
        target = None
        rn = ""
        vn = ""

        if wd == 2
            rt = now_hkreplacehour=19 minute=15 second=0 microsecond=0)
            if now_hk < rt
                target rn vn = rt "跑馬地夜馬" "HV"
        elif wd == 6
            rt = now_hkreplacehour=12 minute=30 second=0 microsecond=0)
            if now_hk < rt
                target rn vn = rt "沙田日馬" "ST"

        if target is None
            for i in range1 8)
                fut = now_hk + timedeltadays=i)
                if futweekday) == 2
                    target = futreplacehour=19 minute=15 second=0 microsecond=0)
                    rn vn = "跑馬地夜馬" "HV"
                    break
                elif futweekday) == 6
                    target = futreplacehour=12 minute=30 second=0 microsecond=0)
                    rn vn = "沙田日馬" "ST"
                    break

        if not target
            stinfo"📅 暫無未來賽事資料")
            return

        ts = inttarget - now_hk)total_seconds))
        if ts <= 0
            stsuccessf"🏇 **{rn}** 已經開始")
            return

        d = ts // 86400
        h = ts % 86400) // 3600
        m = ts % 3600) // 60
        s = ts % 60
        is_today = targetdate) == now_hkdate))
        bg = "linear-gradient135deg #ff6b6b #ee5a24)" if is_today else "linear-gradient135deg #667eea #764ba2)"
        title = f"🔥 今日有賽事{rn}" if is_today else f"⏰ 距離下場賽事{rn}"

        stmarkdownf"""
        <div style="background{bg}padding20px 24pxborder-radius16pxcolorwhitebox-shadow0 6px 20px rgba102126234035)margin-bottom16px">
            <div style="font-size15pxopacity09margin-bottom8px">{title}</div>
            <div style="displayflexgap16pxalign-itemsbaselineflex-wrapwrap">
                <div style="text-aligncenter"><div style="font-size42pxfont-weight800">{d}</div><div style="font-size12pxopacity08">日</div></div>
                <div style="text-aligncenter"><div style="font-size42pxfont-weight800">{h02d}</div><div style="font-size12pxopacity08">時</div></div>
                <div style="text-aligncenter"><div style="font-size42pxfont-weight800">{m02d}</div><div style="font-size12pxopacity08">分</div></div>
                <div style="text-aligncenter"><div style="font-size42pxfont-weight800">{s02d}</div><div style="font-size12pxopacity08">秒</div></div>
            </div>
            <div style="font-size13pxopacity085margin-top10px">📍 {targetstrftime'%Y年%m月%d日 %H%M')} · {vn}</div>
        </div>
        """ unsafe_allow_html=True)
    except Exception as e
        sterrorf"⚠️ 倒數計時器失敗{e}")

def login_page)
    sttitle"🔐 登入 / 註冊")
    c1 c2 = stcolumns2)
    with c1
        if stbutton"🔑 登入" use_container_width=True key="pg_login")
            stsession_statepage_mode = "login"
    with c2
        if stbutton"📝 註冊" use_container_width=True key="pg_reg")
            stsession_statepage_mode = "register"

    mode = stsession_stateget"page_mode" "login")

    if mode == "login"
        with stform"login_form")
            u = sttext_input"用戶名稱" key="login_user")
            p = sttext_input"密碼" type="password" key="login_pass")
            if stform_submit_button"登入")
                user = authenticateu p)
                if user
                    stsession_statelogged_in = True
                    stsession_stateusername = u
                    log_user_activityu "登入" "登入成功")
                    stsession_staterole = userget'group' 'free')
                    strerun)
                else
                    sterror"❌ 用戶名或密碼錯誤")
    else
        stsubheader"📝 註冊新帳號")
        with stform"register_form")
            new_user = sttext_input"用戶名稱最少 3 個字)" key="reg_user")
            phone = sttext_input"手機號碼可選)" key="reg_phone")
            new_pass = sttext_input"密碼" type="password" key="reg_pass")
            new_pass2 = sttext_input"確認密碼" type="password" key="reg_pass2")

            # ===== 邀請碼 =====
            if CONFIGget"enable_invite_reward" True)
                invite_code_input = sttext_input
                    "邀請碼如有)"
                    key="reg_invite_code"
                    placeholder="輸入朋友嘅邀請碼雙方都會獲得獎勵"
                
            else
                invite_code_input = None

            agree_terms = stcheckbox"✅ 我已閱讀並同意服務條款" key="agree_terms")
            submitted = stform_submit_button"註冊")

            if submitted
                if lennew_user) < 3
                    sterror"❌ 用戶名稱至少 3 個字")
                elif new_pass = new_pass2
                    sterror"❌ 密碼不一致")
                elif lennew_pass) < 4
                    sterror"❌ 密碼至少 4 個字")
                elif not agree_terms
                    sterror"❌ 請同意服務條款")
                else
                    users = load_users)

                    # ===== 驗證邀請碼 =====
                    invited_by = None
                    if CONFIGget"enable_invite_reward" True) and invite_code_input
                        invite_code_input = invite_code_inputstrip)upper)
                        for uid u in usersitems)
                            if uget'invite_code' '')upper) == invite_code_input
                                invited_by = uid
                                break
                        if not invited_by
                            sterror"❌ 邀請碼無效請確認後再試")
                            ststop)

                    if new_user in users
                        sterror"❌ 用戶名稱已被使用")
                    else
                        # ===== 建立新用戶 =====
                        users[new_user] = {
                            'password' new_pass
                            'phone' phone
                            'is_paid' False
                            'paid_date' None
                            'expiry_date' None
                            'free_usage' 0
                            'total_usage' 0
                            'created_at' datetimenow)strftime'%Y-%m-%d %H%M%S')
                            'note' ''
                            'group' 'free'
                            'plan' None
                            'predictions_limit' CONFIGget"free_limit" 2)
                            'history' []
                            'terms_agreed' datetimenow)isoformat)
                            'invite_code' new_userupper) + strrandomrandint100 999))
                            'invited_by' invited_by
                            'invite_rewards' 0
                            'invite_count' 0
                            'referred_users' []  # 直接下線列表
                            'level' '🥉 銅牌會員'
                            'exp' 0
                            'badges' []
                            'virtual_balance' CONFIGget'daily_virtual_coin' 1000)
                            'last_claim_date' ''
                            'bets' []
                            'last_lottery_date' ''
                        }

                        # ===== 多級獎勵回溯 =====
                        if invited_by and CONFIGget"enable_invite_reward" True)
                            rewards = CONFIGget"invite_rewards" {"level1" 5 "level2" 2 "level3" 1})

                            # Level 1直接邀請人
                            inviter = usersgetinvited_by)
                            if inviter
                                bonus1 = rewardsget"level1" 5)
                                if inviterget'predictions_limit' 0) = -1
                                    inviter['predictions_limit'] = inviterget'predictions_limit' 0) + bonus1
                                inviter['invite_count'] = inviterget'invite_count' 0) + 1
                                inviter['invite_rewards'] = inviterget'invite_rewards' 0) + bonus1
                                if 'referred_users' not in inviter
                                    inviter['referred_users'] = []
                                if new_user not in inviter['referred_users']
                                    inviter['referred_users']appendnew_user)

                                # 新用戶自己都獲得獎勵
                                users[new_user]['predictions_limit'] += rewardsget"level1" 5)
                                users[new_user]['invite_rewards'] += rewardsget"level1" 5)

                                # Level 2上線邀請人嘅邀請人)
                                level2_user = inviterget'invited_by')
                                if level2_user and level2_user in users
                                    bonus2 = rewardsget"level2" 2)
                                    if users[level2_user]get'predictions_limit' 0) = -1
                                        users[level2_user]['predictions_limit'] += bonus2
                                    users[level2_user]['invite_rewards'] = users[level2_user]get'invite_rewards' 0) + bonus2

                                    # Level 3上上線
                                    level3_user = users[level2_user]get'invited_by')
                                    if level3_user and level3_user in users
                                        bonus3 = rewardsget"level3" 1)
                                        if users[level3_user]get'predictions_limit' 0) = -1
                                            users[level3_user]['predictions_limit'] += bonus3
                                        users[level3_user]['invite_rewards'] = users[level3_user]get'invite_rewards' 0) + bonus3

                        save_usersusers)
                        log_user_activitynew_user "註冊" f"邀請人{invited_by or '無'}")
                        stsuccessf"✅ 註冊成功你獲得 {CONFIGget'invite_rewards' {})get'level1' 5)} 次額外預測獎勵")
                        stsession_statepage_mode = "login"
                        strerun)

def main)
    defaults = {
        'logged_in' False 'username' None 'role' 'free'
        'show_admin' False 'show_lottery' False 'show_shop' False
    }
    for k v in defaultsitems)
        if k not in stsession_state
            stsession_state[k] = v

    if CONFIG["enable_registration"] and not stsession_statelogged_in
        login_page)
        return

    if stsession_stateshow_admin and CONFIG["enable_admin"]
        admin_page)
        return


    c1 c2 c3 c4 c5 = stcolumns[4 1 1 1 1])
    with c1
        sttitle"🏇 賽馬預測系統")
        stmarkdown"AI 驅動・即時預測・彩池推薦")
        stcaptionf"{datetimenow)strftime'%Y年%m月%d日')}")
    with c2
        if CONFIG["enable_admin"] and stsession_stateget"role") == "super_admin"
            if stbutton"🔐 後台" use_container_width=True key="go_admin")
                stsession_stateshow_admin = True
                strerun)
    with c3
        # 👇 新加嘅「常見問題」按鈕同後台平排
        if stbutton"❓ 常見問題" use_container_width=True key="faq_btn")
            stswitch_page"pages/FAQpy")
    with c4
            username = stsession_stateusername
            users = load_users)
            user_data = usersgetusername {})
            virtual_balance = user_dataget'virtual_balance' 0)
            group = user_dataget'group' 'free')
            level = user_dataget'level' '🥉 銅牌會員')

            with stpopover"👤 個人中心" use_container_width=True)
                # ===== 推薦記錄 =====
                with stexpander"👥 我的推薦記錄" expanded=False)
                    users_all = load_users)
                    me = users_allgetstsession_stateget'username' '') {})
                    referred = meget'referred_users' [])
                    invite_code = meget'invite_code' '')
                    invite_count = meget'invite_count' 0)
                    invite_rewards = meget'invite_rewards' 0)

                    stmarkdownf"**你嘅邀請碼**`{invite_code}`")
                    stcaptionf"已成功邀請 **{invite_count}** 位朋友共獲得 **{invite_rewards}** 次額外預測")

                    if referred
                        stmarkdown"**直接下線列表**")
                        df_ref = pdDataFrame{
                            "用戶" referred
                            "註冊時間" [users_allgetu {})get'created_at' '') for u in referred]
                        })
                        stdataframedf_ref use_container_width=True hide_index=True)
                    else
                        stinfo"📭 暫時未邀請過朋友")
                stmarkdownf"### 👤 {username}")
                stmarkdownf"**級別**{groupupper)}　|　**等級**{level}")
                stmetric"💰 虛擬幣結餘" f"${virtual_balance0f}")

                stdivider)

                # 更改密碼
                with stexpander"🔑 更改密碼" expanded=False)
                    old_pw = sttext_input"舊密碼" type="password" key="pc_old_pw")
                    new_pw = sttext_input"新密碼最少 4 字)" type="password" key="pc_new_pw")
                    confirm_pw = sttext_input"確認新密碼" type="password" key="pc_confirm_pw")
                    if stbutton"✅ 確認更改" key="pc_change_pw" use_container_width=True)
                        users2 = load_users)
                        if username not in users2
                            sterror"❌ 用戶不存在")
                        elif users2[username]get'password') = old_pw
                            sterror"❌ 舊密碼不正確")
                        elif lennew_pw) < 4
                            sterror"❌ 新密碼最少 4 個字")
                        elif new_pw = confirm_pw
                            sterror"❌ 兩次密碼不一致")
                        else
                            users2[username]['password'] = new_pw
                            if save_usersusers2)
                                stsuccess"✅ 密碼已更改")
                            else
                                sterror"❌ 儲存失敗")

                # 預測記錄
                with stexpander"📜 預測記錄" expanded=False)
                    history = user_dataget'history' [])
                    if not history
                        stinfo"📭 暫無預測記錄")
                    else
                        total = lenhistory)
                        hits = sum1 for h in history if hget'is_hit') is True)
                        hit_rate = hits / total if total > 0 else 0
                        hc1 hc2 hc3 = stcolumns3)
                        hc1metric"總預測" total)
                        hc2metric"命中" hits)
                        hc3metric"命中率" f"{hit_rate1%}")
                        stdivider)
                        df_hist = pdDataFramehistory[-20][-1])
                        cols = [c for c in ['date' 'race' 'horse' 'is_hit'] if c in df_histcolumns]
                        if cols
                            df_show = df_hist[cols]copy)
                            df_showrenamecolumns={
                                'date' '日期' 'race' '場次'
                                'horse' '預測馬' 'is_hit' '結果'
                            } inplace=True)
                            if '結果' in df_showcolumns
                                df_show['結果'] = df_show['結果']apply
                                    lambda x '✅' if x is True else '❌' if x is False else '⏳')
                                
                            stdataframedf_show use_container_width=True hide_index=True)
    with c5
        if stsession_stateget'logged_in' False)
            if stbutton"🚪 登出" use_container_width=True key="logout_main")
                for k in ['logged_in' 'username' 'role']
                    if k in stsession_state
                        del stsession_state[k]
                strerun)

    stmarkdown"---")
    
    # =========================================================================
    # 👇👇👇 重要倒數卡片⏰ 距離下場賽事)一定要放喺呢度 👇👇👇
    # 你必須將包含「⏰ 距離下場賽事」嘅代碼原封不動咁貼喺呢度。
    # 記住呢度嘅代碼前面「唔可以有 with c1 或者 with c2 嘅縮排」佢一定要係最左邊或者同上面 c1 c2 對齊)。
    # 咁樣佢就會自動佔滿成行變返做「成條橫額」
    # =========================================================================
    
    # 貼上你原本倒數卡片嘅代碼例如)
    # stmarkdown"⏰ 距離下場賽事跑馬地夜馬")
    # stmarkdown"## 2 00 11")
    # 
    
    display_race_calendar)
    stmarkdown"---")

    if stsession_statelogged_in
        ca cb = stcolumns2)
        with ca
            if CONFIGget"enable_lottery" True)
                if stbutton"🎰 每日抽獎" use_container_width=True key="go_lot")
                    stsession_stateshow_lottery = True
                    stsession_stateshow_shop = False
        with cb
            if CONFIGget"enable_shop" True)
                if stbutton"🛒 虛擬商城" use_container_width=True key="go_shp")
                    stsession_stateshow_shop = True
                    stsession_stateshow_lottery = False

        if stsession_stateget'show_lottery')
            show_lottery_interfacestsession_stateusername)
            if stbutton"⬅️ 返回" key="bl")
                stsession_stateshow_lottery = False
                strerun)

        if stsession_stateget'show_shop')
            show_shop_interfacestsession_stateusername)
            if stbutton"⬅️ 返回" key="bs")
                stsession_stateshow_shop = False
                strerun)

    stdivider)
    stsubheader"🎯 賽事預測")

    # ============================================================
    # 🔧 管理員專用一鍵預測所有場次
    # ============================================================
    if stsession_stateget'role') == 'super_admin'
        with stexpander"🛠️ 管理員工具一鍵預測所有場次")
            stcaption"⚠️ 只限管理員使用會自動預測指定日期嘅所有場次。")

            col_date col_btn col_status = stcolumns[2 1 2])

            with col_date
                selected_date = stdate_input
                    "📅 選擇日期"
                    value=pdto_datetime"2026-09-06")
                    key="batch_pred_date"
                

            with col_btn
                stwrite"")
                run_batch = stbutton
                    "🔮 一鍵預測"
                    use_container_width=True
                    key="batch_predict_btn_v3"
                

            with col_status
                stwrite"")
                date_str = selected_datestrftime"%Y-%m-%d")
                try
                    rc_df = pdread_csv"racecard_uploadedcsv" encoding='utf-8-sig')
                    rc_df = _repair_racecardrc_df)
                    rc_df = rc_dfloc[ ~rc_dfcolumnsduplicated)]
                    rename_map = {'馬名' 'horse_name' '檔位' 'draw' '場次' 'race_no'
                                  '比賽日期' 'race_date' '騎師' 'jockey' '練馬師' 'trainer'
                                  '負磅' 'weight' '馬號' 'horse_id' '賠率' 'win_odds'}
                    existing = [c for c in rename_map if c in rc_dfcolumns]
                    if existing
                        rc_dfrenamecolumns={c rename_map[c] for c in existing} inplace=True)
                    rc_df = rc_dfloc[ ~rc_dfcolumnsduplicated)]
                    if isinstancerc_df['race_date'] pdDataFrame)
                        rc_df['race_date'] = rc_df['race_date']iloc[ 0]
                    rc_df['race_date'] = pdto_datetimerc_df['race_date'] errors='coerce')
                    rc_df = rc_dfdropnasubset=['race_date'])
                    rc_df['race_date_str'] = rc_df['race_date']dtstrftime'%Y-%m-%d')
                    rc_df['race_no'] = pdto_numericrc_df['race_no'] errors='coerce')fillna0)astypeint)
                    day_races = sortedrc_df[rc_df['race_date_str'] == date_str]['race_no']unique))
                    if not day_races
                        stwarningf"⚠️ {date_str} 冇數據")
                    else
                        stsuccessf"✅ 準備就緒共 {lenday_races)} 場)")
                except Exception as e
                    sterrorf"讀取失敗{e}")

            # ===== 一鍵預測執行 =====
            if run_batch
                date_str = selected_datestrftime"%Y-%m-%d")
                stinfof"🚀 開始預測 {date_str} 所有場次")

                try
                    rc_df = pdread_csv"racecard_uploadedcsv" encoding='utf-8-sig')
                    rc_df = _repair_racecardrc_df)
                    rc_df = rc_dfloc[ ~rc_dfcolumnsduplicated)]
                    rename_map = {'馬名' 'horse_name' '檔位' 'draw' '場次' 'race_no'
                                  '比賽日期' 'race_date' '騎師' 'jockey' '練馬師' 'trainer'
                                  '負磅' 'weight' '馬號' 'horse_id' '賠率' 'win_odds'}
                    existing = [c for c in rename_map if c in rc_dfcolumns]
                    if existing
                        rc_dfrenamecolumns={c rename_map[c] for c in existing} inplace=True)
                    rc_df = rc_dfloc[ ~rc_dfcolumnsduplicated)]
                    if isinstancerc_df['race_date'] pdDataFrame)
                        rc_df['race_date'] = rc_df['race_date']iloc[ 0]
                    rc_df['race_date'] = pdto_datetimerc_df['race_date'] errors='coerce')
                    rc_df = rc_dfdropnasubset=['race_date'])
                    rc_df['race_date_str'] = rc_df['race_date']dtstrftime'%Y-%m-%d')
                    rc_df['race_no'] = pdto_numericrc_df['race_no'] errors='coerce')fillna0)astypeint)
                    day_races = sortedrc_df[rc_df['race_date_str'] == date_str]['race_no']unique))

                    if not day_races
                        stwarningf"⚠️ {date_str} 冇任何場次數據")
                    else
                        stinfof"📋 準備預測 {lenday_races)} 場{day_races}")
                        progress = stprogress0)
                        status = stempty)
                        success_count = 0
                        fail_count = 0
                        all_results = {}

                        for i rn in enumerateday_races)
                            statustextf"⏳ 預測第 {rn} 場中{i+1}/{lenday_races)})")
                            try
                                result pool = run_predictiondate_str intrn))
                                if result is not None and not resultempty
                                    all_results[intrn)] = result
                                    success_count += 1
                                else
                                    fail_count += 1
                            except Exception as e
                                fail_count += 1
                            progressprogressi + 1) / lenday_races))

                        statustext"✅ 完成")
                        stsuccessf"✅ 成功 {success_count} 場失敗 {fail_count} 場")

                        stsession_state['batch_all_results'] = all_results
                        stsession_state['batch_date_str'] = date_str
                except Exception as e
                    sterrorf"執行失敗{e}")

            # ===== 讀取 session_state 嘅結果 =====
            all_results = stsession_stateget'batch_all_results' {})
            date_str_saved = stsession_stateget'batch_date_str' '')

            if all_results
                stdivider)
                stsubheaderf"🎯 {date_str_saved} 跨場彩池推薦")

                race_list = sortedall_resultskeys))

                stmarkdown"#### 🎯 孖寶連續 2 場)")
                if lenrace_list) >= 2
                    double_start = stselectbox
                        "孖寶起始場次" race_list index=None
                        placeholder="請選擇孖寶起始場次"
                        key="double_start_selector"
                    
                    if double_start is not None
                        d_idx = race_listindexdouble_start)
                        d_races = race_list[d_idxd_idx + 2]
                        if lend_races) >= 2
                            d1 = all_results[d_races[0]]iloc[0]['horse_name']
                            d2 = all_results[d_races[1]]iloc[0]['horse_name']
                            stsuccessf"**【孖寶】第 {d_races[0]}-{d_races[1]} 場**{d1} + {d2}")
                        else
                            stwarningf"⚠️ 由第 {double_start} 場開始唔夠 2 場數據")
                else
                    stwarning"⚠️ 唔夠 2 場賽事冇孖寶")

                stdivider)

                stmarkdown"#### 🎯 三寶連續 3 場)")
                if lenrace_list) >= 3
                    treble_start = stselectbox
                        "三寶起始場次" race_list index=None
                        placeholder="請選擇三寶起始場次"
                        key="treble_start_selector"
                    
                    if treble_start is not None
                        t_idx = race_listindextreble_start)
                        t_races = race_list[t_idxt_idx + 3]
                        if lent_races) >= 3
                            t1 = all_results[t_races[0]]iloc[0]['horse_name']
                            t2 = all_results[t_races[1]]iloc[0]['horse_name']
                            t3 = all_results[t_races[2]]iloc[0]['horse_name']
                            stsuccessf"**【三寶】第 {t_races[0]}-{t_races[2]} 場**{t1} + {t2} + {t3}")
                        else
                            stwarningf"⚠️ 由第 {treble_start} 場開始唔夠 3 場數據")
                else
                    stwarning"⚠️ 唔夠 3 場賽事冇三寶")

                stdivider)

                stmarkdown"#### 🎯 六環彩連續 6 場)")
                if lenrace_list) >= 6
                    six_up_start = stselectbox
                        "六環彩起始場次" race_list index=None
                        placeholder="請選擇六環彩起始場次"
                        key="six_up_start_selector"
                    
                    if six_up_start is not None
                        s_idx = race_listindexsix_up_start)
                        six_up_races = race_list[s_idxs_idx + 6]
                        if lensix_up_races) >= 6
                            horses = [all_results[rn]iloc[0]['horse_name'] for rn in six_up_races]
                            stsuccessf"**【六環彩】第 {six_up_races[0]}-{six_up_races[-1]} 場**{' + 'joinhorses)}")
                        else
                            stwarningf"⚠️ 由第 {six_up_start} 場開始唔夠 6 場數據只有 {lensix_up_races)} 場)")
                else
                    stwarning"⚠️ 唔夠 6 場賽事冇六環彩")

                stdivider)

                stsubheader"📊 各場預測結果")
                cols_per_row = 3
                for i in range0 lenrace_list) cols_per_row)
                    cols = stcolumnscols_per_row)
                    for j col in enumeratecols)
                        idx = i + j
                        if idx >= lenrace_list)
                            break
                        rn = race_list[idx]
                        with col
                            stmarkdownf"**🏇 第 {rn} 場**")
                            df = all_results[rn]copy)
                            rename_map = {}
                            if '馬名' in dfcolumns
                                rename_map['馬名'] = '馬名'
                            elif 'horse_name' in dfcolumns
                                rename_map['horse_name'] = '馬名'
                            if '檔位' in dfcolumns
                                rename_map['檔位'] = '檔位'
                            elif 'draw' in dfcolumns
                                rename_map['draw'] = '檔位'
                            if '賠率' in dfcolumns
                                rename_map['賠率'] = '賠率'
                            elif 'win_odds' in dfcolumns
                                rename_map['win_odds'] = '賠率'
                            if '騎師' in dfcolumns
                                rename_map['騎師'] = '騎師'
                            elif 'jockey' in dfcolumns
                                rename_map['jockey'] = '騎師'
                            if '練馬師' in dfcolumns
                                rename_map['練馬師'] = '練馬師'
                            elif 'trainer' in dfcolumns
                                rename_map['trainer'] = '練馬師'
                            if '預測勝率' in dfcolumns
                                rename_map['預測勝率'] = '勝率'
                            elif '勝率' in dfcolumns
                                rename_map['勝率'] = '勝率'
                            valid_cols = [c for c in rename_mapkeys) if c in dfcolumns]
                            df_show = df[valid_cols]head3)copy)
                            df_showrenamecolumns=rename_map inplace=True)
                            if '勝率' in df_showcolumns
                                df_show['勝率'] = df_show['勝率']applylambda x f"{x1%}")
                            stdataframedf_show use_container_width=True hide_index=True)

    # ============================================================
    # 🚀 單場預測區塊按鈕版)
    # ============================================================
    cd cbtn = stcolumns[3 1])
    with cd
        date = stdate_input"📅 日期" value=pdto_datetime"2026-09-06") key="pd_date")
    with cbtn
        stwrite"")
        run_predict = stbutton"🚀 執行預測" type="primary" use_container_width=True key="pd_btn")

    stmarkdown"**🏇 選擇場次**")
    if 'selected_race' not in stsession_state
        stsession_stateselected_race = 1

    race_cols = stcolumns6)
    for i in range11)
        race_num = i + 1
        col_idx = i % 6
        with race_cols[col_idx]
            if stsession_stateselected_race == race_num
                if stbuttonf"**{race_num}**" key=f"race_btn_{race_num}" use_container_width=True type="primary")
                    stsession_stateselected_race = race_num
            else
                if stbuttonf"{race_num}" key=f"race_btn_{race_num}" use_container_width=True)
                    stsession_stateselected_race = race_num
        if col_idx == 5 and i < 10
            race_cols = stcolumns6)

    race_no = stsession_stateselected_race
    stcaptionf"已選擇第 {race_no} 場")

    if run_predict
        with stspinner"預測中")
            result pool = run_predictiondatestrftime"%Y-%m-%d") race_no)
            if result is not None and not resultempty
                stsession_state['last_prediction'] = result
                stsession_state['last_pool'] = pool

    if 'last_prediction' in stsession_state and stsession_state['last_prediction'] is not None
        stsuccess"✅ 預測完成")
        if stsession_stateget'last_pool')
            stinfostsession_state['last_pool'])
        stdataframestsession_state['last_prediction'] use_container_width=True)

    # ============================================================
    # 📊 AI 預測表現 & 賽果對比獨立顯示唔使預測)
    # ============================================================
    if stsession_stateget'logged_in' False)
        stdivider)
        with stexpander"📊 AI 預測表現 & 賽果對比 點擊展開)" expanded=False)
            try
                from database import load_predictions
                ai_data = load_predictions)

                if not ai_data
                    stwarning"⚠️ 尚未有任何預測紀錄請先執行預測")
                else
                    stinfof"✅ 成功讀取 {lenai_data)} 個預測紀錄")
                    
                    result_file = "race_results_cleancsv"
                    df_results = pdDataFrame)
                    if ospathexistsresult_file)
                        try
                            df_results = pdread_csvresult_file encoding='utf-8-sig')
                            required_cols = ['race_date' 'race_no' 'horse_name' 'finish_position']
                            if allcol in df_resultscolumns for col in required_cols)
                                df_results['horse_name'] = df_results['horse_name']astypestr)strstrip)
                                df_results['finish_position'] = pdto_numericdf_results['finish_position'] errors='coerce')
                                df_results['race_no'] = pdto_numericdf_results['race_no'] errors='coerce')
                                df_results = df_resultsdropnasubset=['race_no'])
                                df_results['race_no'] = df_results['race_no']astypeint)
                                df_results['race_date'] = pdto_datetimedf_results['race_date'] errors='coerce')
                            else
                                sterror"❌ 賽果檔案缺少必要欄位")
                                df_results = pdDataFrame)
                        except Exception as e
                            sterrorf"❌ 讀取賽果失敗{e}")
                            df_results = pdDataFrame)
                    else
                        stwarning"⚠️ 找不到賽果檔案 race_results_cleancsv")

                    pred_list = []
                    for key value in ai_dataitems)
                        if '_' not in key continue
                        parts = keysplit'_')
                        if lenparts) = 2 continue
                        date_str race_no_str = parts[0] parts[1]
                        if not race_no_strisdigit) continue
                        race_no_c = intrace_no_str)
                        if not isinstancevalue dict) continue
                        horse_list = valueget'all_horses' [])
                        if not horse_list or not isinstancehorse_list list)
                            top = valueget'top_horse')
                            if top horse_list = [top]
                            else continue
                        cleaned = [strh)strip) for h in horse_list if strh)strip)]
                        for idx horse in enumeratecleaned[4] 1)
                            pred_listappend{'日期' date_str '場次' race_no_c '預測名次' idx '預測馬' horse})

                    if pred_list and not df_resultsempty
                        df_pred = pdDataFramepred_list)
                        df_pred['場次'] = df_pred['場次']astypeint)
                        df_pred['預測名次'] = df_pred['預測名次']astypeint)

                        pred_dates = sorteddf_pred['日期']unique))
                        result_dates = df_results['race_date']dtstrftime'%Y-%m-%d')unique)
                        available_dates = [d for d in pred_dates if d in result_dates]

                        if available_dates
                            selected_date = stselectbox"📅 選擇日期" available_dates format_func=lambda x x key="ai_cmp_date")
                            df_pred_date = df_pred[df_pred['日期'] == selected_date]copy)
                            df_result_date = df_results[df_results['race_date']dtstrftime'%Y-%m-%d') == selected_date]copy)

                            pred_races = sorteddf_pred_date['場次']unique))
                            result_races = sorteddf_result_date['race_no']unique))
                            available_races = [r for r in pred_races if r in result_races]

                            if available_races
                                selected_race = stselectbox"🏇 選擇場次" available_races format_func=lambda x f"第 {x} 場" key="ai_cmp_race")
                                df_pred_race = df_pred_date[df_pred_date['場次'] == selected_race]copy)
                                df_result_race = df_result_date[df_result_date['race_no'] == selected_race]copy)sort_values'finish_position')head4)
                                df_result_race = df_result_racerenamecolumns={'finish_position' '真實名次' 'horse_name' '真實馬'})

                                real_top3_names = df_result_race['真實馬']tolist)
                                df_pred_race['結果'] = df_pred_race['預測馬']applylambda x '命中' if x in real_top3_names else '失準')
                                
                                display_pred = df_pred_race[['預測名次' '預測馬' '結果']]copy)
                                display_predcolumns = ['名次' '預測馬' '結果']
                                display_real = df_result_race[['真實名次' '真實馬']]reset_indexdrop=True)
                                display_realcolumns = ['真實名次' '真實馬']
                                
                                # 🔥 修正對比邏輯只按馬名唔理名次
                                real_top3_names = df_result_race['真實馬']tolist)
                                
                                df_pred_race['結果'] = df_pred_race['預測馬']apply
                                    lambda x '命中' if x in real_top3_names else '失準'
                                
                                
                                # 🛠️ 關鍵修正強制重置索引確保左右對齊
                                df_pred_race = df_pred_racereset_indexdrop=True)
                                df_result_race = df_result_racereset_indexdrop=True)
                                
                                # 準備左邊預測)
                                display_pred = df_pred_race[['預測名次' '預測馬' '結果']]copy)
                                display_predcolumns = ['名次' '預測馬' '結果']
                                display_pred['名次'] = display_pred['名次']astypeint)  # 轉做整數
                                
                                # 準備右邊真實)
                                display_real = df_result_race[['真實名次' '真實馬']]copy)
                                display_realcolumns = ['真實名次' '真實馬']
                                display_real['真實名次'] = display_real['真實名次']astypeint)  # 轉做整數
                                
                                # 左右合併因為索引已經重置所以會完美對齊)
                                display_df = pdconcat[display_pred display_real] axis=1)

                                stwritef"📊 {selected_date} 第 {selected_race} 場 預測 vs 賽果")

                                def highlight_rowrow)
                                    if row['結果'] == '命中' return ['background-color #d4edda color black'] * lenrow)
                                    elif row['結果'] == '失準' return ['background-color #f8d7da color black'] * lenrow)
                                    return ['background-color white color black'] * lenrow)

                                stdataframedisplay_dfstyleapplyhighlight_row axis=1) use_container_width=True hide_index=True)
                            else
                                stinfof"ℹ️ {selected_date} 沒有可比對嘅場次")
                        else
                            stinfo"ℹ️ 沒有日期同時有預測同賽果數據")
                    else
                        stinfo"ℹ️ 請確保已有預測紀錄及賽果數據")
            except Exception as e
                sterrorf"❌ 讀取預測紀錄失敗{e}")
    # ===== 打賞功能 =====
    stdivider)
    stsubheader"❤️ 打賞支持")
    if stsession_stateget'logged_in' False)
        stcaption"你嘅支持係我哋繼續開發嘅動力打賞後會自動增加 VIP 天數。")
        
        headers = {"apikey" SUPABASE_KEY "Authorization" f"Bearer {SUPABASE_KEY}"}
        try
            res = requestsgetf"{SUPABASE_URL}/rest/v1/reward_configenabled=eqtrue&order=amountasc" headers=headers)
            configs = resjson) if resstatus_code == 200 else []
        except Exception
            configs = []
        
        if not configs
            stinfo"暫未開放打賞敬請期待")
        else
            cols = stcolumnslenconfigs))
            for i cfg in enumerateconfigs)
                with cols[i]
                    stmarkdownf"### {cfgget'label' '打賞')}")
                    stmarkdownf"**${cfg['amount']0f}**")
                    stcaptionf"送 {cfg['vip_days']} 日 VIP")
                    if stbuttonf"打賞 ${cfg['amount']0f}" key=f"reward_{cfg['id']}" use_container_width=True)
                        stsession_state['selected_reward'] = cfg
            
            if 'selected_reward' in stsession_state
                cfg = stsession_state['selected_reward']
                stdivider)
                stinfof"你選擇咗**{cfg['label']}**${cfg['amount']0f} → {cfg['vip_days']} 日 VIP)")
                stmarkdown"**付款方式FPS 轉數快**")
                stcode"FPS ID 你的電話號碼或 FPS ID" language=None)
                stmarkdown"付款後請撳下面個掣管理員會盡快審核。")
                
                if stbutton"✅ 我已經付款" type="primary")
                    headers_post = {
                        "apikey" SUPABASE_KEY
                        "Authorization" f"Bearer {SUPABASE_KEY}"
                        "Content-Type" "application/json"
                    }
                    payload = {
                        "username" stsession_stateget'username' 'unknown')
                        "amount" cfg['amount']
                        "vip_days" cfg['vip_days']
                        "rewarded_at" datetimenow)isoformat)
                        "status" "pending"
                    }
                    requestspostf"{SUPABASE_URL}/rest/v1/reward_history" headers=headers_post json=payload)
                    stsuccess"✅ 已提交管理員審核後會自動加 VIP 天數。")
                    if 'selected_reward' in stsession_state
                        del stsession_state['selected_reward']
    else
        stinfo"請先登入以使用打賞功能")

    stdivider)
    stwarning"⚠️ 免責聲明本系統預測僅供參考不構成投注建議。賽馬活動涉及風險用戶應量力而為。用戶必須年滿18歲。")
    stcaptionf"🕐 {datetimenow)strftime'%Y-%m-%d %H%M%S')} · v161")
    stcaption"💬 Telegram@bryhjdjbrbxibvrjskofndhiebdpaq")


if __name__ == '__main__'
    main)
