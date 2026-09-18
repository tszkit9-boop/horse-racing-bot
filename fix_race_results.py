#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fix_race_results.py - 補齊 race_results_clean.csv 嘅 horse_id
"""

import os
import re
import pandas as pd

MAPPING_FILE = "horse_name_mapping_cn.csv"
RESULT_FILE = "race_results_clean.csv"


def normalize_name(name):
    """清理馬名（移除括號、空格）"""
    if pd.isna(name):
        return ''
    name = str(name).strip()
    name = re.sub(r'\s*\([A-Z]\d+\)\s*$', '', name)
    name = name.replace(' ', '').replace('\u3000', '')
    name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', name)
    return name


def extract_from_bracket(name):
    """從 '辣得金 (J087)' 抽出 ('辣得金', 'J087')"""
    if pd.isna(name):
        return None, None
    m = re.match(r'^(.+?)\s*\(([A-Z]\d+)\)\s*$', str(name).strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def main():
    # 1. 讀取對照表
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ 搵唔到 {MAPPING_FILE}")
        return

    print(f"📊 讀取 {MAPPING_FILE}...")
    mapping = pd.read_csv(MAPPING_FILE, encoding='utf-8-sig')
    mapping.columns = [str(c).replace('\ufeff', '').strip() for c in mapping.columns]

    if 'horse_name_cn' not in mapping.columns or 'horse_id' not in mapping.columns:
        print(f"❌ 對照表缺少必要欄位：{list(mapping.columns)}")
        return

    # 建立 normalised 中文名 → horse_id 字典
    mapping['_norm'] = mapping['horse_name_cn'].apply(normalize_name)
    mapping = mapping[mapping['_norm'] != '']
    name_to_id = dict(zip(mapping['_norm'], mapping['horse_id'].astype(str).str.strip()))
    print(f"  ✅ 對照表：{len(name_to_id)} 條")

    # 2. 讀取賽果檔
    if not os.path.exists(RESULT_FILE):
        print(f"❌ 搵唔到 {RESULT_FILE}")
        return

    print(f"📊 讀取 {RESULT_FILE}...")
    df = pd.read_csv(RESULT_FILE, encoding='utf-8-sig')
    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    print(f"  原始數據：{len(df)} 筆")

    # 確保有 horse_id 欄
    if 'horse_id' not in df.columns:
        df['horse_id'] = ''
    if 'horse_name' not in df.columns:
        print("❌ 缺少 horse_name 欄位")
        return

    df['horse_id'] = df['horse_id'].fillna('').astype(str).str.strip()
    df['horse_id'] = df['horse_id'].replace('nan', '')
    df['horse_name'] = df['horse_name'].astype(str).str.strip()

    # 3. 逐行補齊
    fixed_bracket = 0
    fixed_mapping = 0
    still_empty = 0
    already_has = 0

    for idx, row in df.iterrows():
        hid = str(row['horse_id']).strip()
        name = str(row['horse_name']).strip()

        # 已有 horse_id，跳過
        if hid and hid != 'nan' and hid != '':
            already_has += 1
            continue

        # 優先：從括號抽
        clean_name, extracted_id = extract_from_bracket(name)
        if extracted_id:
            df.at[idx, 'horse_name'] = clean_name
            df.at[idx, 'horse_id'] = extracted_id
            fixed_bracket += 1
            continue

        # 次選：從對照表搵
        norm = normalize_name(name)
        if norm in name_to_id:
            df.at[idx, 'horse_id'] = name_to_id[norm]
            fixed_mapping += 1
            continue

        still_empty += 1

    # 4. 儲存
    df.to_csv(RESULT_FILE, index=False, encoding='utf-8-sig')

    print()
    print("=" * 50)
    print(f"🎉 完成！")
    print(f"   已有 horse_id：{already_has} 筆")
    print(f"   從括號抽出：{fixed_bracket} 筆")
    print(f"   從對照表補齊：{fixed_mapping} 筆")
    print(f"   仍然空白：{still_empty} 筆")
    print("=" * 50)


if __name__ == '__main__':
    main()
