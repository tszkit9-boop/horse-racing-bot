# backtest_top3.py
# 回測策略：每場買 AI 預測嘅頭三名，每匹 $100 獨贏
import pandas as pd
import numpy as np
import json
import requests
import re

SUPABASE_URL = "https://fewanagxvezelufmuggq.supabase.co"
SUPABASE_KEY = "sb_publishable_Ww_BGSKjqhGCvv5iNl8A0Q_UDkVqdtF"
BET_AMOUNT = 100
START_DATE = "2026-09-01"

# 1. 讀取預測
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
res = requests.get(f"{SUPABASE_URL}/rest/v1/predictions?date=gte.{START_DATE}&order=date.asc", headers=headers)
predictions = res.json() if res.status_code == 200 else []

# 2. 讀取賽果（判斷贏馬）
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

race_winner = {}
for (date, race), group in results.groupby([results['race_date'].dt.strftime('%Y-%m-%d'), 'race_no']):
    winner = group[group['finish_position'] == 1]['horse_name'].tolist()
    if winner:
        race_winner[(date, race)] = winner[0]

# 3. 讀取賠率
odds_df = pd.read_csv("odds_features.csv", encoding='utf-8-sig')
odds_df.columns = [str(c).replace('\ufeff', '').strip() for c in odds_df.columns]

def clean_name(name):
    if pd.isna(name): return ""
    name = str(name).strip()
    name = re.sub(r'[\(（].*?[\)）]', '', name)
    return name.replace(' ', '').replace('\u3000', '')

odds_df['clean_name'] = odds_df['horse_name'].apply(clean_name)
odds_df['date_str'] = pd.to_datetime(odds_df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')
odds_df['race_no'] = pd.to_numeric(odds_df['race_no'], errors='coerce')
odds_df['odds_last'] = pd.to_numeric(odds_df['odds_last'], errors='coerce')

odds_lookup = {}
for _, row in odds_df.iterrows():
    if pd.isna(row['race_no']) or pd.isna(row['odds_last']): continue
    odds_lookup[(row['date_str'], int(row['race_no']), row['clean_name'])] = row['odds_last']

# 4. 模擬落注
rows = []
bankroll = 10000

for pred in predictions:
    date_str = str(pred.get('date', '')).strip()
    race_no = pred.get('race')
    if not date_str or race_no is None: continue
    try: race_no = int(race_no)
    except: continue

    all_horses = pred.get('all_horses', [])
    if isinstance(all_horses, str):
        try: all_horses = json.loads(all_horses)
        except: all_horses = []
    if not all_horses: continue

    # 只取頭三名（如果少於三匹，有幾多買幾多）
    top3 = all_horses[:3]
    winner_key = (date_str, race_no)
    if winner_key not in race_winner: continue
    winner_clean = clean_name(race_winner[winner_key])

    for horse in top3:
        horse_clean = clean_name(horse)
        real_odds = odds_lookup.get((date_str, race_no, horse_clean))
        if real_odds is None or real_odds <= 1.0: continue

        is_win = (horse_clean == winner_clean)
        profit = (BET_AMOUNT * real_odds - BET_AMOUNT) if is_win else -BET_AMOUNT
        bankroll += profit

        rows.append({
            '日期': date_str, '場次': race_no, '買入馬': horse,
            '賠率': real_odds, '結果': '✅ 贏' if is_win else '❌ 輸',
            '盈虧': profit, '累積本金': bankroll
        })

# 5. 統計
df = pd.DataFrame(rows)
if df.empty:
    print("⚠️ 冇任何符合條件嘅落注機會")
else:
    total_bets = len(df)
    wins = (df['結果'] == '✅ 贏').sum()
    total_profit = df['盈虧'].sum()
    roi = total_profit / (total_bets * BET_AMOUNT) * 100

    print("\n" + "="*50)
    print("📊 頭三名回測結果（2026年9月至今）")
    print("="*50)
    print(f"策略：每場買頭三名，每匹 $100 獨贏")
    print(f"總落注次數：{total_bets}")
    print(f"命中次數（頭馬）：{wins}")
    print(f"命中率：{wins/total_bets:.1%}")
    print(f"總盈虧：${total_profit:+.0f}")
    print(f"投資回報率 (ROI)：{roi:+.1f}%")
    print(f"最終本金：${bankroll:.0f}（初始 $10000）")
    print("="*50)

    df.to_csv("backtest_top3_report.csv", index=False, encoding='utf-8-sig')
    print("\n✅ 報告已儲存到：backtest_top3_report.csv")