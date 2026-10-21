#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
accuracy_check.py - 對比預測同實際賽果
1. 輸出 accuracy_report.csv (命中率)
2. 結算紙上回測盈虧 (位置模式)
3. 🆕 分析位置Q (A+B, A+C) 策略命中率，並輸出 qpl_summary.json
"""

import pandas as pd
import json
import os
from datetime import datetime
from supabase import create_client

SUPABASE_URL = "https://fewanagxvezelufmuggq.supabase.co"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"
OUTPUT_CSV = "accuracy_report.csv"


def get_venue(race_date_str):
    """根據日期判斷場地：星期三 = HV，其他 = ST"""
    try:
        d = pd.to_datetime(race_date_str)
        return 'HV' if d.weekday() == 2 else 'ST'
    except Exception:
        return 'ST'


# ============================================================
# 📊 1. 命中率報告
# ============================================================
def generate_accuracy_report():
    print("=" * 60)
    print("📊 開始生成命中率報告...")

    # ===== 讀取預測記錄 =====
    print("📂 讀取預測記錄...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table("predictions").select("*").execute()
    pred_df = pd.DataFrame(response.data)
    print(f"  ✅ {len(pred_df)} 條預測記錄")

    # ===== 讀取賽果 =====
    print("📂 讀取賽果...")
    if not os.path.exists("race_results_clean.csv"):
        print("⚠️ 冇 race_results_clean.csv")
        return
        
    results_df = pd.read_csv("race_results_clean.csv", encoding="utf-8-sig", low_memory=False)
    results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
    results_df['race_no'] = pd.to_numeric(results_df['race_no'], errors='coerce').fillna(0).astype(int)
    results_df['finish_position'] = pd.to_numeric(results_df['finish_position'], errors='coerce')
    results_df['horse_name'] = results_df['horse_name'].astype(str).str.strip()
    results_df = results_df.dropna(subset=['race_date', 'finish_position'])
    print(f"  ✅ {len(results_df)} 條賽果記錄")

    # ===== 逐條對比 =====
    print("🔧 對比預測同賽果...")
    rows = []
    for _, pred in pred_df.iterrows():
        pred_date = pred.get('date', '')
        pred_race = pred.get('race', 0)
        top_horse = pred.get('top_horse', '')
        all_horses = json.loads(pred['all_horses']) if pred.get('all_horses') else []

        sub = results_df[
            (results_df['race_date'].dt.strftime('%Y-%m-%d') == pred_date) &
            (results_df['race_no'] == pred_race)
        ]
        if sub.empty:
            continue

        winner_row = sub[sub['finish_position'] == 1]
        if winner_row.empty:
            continue
        actual_winner = winner_row.iloc[0]['horse_name']

        top1_hit = (top_horse == actual_winner)
        top3_hit = (actual_winner in all_horses[:3])

        rows.append({
            'date': pred_date,
            'race': pred_race,
            'venue': get_venue(pred_date),
            'top_horse': top_horse,
            'actual_winner': actual_winner,
            'top1_hit': top1_hit,
            'top3_hit': top3_hit,
        })

    detail_df = pd.DataFrame(rows)
    if detail_df.empty:
        print("⚠️ 冇匹配到任何預測同賽果")
        return

    # ===== 統計 =====
    print("\n📊 統計結果：")
    for venue in ['ST', 'HV']:
        venue_df = detail_df[detail_df['venue'] == venue]
        if venue_df.empty:
            continue
        total = len(venue_df)
        top1 = venue_df['top1_hit'].sum()
        top3 = venue_df['top3_hit'].sum()
        name = '沙田（ST）' if venue == 'ST' else '跑馬地（HV）'
        print(f"  {name}：")
        print(f"    總場次：{total}")
        print(f"    Top-1 命中：{top1}（{top1/total:.1%}）")
        print(f"    Top-3 命中：{top3}（{top3/total:.1%}）")

    total = len(detail_df)
    top1 = detail_df['top1_hit'].sum()
    top3 = detail_df['top3_hit'].sum()
    print(f"\n  整體：")
    print(f"    總場次：{total}")
    print(f"    Top-1 命中：{top1}（{top1/total:.1%}）")
    print(f"    Top-3 命中：{top3}（{top3/total:.1%}）")

    # ===== 寫入 CSV =====
    detail_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n🎉 已寫入 {OUTPUT_CSV}")


# ============================================================
# 📝 2. 紙上回測自動結算（位置模式）
# ============================================================
def settle_paper_trades():
    print("=" * 60)
    print("📝 開始結算紙上回測（位置模式）...")

    if not os.path.exists("race_results_clean.csv"):
        print("⚠️ 冇 race_results_clean.csv，無法結算紙上回測。")
        return

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # ===== 讀取賽果 =====
        results_df = pd.read_csv("race_results_clean.csv", encoding="utf-8-sig", low_memory=False)
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
        results_df['race_no'] = pd.to_numeric(results_df['race_no'], errors='coerce').fillna(0).astype(int)
        results_df['finish_position'] = pd.to_numeric(results_df['finish_position'], errors='coerce')
        results_df['horse_name'] = results_df['horse_name'].astype(str).str.strip()
        results_df = results_df.dropna(subset=['race_date', 'finish_position'])

        # ===== 讀取未結算嘅紙上投注 =====
        response = supabase.table("paper_trades").select("*").eq("settled", False).execute()
        trades = response.data
        if not trades:
            print("ℹ️ 冇未結算嘅紙上投注。")
            return

        print(f"✅ 已載入 {len(trades)} 筆未結算紙上投注")

        settled_count = 0
        win_count = 0
        lose_count = 0
        total_profit = 0.0

        for trade in trades:
            try:
                pred_date = trade.get('date', '')
                pred_race = int(trade.get('race', 0))
                horse_name = trade.get('horse_name', '')
                odds = float(trade.get('odds', 0))
                bet_amount = float(trade.get('bet_amount', 100))

                sub = results_df[
                    (results_df['race_date'].dt.strftime('%Y-%m-%d') == pred_date) &
                    (results_df['race_no'] == pred_race) &
                    (results_df['horse_name'] == str(horse_name).strip())
                ]
                if sub.empty:
                    continue

                pos = sub.iloc[0]['finish_position']
                if pd.isna(pos):
                    continue

                # 🆕 買位置：跑入前三名就贏（pos <= 3）
                if int(pos) <= 3:
                    # 因為系統冇爬位置賠率，我哋用獨贏賠率除以 3.5 做保守估算
                    est_place_odds = odds / 3.5
                    if est_place_odds < 1.0:
                        est_place_odds = 1.0
                    profit = (est_place_odds - 1.0) * bet_amount
                    result = 'win'
                    win_count += 1
                else:
                    profit = -bet_amount
                    result = 'lose'
                    lose_count += 1

                total_profit += profit

                # 更新 Supabase
                supabase.table("paper_trades").update({
                    "result": result,
                    "profit": profit,
                    "settled": True
                }).eq("id", trade['id']).execute()

                settled_count += 1
            except Exception as e:
                print(f"⚠️ 結算交易 {trade.get('id')} 失敗：{e}")

        print(f"✅ 已結算 {settled_count} 筆紙上投注")
        if settled_count > 0:
            print(f"   勝：{win_count} 筆 ｜ 負：{lose_count} 筆")
            print(f"   總盈虧：${total_profit:,.0f}")

    except Exception as e:
        print(f"⚠️ 結算紙上回測失敗：{e}")


# ============================================================
# 🧪 3. 位置Q (QPL) 策略回測分析 (A+B, A+C)
# ============================================================
def analyze_qpl_strategy():
    print("=" * 60)
    print("🧪 開始分析【位置Q 策略】 (A+B, A+C)...")

    if not os.path.exists("race_results_clean.csv"):
        print("⚠️ 冇 race_results_clean.csv，無法分析。")
        return

    try:
        # 1. 讀取預測記錄 (攞 Top 3)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table("predictions").select("*").execute()
        pred_df = pd.DataFrame(response.data)

        # 2. 讀取賽果
        results_df = pd.read_csv("race_results_clean.csv", encoding="utf-8-sig")
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')
        results_df['race_no'] = pd.to_numeric(results_df['race_no'], errors='coerce').fillna(0).astype(int)
        results_df['horse_name'] = results_df['horse_name'].astype(str).str.strip()

        total_races = 0
        ab_hits = 0
        ac_hits = 0

        details = []

        for _, pred in pred_df.iterrows():
            pred_date = pred.get('date', '')
            pred_race = pred.get('race', 0)
            all_horses = json.loads(pred['all_horses']) if pred.get('all_horses') else []

            if len(all_horses) < 3:
                continue

            A, B, C = all_horses[0], all_horses[1], all_horses[2]

            # 攞返呢場嘅賽果
            sub = results_df[
                (results_df['race_date'] == pred_date) &
                (results_df['race_no'] == pred_race)
            ]
            if sub.empty:
                continue

            total_races += 1

            # 搵 A, B, C 嘅名次
            def get_pos(horse_name):
                row = sub[sub['horse_name'] == str(horse_name).strip()]
                if not row.empty:
                    return pd.to_numeric(row.iloc[0]['finish_position'], errors='coerce')
                return 99

            pos_A = get_pos(A)
            pos_B = get_pos(B)
            pos_C = get_pos(C)

            # 判斷 A+B 同 A+C 有冇中
            ab_hit = (pos_A <= 3) and (pos_B <= 3)
            ac_hit = (pos_A <= 3) and (pos_C <= 3)

            if ab_hit: ab_hits += 1
            if ac_hit: ac_hits += 1

            if ab_hit or ac_hit:
                details.append({
                    '日期': pred_date,
                    '場次': pred_race,
                    'Top3預測': f"A:{A}({pos_A}) / B:{B}({pos_B}) / C:{C}({pos_C})",
                    'A+B 命中': '✅' if ab_hit else '❌',
                    'A+C 命中': '✅' if ac_hit else '❌'
                })

        print(f"📊 共分析 {total_races} 場有效賽事")
        if total_races > 0:
            print(f"   🎯 A+B (首選+次選) 命中率：{ab_hits}/{total_races} = {ab_hits/total_races:.1%}")
            print(f"   🎯 A+C (首選+第三) 命中率：{ac_hits}/{total_races} = {ac_hits/total_races:.1%}")

        # 輸出詳細命中紀錄
        if details:
            df_details = pd.DataFrame(details)
            df_details.to_csv("qpl_backtest_report.csv", index=False, encoding="utf-8-sig")
            print("🎉 已將位置Q命中詳細紀錄寫入 qpl_backtest_report.csv")

        # 🆕 將統計結果寫入 JSON 供網站讀取
        summary = {
            "total_races": total_races,
            "ab_hits": ab_hits,
            "ac_hits": ac_hits,
            "ab_rate": (ab_hits/total_races) if total_races > 0 else 0,
            "ac_rate": (ac_hits/total_races) if total_races > 0 else 0
        }
        with open("qpl_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=4)
        print("📁 已將統計結果寫入 qpl_summary.json")

    except Exception as e:
        print(f"⚠️ 分析位置Q失敗：{e}")


# ============================================================
# 主程式
# ============================================================
if __name__ == "__main__":
    generate_accuracy_report()
    settle_paper_trades()
    analyze_qpl_strategy()  # 🆕 執行位置Q分析
    print("=" * 60)
    print("✅ 所有任務完成")