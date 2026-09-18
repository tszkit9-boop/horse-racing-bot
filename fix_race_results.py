#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fix_race_results.py - 補齊 race_results_clean.csv 嘅 horse_id
"""

import re
import pandas as pd

# 1. 讀取對照表
print("📊 讀取對照表...")
mapping = pd.read_csv("horse_name_mapping_cn.csv", encoding='utf-8-sig')
mapping.columns = [str(c).replace('\ufeff', '').strip() for c in mapping.columns]

# 建立 中文名 → horse_id 字典
name_to_id = dict(zip(
    mapping['horse_name_cn'].astype(str).str.strip(),
    mapping['horse_id'].astype(str).str.strip()
))
print(f"  對照表：{len(name_to_id)} 條")

# 2. 讀取 race_results_clean.csv
print("📊 讀取 race_results_clean.csv...")
df = pd.read_csv("race_results_clean.csv", encoding='utf-8-sig')
df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
print(f"  原始數據：{len(df)} 筆")

# 3. 確保有 horse_id 欄
if 'horse_id' not in df.columns:
    df['horse_id'] = ''
df['horse_id'] = df['horse_id'].fillna('').astype(str).str.strip()
df['horse_name'] = df['horse_name'].astype(str).str.strip()

# 4. 從 horse_name 括號抽 horse_id（舊格式）
def extract_from_bracket(name):
    if pd.isna(name):
        return None
    m = re.match(r'^(.+?)\s*\(([A-Z]\d+)\)\s*$', str(name))
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None

# 5. 補齊 horse_id
fixed_bracket = 0
fixed_mapping = 0
still_empty = 0

for idx, row in df.iterrows():
    hid = str(row['horse_id']).strip()
    name = str(row['horse_name']).strip()

    # 已有 horse_id，跳過
    if hid and hid != 'nan' and hid != '':
        continue

    # 優先：從括號抽
    result = extract_from_bracket(name)
    if result:
        clean_name, extracted_id = result
        df.at[idx, 'horse_name'] = clean_name
        df.at[idx, 'horse_id'] = extracted_id
        fixed_bracket += 1
        continue

    # 次選：從對照表搵
    clean_name = re.sub(r'\s*\([A-Z]\d+\)\s*$', '', name).strip()
    if clean_name in name_to_id:
        df.at[idx, 'horse_id'] = name_to_id[clean_name]
        fixed_mapping += 1
        continue

    still_empty += 1

# 6. 儲存
df.to_csv("race_results_clean.csv", index=False, encoding='utf-8-sig')

print()
print("=" * 50)
print(f"✅ 完成！")
print(f"   從括號抽出：{fixed_bracket} 筆")
print(f"   從對照表補齊：{fixed_mapping} 筆")
print(f"   仍然空白：{still_empty} 筆")
print("=" * 50)
