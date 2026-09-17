#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_mapping.py
從 race_results_clean.csv 抽「中文馬名 ↔ horse_id」對照表
支援兩種格式：
  1. 新格式：horse_name='辣得金', horse_id='J087'（已拆欄）
  2. 舊格式：horse_name='辣得金 (J087)', horse_id=''（未拆欄）
"""

import os
import re
import pandas as pd

INPUT_FILE = "race_results_clean.csv"
OUTPUT_FILE = "horse_name_mapping_cn.csv"


def extract_from_old_format(name):
    """從 '辣得金 (J087)' 抽出 ('辣得金', 'J087')"""
    if pd.isna(name):
        return None, None
    name = str(name).strip()
    m = re.match(r'^(.+?)\s*\(([A-Z]\d+)\)\s*$', name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 搵唔到 {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]

    print(f"📊 讀入 {len(df)} 行")

    # 確保有 horse_id 欄
    if 'horse_id' not in df.columns:
        df['horse_id'] = ''
    if 'horse_name' not in df.columns:
        print("❌ 冇 horse_name 欄")
        return

    df['horse_id'] = df['horse_id'].fillna('').astype(str).str.strip()
    df['horse_name'] = df['horse_name'].astype(str).str.strip()

    records = []

    for _, row in df.iterrows():
        name = row['horse_name']
        hid = row['horse_id']

        # 情況 1：已經拆好欄
        if hid and hid != 'nan':
            clean_name = re.sub(r'\s*\([A-Z]\d+\)\s*$', '', name).strip()
            records.append({'horse_name_cn': clean_name, 'horse_id': hid})
            continue

        # 情況 2：舊格式，嘗試從中文名抽
        extracted_name, extracted_id = extract_from_old_format(name)
        if extracted_id:
            records.append({'horse_name_cn': extracted_name, 'horse_id': extracted_id})

    if not records:
        print("❌ 冇任何有效映射")
        return

    mapping_df = pd.DataFrame(records).drop_duplicates(subset=['horse_id'], keep='first')
    mapping_df = mapping_df.sort_values('horse_name_cn').reset_index(drop=True)

    mapping_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    print(f"\n✅ 生成 {len(mapping_df)} 條映射 → {OUTPUT_FILE}")
    print("\n頭 10 條：")
    print(mapping_df.head(10).to_string(index=False))


if __name__ == '__main__':
    main()
