#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
預測全日所有場次
用法：
  python predict_all_races.py --date 2025-04-09
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
import pandas as pd
import os
import subprocess
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('--date', type=str, required=True, help='日期 YYYY-MM-DD')
args = parser.parse_args()

target_date = args.date
print(f"📊 開始預測 {target_date} 全日所有場次...")

# 讀取排位表
df = pd.read_csv('HKCJ_FULL_YEAR_DATA.csv', encoding='utf-8-sig')
df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
target = pd.to_datetime(target_date)

# 篩選指定日期
day_races = df[df['race_date'].dt.date == target.date()]
if day_races.empty:
    print(f"❌ {target_date} 沒有賽事")
    sys.exit(1)

# 取得所有場次
race_nos = sorted(day_races['race_no'].unique())
print(f"📋 共 {len(race_nos)} 場：{race_nos}")

all_results = []
for race_no in race_nos:
    print(f"\n🏇 預測第 {race_no} 場...")
    # 呼叫 predict_race_card.py 逐場預測
    result = subprocess.run(
        ['python', 'predict_race_card.py', '--date', target_date, '--race', str(race_no)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        # 讀取預測結果
        df_pred = pd.read_csv('prediction_result.csv')
        df_pred['場次'] = race_no
        all_results.append(df_pred)
        print(f"  ✅ 第 {race_no} 場完成")
    else:
        print(f"  ❌ 第 {race_no} 場失敗")

if not all_results:
    print("❌ 沒有任何場次成功")
    sys.exit(1)

# 合併所有結果
combined = pd.concat(all_results, ignore_index=True)
output_file = f'prediction_all_{target_date}.csv'
combined.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n✅ 全部預測完成！共 {len(combined)} 筆記錄")
print(f"📁 已儲存至 {output_file}")

# 顯示摘要
print("\n" + "="*60)
print(f"🏇 {target_date} 全日預測摘要")
print("="*60)
for race_no in race_nos:
    race_data = combined[combined['場次'] == race_no]
    if not race_data.empty:
        winner = race_data.iloc[0]['馬匹名稱']
        print(f"第{race_no}場：{winner}（勝率 {race_data.iloc[0]['預測勝率']:.2%}）")
print("="*60)