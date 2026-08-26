#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
每日自動比對賽果 (供 GitHub Actions 使用)
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def standardize_columns_safe(df):
    rename_map = {
        '日期': 'race_date',
        '場次': 'race_no',
        '馬名': 'horse_name',
        '名次': 'finish_position',
        '馬匹名稱': 'horse_name',
        'horse_name': 'horse_name',
        'finish_position': 'finish_position'
    }
    df.rename(columns=rename_map, inplace=True, errors='ignore')
    return df

ACCURACY_FILE = 'accuracy.json'
ALL_DATA_FILE = 'ALL_DATA_MERGED.csv'

def update_accuracy_with_results():
    acc = load_json(ACCURACY_FILE)
    records = acc.get('records', [])
    if not records:
        return 0, "沒有預測記錄"
    try:
        results_df = pd.read_csv(ALL_DATA_FILE, encoding='utf-8-sig')
        results_df = standardize_columns_safe(results_df)
        required = ['race_date', 'race_no', 'horse_name', 'finish_position']
        for col in required:
            if col not in results_df.columns:
                return 0, f"缺少必要欄位：{col}"
        results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce')
        results_df = results_df.dropna(subset=['race_date'])
        updated = 0
        for rec in records:
            if rec.get('actual_result') is not None:
                continue
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
            save_json(ACCURACY_FILE, acc)
        return updated, f"成功比對 {updated} 條記錄"
    except Exception as e:
        return 0, f"比對失敗：{str(e)}"

def main():
    print(f"🤖 開始自動比對賽果 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    updated, msg = update_accuracy_with_results()
    print(f"✅ {msg}")
    if updated > 0:
        print("📝 accuracy.json 已更新，將 commit 變更")
    else:
        print("📭 無新記錄更新")

if __name__ == '__main__':
    main()
