# merge_trackwork.py
# 將晨操特徵合併入主數據（另存新檔，唔會覆蓋原檔）
# ⚠️ 只讀取，唔會修改任何現有檔案

import pandas as pd

# ===== 1. 讀取主數據 =====
print("📂 讀取 ALL_DATA_MERGED_updated.csv...")
main = pd.read_csv("ALL_DATA_MERGED_updated.csv", encoding='utf-8-sig', low_memory=False)
main.columns = [str(c).replace('\ufeff', '').strip() for c in main.columns]
print(f"✅ 主數據：{len(main)} 行，{len(main.columns)} 欄")

# ===== 2. 讀取晨操聚合數據 =====
print("\n📂 讀取 trackwork_aggregated.csv...")
tw = pd.read_csv("trackwork_aggregated.csv", encoding='utf-8-sig')
tw.columns = [str(c).replace('\ufeff', '').strip() for c in tw.columns]
print(f"✅ 晨操數據：{len(tw)} 行")

# ===== 3. 讀取中文馬名 → horse_id 對照表 =====
print("\n📂 讀取 horse_name_mapping_cn.csv...")
cn_map = pd.read_csv("horse_name_mapping_cn.csv", encoding='utf-8-sig')
cn_map.columns = [str(c).replace('\ufeff', '').strip() for c in cn_map.columns]
id_to_cn = dict(zip(cn_map['horse_id'].astype(str).str.strip(), cn_map['horse_name_cn']))
cn_to_id = {v: k for k, v in id_to_cn.items()}
print(f"✅ 對照表：{len(cn_to_id)} 條")

# ===== 4. 統一日期格式同類型 =====
print("\n🔧 統一日期格式同數據類型...")
main['race_date'] = pd.to_datetime(main['race_date'], errors='coerce')
main['race_date_int'] = main['race_date'].dt.strftime('%Y%m%d').astype(str)

# 主數據嘅 race_no 轉做文字
main['race_no'] = main['race_no'].astype(str).str.strip()

# 晨操數據嘅 race_date 同 race_no 都轉做文字
tw['race_date'] = tw['race_date'].astype(str).str.strip()
tw['race_no'] = tw['race_no'].astype(str).str.strip()

# ===== 5. 將晨操數據嘅中文馬名轉做 horse_id =====
print("🔧 轉換晨操數據嘅馬名...")
tw['horse_id'] = tw['horse_name_cn'].map(cn_to_id)
matched = tw['horse_id'].notna().sum()
print(f"✅ 成功匹配 horse_id：{matched} / {len(tw)}")

# ===== 6. 準備合併 =====
tw_for_merge = tw[tw['horse_id'].notna()].copy()
tw_for_merge['race_date_str'] = tw_for_merge['race_date'].astype(str)

# 只保留需要嘅特徵欄位
feature_cols = ['total_workouts', 'gallop_count', 'trotting_count', 'race_count',
                'last_gallop_time', 'fastest_gallop_time', 'avg_gallop_time', 'has_trial']
tw_features = tw_for_merge[['horse_id', 'race_date_str', 'race_no'] + feature_cols].copy()

# 重新命名欄位，加上 tw_ 前綴，避免同主數據撞名
tw_features = tw_features.rename(columns={c: f'tw_{c}' for c in feature_cols})

print(f"\n📊 準備合併：{len(tw_features)} 行晨操特徵")

# ===== 7. 合併 =====
print("\n🔧 合併中...")
merged = main.merge(
    tw_features,
    left_on=['horse_id', 'race_date_int', 'race_no'],
    right_on=['horse_id', 'race_date_str', 'race_no'],
    how='left'
)

# 刪除多餘嘅臨時欄位
merged = merged.drop(columns=['race_date_str'], errors='ignore')

# ===== 8. 統計 =====
matched_rows = merged['tw_total_workouts'].notna().sum()
print(f"\n📊 合併結果：")
print(f"  主數據總行數：{len(main)}")
print(f"  成功合併晨操特徵：{matched_rows} 行（{matched_rows/len(main)*100:.1f}%）")

# ===== 9. 儲存（另存新檔，唔覆蓋原檔）=====
output = "ALL_DATA_MERGED_with_trackwork.csv"
merged.to_csv(output, index=False, encoding='utf-8-sig')
print(f"\n✅ 已儲存到：{output}")
print(f"⚠️ 原檔 ALL_DATA_MERGED_updated.csv 完全冇改動！")
print(f"\n📋 新檔案欄位數：{len(merged.columns)}（原檔 119 欄 + 8 個 tw_ 特徵 = 127 欄）")