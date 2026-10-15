# check_date_range.py
# 檢查兩個檔案嘅日期範圍

import pandas as pd

print("=" * 60)
print("📂 ALL_DATA_MERGED_updated.csv 嘅日期範圍")
print("=" * 60)
main = pd.read_csv("ALL_DATA_MERGED_updated.csv", encoding='utf-8-sig', low_memory=False)
main.columns = [str(c).replace('\ufeff', '').strip() for c in main.columns]
main['race_date'] = pd.to_datetime(main['race_date'], errors='coerce')
main = main.dropna(subset=['race_date'])
print(f"最早日期：{main['race_date'].min()}")
print(f"最晚日期：{main['race_date'].max()}")
print(f"總行數：{len(main)}")

print("\n📊 按月統計（最近 10 個月）：")
main['month'] = main['race_date'].dt.strftime('%Y-%m')
monthly = main.groupby('month').size().reset_index(name='count')
print(monthly.tail(10).to_string(index=False))

print("\n" + "=" * 60)
print("📂 trackwork_aggregated.csv 嘅日期範圍")
print("=" * 60)
tw = pd.read_csv("trackwork_aggregated.csv", encoding='utf-8-sig')
tw.columns = [str(c).replace('\ufeff', '').strip() for c in tw.columns]
tw['race_date_str'] = tw['race_date'].astype(str)
print(f"最早日期：{tw['race_date_str'].min()}")
print(f"最晚日期：{tw['race_date_str'].max()}")
print(f"總行數：{len(tw)}")

print("\n📊 按月統計：")
tw['month'] = tw['race_date_str'].str[:6]
monthly_tw = tw.groupby('month').size().reset_index(name='count')
print(monthly_tw.to_string(index=False))

print("\n" + "=" * 60)
print("🔍 診斷：")
print("=" * 60)
main_max = main['race_date'].max().strftime('%Y%m%d')
tw_min = tw['race_date_str'].min()
if tw_min > main_max:
    print(f"❌ 晨操數據最早日期（{tw_min}）遲過主數據最晚日期（{main_max}）")
    print(f"   → 兩邊完全冇重疊，所以合併成功率係 0%")
    print(f"   → 解決方法：你需要爬取 2026年9月之前嘅晨操數據，或者等主數據更新。")
else:
    print(f"✅ 兩邊有重疊日期，可以合併")