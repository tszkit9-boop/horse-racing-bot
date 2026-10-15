# backtest_advanced.py
# Level 2 進化版回測：計算賺蝕（ROI）
# 賠率來源：odds_features.csv
# ⚠️ 呢個腳本只會讀取數據，絕對唔會寫入 Supabase，唔會影響網站

import pandas as pd
import numpy as np
import json
import requests
import re
from datetime import datetime

# ===== 設定 =====
SUPABASE_URL = "https://fewanagxvezelufmuggq.supabase.co"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"
BET_AMOUNT = 100          # 每注金額
VALUE_THRESHOLD = 0.4     # 值博率門檻（0.4 = 40%）
START_DATE = "2026-09-01"

# ===== 1. 從 Supabase 讀取預測 =====
print("📂 讀取 Supabase 預測紀錄...")
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
try:
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/predictions?date=gte.{START_DATE}&order=date.asc",
        headers=headers, timeout=15
    )
    predictions = res.json() if res.status_code == 200 else []
    print(f"✅ 讀取到 {len(predictions)} 條預測紀錄")
except Exception as e:
    print(f"❌ 連線失敗：{e}")
    exit()

# ===== 2. 讀取賽果（判斷贏馬）=====
print("\n📂 讀取賽果數據 (race_results_clean.csv)...")
results = pd.read_csv("race_results_clean.csv", encoding='utf-8-sig')
results.columns = [str(c).replace('\ufeff', '').strip() for c in results.columns]
results['race_date'] = pd.to_datetime(results['race_date'], errors='coerce')
results = results.dropna(subset=['race_date'])
results = results[results['race_date'] >= START_DATE]
results['race_no'] = pd.to_numeric(results['race_no'], errors='coerce')
results['finish_position'] = pd.to_numeric(results['finish_position'], errors='coerce')
results = results.dropna(subset=['race_no', 'finish_position'])
results['race_no'] = results['race_no'].astype(int)
results['horse_name'] = results['horse_name'].astype(str).str.strip()

# 建立贏馬 Lookup
race_winner = {}
for (date, race), group in results.groupby([results['race_date'].dt.strftime('%Y-%m-%d'), 'race_no']):
    winner = group[group['finish_position'] == 1]['horse_name'].tolist()
    if winner:
        race_winner[(date, race)] = winner[0]

print(f"✅ 建立咗 {len(race_winner)} 場賽事嘅贏馬數據")

# ===== 3. 從 odds_features.csv 讀取賠率 =====
print("\n📂 讀取賠率數據 (odds_features.csv)...")
odds_df = pd.read_csv("odds_features.csv", encoding='utf-8-sig')
odds_df.columns = [str(c).replace('\ufeff', '').strip() for c in odds_df.columns]

# 統一馬名格式（清走 (H123) 呢類括號）
def clean_name(name):
    if pd.isna(name):
        return ""
    name = str(name).strip()
    name = re.sub(r'[\(（].*?[\)）]', '', name)
    name = name.replace(' ', '').replace('\u3000', '')
    return name

odds_df['clean_name'] = odds_df['horse_name'].apply(clean_name)
odds_df['date_str'] = pd.to_datetime(odds_df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')
odds_df['race_no'] = pd.to_numeric(odds_df['race_no'], errors='coerce')
odds_df['odds_last'] = pd.to_numeric(odds_df['odds_last'], errors='coerce')

# 建立賠率 Lookup
odds_lookup = {}
for _, row in odds_df.iterrows():
    if pd.isna(row['race_no']) or pd.isna(row['odds_last']):
        continue
    key = (row['date_str'], int(row['race_no']), row['clean_name'])
    odds_lookup[key] = row['odds_last']

print(f"✅ 建立咗 {len(odds_lookup)} 條賠率紀錄")

# ===== 4. 逐條預測模擬落注 =====
rows = []
bankroll = 10000  # 初始本金
matched_odds_count = 0

for pred in predictions:
    date_str = str(pred.get('date', '')).strip()
    race_no = pred.get('race')
    if not date_str or race_no is None:
        continue
    try:
        race_no = int(race_no)
    except:
        continue

    # 拎預測
    all_horses = pred.get('all_horses', [])
    if isinstance(all_horses, str):
        try:
            all_horses = json.loads(all_horses)
        except:
            all_horses = []
    if not all_horses:
        continue

    top_horse = all_horses[0]
    top_prob = float(pred.get('top_prob', 0))
    top_horse_clean = clean_name(top_horse)

    # 拎真實賠率（從 odds_features.csv 嘅 odds_last）
    key = (date_str, race_no, top_horse_clean)
    real_odds = odds_lookup.get(key, None)

    if real_odds is None or real_odds <= 1.0:
        continue

    matched_odds_count += 1

    # 計算值博率
    implied_prob = 1.0 / real_odds
    value_ratio = (top_prob - implied_prob) / implied_prob

    # 只買值博率 > 門檻嘅馬
    if value_ratio < VALUE_THRESHOLD:
        continue

    # 檢查有冇贏
    winner_key = (date_str, race_no)
    if winner_key not in race_winner:
        continue

    winner_clean = clean_name(race_winner[winner_key])
    is_win = (winner_clean == top_horse_clean)
    profit = (BET_AMOUNT * real_odds - BET_AMOUNT) if is_win else -BET_AMOUNT
    bankroll += profit

    rows.append({
        '日期': date_str,
        '場次': race_no,
        '買入馬': top_horse,
        '賠率': real_odds,
        '模型概率': f"{top_prob:.1%}",
        '值博率': f"{value_ratio:+.1%}",
        '結果': '✅ 贏' if is_win else '❌ 輸',
        '盈虧': profit,
        '累積本金': bankroll
    })

# ===== 5. 統計 =====
df = pd.DataFrame(rows)
if df.empty:
    print(f"\n⚠️ 冇任何符合值博率 > {VALUE_THRESHOLD:.0%} 嘅落注機會")
    print(f"（提示：總共只有 {matched_odds_count} 條預測成功匹配到賠率）")
    exit()

total_bets = len(df)
wins = (df['結果'] == '✅ 贏').sum()
total_profit = df['盈虧'].sum()
roi = total_profit / (total_bets * BET_AMOUNT) * 100

print("\n" + "="*50)
print("📊 進化版回測結果（2026年9月至今）")
print("="*50)
print(f"策略：值博率 > {VALUE_THRESHOLD:.0%} 就買 $100 獨贏")
print(f"總落注次數：{total_bets}")
print(f"命中次數：{wins}")
print(f"命中率：{wins/total_bets:.1%}")
print(f"總盈虧：${total_profit:+.0f}")
print(f"投資回報率 (ROI)：{roi:+.1f}%")
print(f"最終本金：${bankroll:.0f}（初始 $10000）")
print("="*50)

df.to_csv("backtest_advanced_report.csv", index=False, encoding='utf-8-sig')
print(f"\n✅ 詳細報告已儲存到：backtest_advanced_report.csv")