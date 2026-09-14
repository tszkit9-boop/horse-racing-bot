import pandas as pd

print("📊 讀取歷史數據...")
df = pd.read_csv("ALL_DATA_MERGED.csv", encoding='utf-8-sig', low_memory=False)

# 確保有 horse_name 同 horse_id 呢兩欄
if 'horse_name' not in df.columns or 'horse_id' not in df.columns:
    print("❌ 找不到 horse_name 或 horse_id 欄位！")
    exit(1)

# 去除重複，只保留唯一嘅「中文馬名 -> 馬匹編號」對應
mapping = df[['horse_name', 'horse_id']].dropna().drop_duplicates()

# 清理空格
mapping['horse_name'] = mapping['horse_name'].astype(str).str.strip()
mapping['horse_id'] = mapping['horse_id'].astype(str).str.strip()

# 儲存為 CSV
mapping.to_csv("horse_name_mapping.csv", index=False, encoding='utf-8-sig')
print(f"✅ 成功生成 horse_name_mapping.csv，共 {len(mapping)} 條對照記錄！")
