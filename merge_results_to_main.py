# merge_results_to_main.py
# 將賽果數據合併入主訓練數據，另存新檔，不覆蓋原檔
# 只讀取，不修改任何現有檔案

import pandas as pd

# ===== 1. 讀取賽果數據（你上傳嘅檔案）=====
print("📂 讀取賽果數據...")
# 請確認你嘅檔案名稱，如果唔同請自行修改
results_df = pd.read_csv("race_results_clean.csv", encoding='utf-8-sig') 
# 如果你嘅檔案叫其他名，請改成你嘅檔案名
# 例如: results_df = pd.read_csv("你嘅賽果檔案.csv", encoding='utf-8-sig')

# 清理欄位名
results_df.columns = [str(c).replace('\ufeff', '').strip() for c in results_df.columns]

print(f"✅ 賽果數據：{len(results_df)} 行")
print(f"賽果欄位：{results_df.columns.tolist()}")

# ===== 2. 讀取主訓練數據 =====
print("\n📂 讀取主訓練數據 (ALL_DATA_MERGED_updated.csv)...")
main_df = pd.read_csv("ALL_DATA_MERGED_updated.csv", encoding='utf-8-sig', low_memory=False)
main_df.columns = [str(c).replace('\ufeff', '').strip() for c in main_df.columns]

print(f"✅ 主數據：{len(main_df)} 行，{len(main_df.columns)} 欄")

# ===== 3. 統一鍵值格式 =====
print("\n🔧 統一日期、場次、馬匹編號格式...")

# 統一日期為 YYYY-MM-DD 字串
if 'race_date' in results_df.columns:
    results_df['race_date'] = pd.to_datetime(results_df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')
if 'race_date' in main_df.columns:
    main_df['race_date'] = pd.to_datetime(main_df['race_date'], errors='coerce').dt.strftime('%Y-%m-%d')

# 統一場次為字串
if 'race_no' in results_df.columns:
    results_df['race_no'] = results_df['race_no'].astype(str).str.strip()
if 'race_no' in main_df.columns:
    main_df['race_no'] = main_df['race_no'].astype(str).str.strip()

# 統一 horse_id 為字串（去除空格）
if 'horse_id' in results_df.columns:
    results_df['horse_id'] = results_df['horse_id'].astype(str).str.strip()
if 'horse_id' in main_df.columns:
    main_df['horse_id'] = main_df['horse_id'].astype(str).str.strip()

# ===== 4. 合併數據（以主數據為左表）=====
print("\n🔧 合併數據中...")

# 為了避免欄位名衝突，先將賽果數據嘅 finish_position 改名
results_df = results_df.rename(columns={'finish_position': 'finish_position_new'})

# 執行合併（左連接，保留主數據所有行）
merged = main_df.merge(
    results_df[['race_date', 'race_no', 'horse_id', 'finish_position_new']],
    on=['race_date', 'race_no', 'horse_id'],
    how='left'
)

# ===== 5. 更新 finish_position =====
# 如果主數據本身有 finish_position，而新賽果有數據，則以新賽果為準
if 'finish_position' in merged.columns:
    merged['finish_position'] = merged['finish_position_new'].combine_first(merged['finish_position'])
else:
    merged['finish_position'] = merged['finish_position_new']

# 刪除臨時欄位
merged = merged.drop(columns=['finish_position_new'])

# ===== 6. 統計結果 =====
matched = merged['finish_position'].notna().sum()
print(f"\n📊 合併結果：")
print(f"  主數據總行數：{len(main_df)}")
print(f"  成功匹配並更新 finish_position：{matched} 行")
print(f"  新增欄位數：0（只更新 finish_position）")

# ===== 7. 儲存（另存新檔，不覆蓋原檔）=====
output_file = "ALL_DATA_MERGED_updated_with_results.csv"
merged.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n✅ 已儲存到：{output_file}")
print(f"⚠️ 原檔 ALL_DATA_MERGED_updated.csv 完全冇改動！")