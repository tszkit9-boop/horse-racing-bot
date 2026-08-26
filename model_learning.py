# -*- coding: utf-8 -*-
"""
模型自我學習模組
功能：
1. 自動比對預測同真實賽果
2. 更新命中率、ROI 統計
3. 自動調整 XGBoost 同 CatBoost 嘅 fusion 權重
4. 顯示模型表現趨勢圖同特徵重要性
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from catboost import CatBoostClassifier
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# 配置
# ============================================================
ACCURACY_FILE = 'accuracy.json'
USER_DATA_FILE = 'users.json'
CONFIG_FILE = 'system_config.json'

# 特徵名稱（同主程式一致）
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
# 輔助函數
# ============================================================
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

def load_accuracy():
    return load_json(ACCURACY_FILE)

def save_accuracy(acc):
    return save_json(ACCURACY_FILE, acc)

def load_system_config():
    return load_json(CONFIG_FILE)

def save_system_config(config):
    return save_json(CONFIG_FILE, config)

# ============================================================
# 核心函數 1：自動比對賽果
# ============================================================
def update_accuracy_with_results():
    """
    自動比對 accuracy.json 入面嘅預測記錄同 ALL_DATA_MERGED.csv 嘅真實賽果
    回傳：更新咗幾多條記錄
    """
    acc = load_accuracy()
    records = acc.get('records', [])
    if not records:
        return 0, "沒有預測記錄"

    try:
        # 讀取歷史賽果數據
        results_df = pd.read_csv('ALL_DATA_MERGED.csv', encoding='utf-8-sig')
        
        # 標準化欄位名稱
        results_df = _standardize_columns(results_df)
        
        # 確保有日期、場次、馬名、名次欄位
        required_cols = ['race_date', 'race_no', 'horse_name', 'finish_position']
        for col in required_cols:
            if col not in results_df.columns:
                return 0, f"缺少必要欄位：{col}"
        
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
        results_df = results_df.dropna(subset=['race_date'])
        
        updated = 0
        for rec in records:
            if rec.get('actual_result') is not None:
                continue  # 已經對過
            date_str = rec.get('date')
            race_no = rec.get('race')
            horse = rec.get('horse')
            if not date_str or not race_no or not horse:
                continue
            matched = results_df[
                (results_df['race_date'].dt.strftime('%Y-%m-%d') == date_str) & 
                (results_df['race_no'] == race_no) & 
                (results_df['horse_name'] == horse)
            ]
            if not matched.empty:
                pos = matched.iloc[0]['finish_position']
                rec['actual_result'] = int(pos) if pd.notna(pos) else None
                rec['is_hit'] = (rec['actual_result'] == 1) if rec['actual_result'] is not None else None
                updated += 1
        if updated > 0:
            save_accuracy(acc)
        return updated, f"成功比對 {updated} 條記錄"
    except Exception as e:
        return 0, f"比對失敗：{str(e)}"

def _standardize_columns(df):
    """標準化欄位名稱（同主程式一致）"""
    rename_map = {
        '日期': 'race_date',
        '場次': 'race_no',
        '馬名': 'horse_name',
        '名次': 'finish_position',
        '馬匹名稱': 'horse_name',
        '馬匹名': 'horse_name',
        'horse_name': 'horse_name',
        'finish_position': 'finish_position'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    return df

# ============================================================
# 核心函數 2：自動調整模型權重
# ============================================================
def adjust_model_weights():
    """
    根據歷史命中率，自動調整 XGBoost 同 CatBoost 嘅 fusion 權重
    回傳：新權重
    """
    acc = load_accuracy()
    records = acc.get('records', [])
    
    # 計算整體命中率
    total = len([r for r in records if r.get('is_hit') is not None])
    hit = sum(1 for r in records if r.get('is_hit') is True)
    hit_rate = hit / total if total > 0 else 0
    
    # 讀取現有權重
    config = load_system_config()
    current_xgb = config.get('xgb_weight', 25)
    current_cat = config.get('cat_weight', 1)
    
    # 根據命中率調整權重
    # 規則：命中率越高，XGB 權重越高；命中率越低，CatBoost 權重越高
    if hit_rate >= 0.6:
        new_xgb = min(40, current_xgb + 3)
        new_cat = max(1, current_cat - 1)
    elif hit_rate >= 0.5:
        new_xgb = min(35, current_xgb + 1)
        new_cat = max(1, current_cat)
    elif hit_rate >= 0.4:
        new_xgb = max(15, current_xgb - 2)
        new_cat = min(10, current_cat + 2)
    elif hit_rate >= 0.3:
        new_xgb = max(10, current_xgb - 5)
        new_cat = min(15, current_cat + 5)
    else:
        new_xgb = max(5, current_xgb - 8)
        new_cat = min(20, current_cat + 8)
    
    # 確保總權重不變（保持 26，或者可以浮動）
    # 我哋採用浮動權重，唔鎖定總和
    # 如果權重差異過大，限制一下
    if new_xgb < 1: new_xgb = 1
    if new_cat < 1: new_cat = 1
    if new_xgb > 50: new_xgb = 50
    if new_cat > 30: new_cat = 30
    
    # 儲存新權重
    config['xgb_weight'] = new_xgb
    config['cat_weight'] = new_cat
    config['last_weight_update'] = datetime.now().isoformat()
    config['last_hit_rate'] = hit_rate
    save_system_config(config)
    
    return {
        'xgb_weight': new_xgb,
        'cat_weight': new_cat,
        'hit_rate': hit_rate,
        'total': total,
        'hit': hit
    }

# ============================================================
# 核心函數 3：獲取統計數據
# ============================================================
def get_model_stats():
    """
    獲取模型表現統計
    回傳：dict 包含總數、命中數、命中率、ROI、權重等
    """
    acc = load_accuracy()
    records = acc.get('records', [])
    
    total = len([r for r in records if r.get('is_hit') is not None])
    hit = sum(1 for r in records if r.get('is_hit') is True)
    hit_rate = hit / total if total > 0 else 0
    roi = (hit * 400 - total * 100) / (total * 100) if total > 0 else 0
    
    config = load_system_config()
    xgb_w = config.get('xgb_weight', 25)
    cat_w = config.get('cat_weight', 1)
    last_update = config.get('last_weight_update', '從未')
    
    # 最近 10 場命中情況
    recent_10 = []
    if records:
        sorted_records = sorted(records, key=lambda x: x.get('predicted_at', ''), reverse=True)
        for r in sorted_records[:10]:
            recent_10.append(r.get('is_hit'))
    
    return {
        'total': total,
        'hit': hit,
        'hit_rate': hit_rate,
        'roi': roi,
        'xgb_weight': xgb_w,
        'cat_weight': cat_w,
        'last_update': last_update,
        'recent_10': recent_10,
        'total_records': len(records)
    }

# ============================================================
# 核心函數 4：顯示分析儀表板（用於主頁面）
# ============================================================
def show_analysis_dashboard():
    """
    顯示模型分析儀表板（放喺預測控制上層）
    """
    stats = get_model_stats()
    records = load_accuracy().get('records', [])
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    col_stat1.metric("📊 總預測", stats['total'])
    col_stat2.metric("🎯 命中次數", stats['hit'])
    col_stat3.metric("📈 命中率", f"{stats['hit_rate']:.2%}")
    col_stat4.metric("💰 ROI (模擬)", f"{stats['roi']:.2%}")
    
    # 最近 10 場命中情況
    if stats['recent_10']:
        hit_seq = ["✅" if h is True else "❌" if h is False else "⬜" for h in stats['recent_10']]
        st.caption(f"📊 最近 10 場命中情況： " + "".join(hit_seq))
    
    # 顯示當前權重
    st.caption(f"⚙️ 當前模型融合權重：XGBoost **{stats['xgb_weight']}** : CatBoost **{stats['cat_weight']}**（上次調整：{stats['last_update']}）")
    
    # 更新按鈕
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 比對賽果 + 更新統計", key="update_analysis_btn", use_container_width=True):
            with st.spinner("正在比對賽果..."):
                updated, msg = update_accuracy_with_results()
                if updated > 0:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.info(f"📭 {msg}")
    with col_btn2:
        if st.button("⚖️ 自動調整權重", key="adjust_weights_btn", use_container_width=True):
            with st.spinner("正在計算最佳權重..."):
                result = adjust_model_weights()
                st.success(f"✅ 權重已調整：XGBoost = {result['xgb_weight']}, CatBoost = {result['cat_weight']}（命中率 {result['hit_rate']:.2%}，共 {result['total']} 場）")
                st.rerun()
    
    # 特徵重要性圖表
    with st.expander("📊 特徵重要性分析（CatBoost）"):
        try:
            cat_model = CatBoostClassifier()
            cat_model.load_model('hk_catboost_model.cbm')
            importances = cat_model.get_feature_importance()
            feature_names = EXPECTED_FEATURES
            if len(importances) == len(feature_names):
                df_imp = pd.DataFrame({
                    '特徵': feature_names,
                    '重要性': importances
                }).sort_values('重要性', ascending=False).head(15)
                fig = px.bar(df_imp, x='重要性', y='特徵', orientation='h', 
                            title='Top 15 特徵重要性',
                            color='重要性', color_continuous_scale='Blues')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("特徵數量不匹配")
        except Exception as e:
            st.info(f"無法載入 CatBoost 模型：{e}")
    
    # 命中率趨勢圖
    with st.expander("📈 命中率趨勢圖"):
        if records:
            df_records = pd.DataFrame(records)
            if 'date' in df_records.columns and 'is_hit' in df_records.columns:
                df_records['date'] = pd.to_datetime(df_records['date'])
                df_records = df_records.dropna(subset=['date', 'is_hit'])
                if not df_records.empty:
                    daily = df_records.groupby(df_records['date'].dt.date).agg(
                        total=('is_hit', 'count'),
                        hit=('is_hit', lambda x: (x==True).sum())
                    ).reset_index()
                    daily['hit_rate'] = daily['hit'] / daily['total']
                    fig2 = px.line(daily, x='date', y='hit_rate', 
                                   title='每日命中率趨勢',
                                   markers=True)
                    fig2.update_layout(yaxis_tickformat='.0%')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("未有足夠數據")
            else:
                st.info("未有日期或命中數據")
        else:
            st.info("暫時未有預測記錄")

# ============================================================
# 核心函數 5：權重建議（顯示俾管理員睇）
# ============================================================
def get_weight_recommendation():
    """
    根據特徵重要性數據，俾出權重調整建議
    """
    try:
        cat_model = CatBoostClassifier()
        cat_model.load_model('hk_catboost_model.cbm')
        importances = cat_model.get_feature_importance()
        # 簡單建議：如果重要特徵多，CatBoost 權重應該高啲
        # 但呢個只係非常粗略嘅建議
        high_importance = sum(1 for i in importances if i > 1.0)
        if high_importance > 10:
            return "CatBoost 有多個重要特徵，建議增加 CatBoost 權重"
        else:
            return "XGBoost 表現穩定，建議保持 XGBoost 為主導"
    except:
        return "無法分析特徵重要性"

# ============================================================
# 如果直接執行此檔案，可以測試
# ============================================================
if __name__ == '__main__':
    print("🧠 模型自我學習模組")
    print("=" * 40)
    stats = get_model_stats()
    print(f"總預測：{stats['total']}")
    print(f"命中率：{stats['hit_rate']:.2%}")
    print(f"當前權重：XGB {stats['xgb_weight']} : Cat {stats['cat_weight']}")
