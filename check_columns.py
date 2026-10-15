# check_columns.py
# 只係檢查欄位，唔會修改任何檔案

import pandas as pd

print("=" * 60)
print("📂 ALL_DATA_MERGED_updated.csv 嘅欄位：")
print("=" * 60)
main = pd.read_csv("ALL_DATA_MERGED_updated.csv", encoding='utf-8-sig', low_memory=False, nrows=5)
main.columns = [str(c).replace('\ufeff', '').strip() for c in main.columns]
print(f"總欄位數：{len(main.columns)}")
print(f"欄位清單：{main.columns.tolist()}")

print("\n" + "=" * 60)
print("📂 trackwork_aggregated.csv 嘅欄位：")
print("=" * 60)
tw = pd.read_csv("trackwork_aggregated.csv", encoding='utf-8-sig', nrows=5)
tw.columns = [str(c).replace('\ufeff', '').strip() for c in tw.columns]
print(f"欄位清單：{tw.columns.tolist()}")

print("\n" + "=" * 60)
print("📋 ALL_DATA_MERGED_updated.csv 前 3 行（只顯示部分欄位）：")
print("=" * 60)
# 只顯示馬名、日期、場次相關嘅欄位
cols_to_show = []
for c in main.columns:
    cl = str(c).lower()
    if any(k in cl for k in ['horse', 'name', '馬', 'date', '日期', 'race', '場']):
        cols_to_show.append(c)
print(main[cols_to_show].head(3).to_string())

print("\n✅ 檢查完成，冇修改任何檔案。")