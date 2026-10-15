# aggregate_trackwork.py
# 將晨操數據聚合為「每匹馬、每場賽事一行」嘅特徵表
# ⚠️ 呢個腳本只會讀寫 CSV，絕對唔會影響網站同模型

import pandas as pd

# ===== 1. 讀取數據 =====
print("📂 讀取 trackwork_processed.csv...")
df = pd.read_csv("trackwork_processed.csv", encoding='utf-8-sig')
print(f"✅ 讀取到 {len(df)} 條記錄")

# ===== 2. 只保留有中文馬名嘅記錄 =====
df = df[df['horse_name_cn'].notna()].copy()
print(f"✅ 有中文馬名嘅記錄：{len(df)}")

# ===== 3. 標記操練類型 =====
df['Type'] = df['Type'].astype(str).str.strip()
df['is_gallop'] = df['Type'].str.lower().str.contains('gallop', na=False)
df['is_trotting'] = df['Type'].str.lower().str.contains('trotting', na=False)
df['is_race'] = df['Type'].str.lower().str.fullmatch('race', na=False)

print(f"\n📊 類型分佈：")
print(f"  Gallop（快操）：{df['is_gallop'].sum()}")
print(f"  Trotting（踱步）：{df['is_trotting'].sum()}")
print(f"  Race（試閘）：{df['is_race'].sum()}")

# ===== 4. 聚合：每匹馬 + 日期 + 場次 =====
print("\n🔧 聚合中...")
results = []

for (horse, date, race), group in df.groupby(['horse_name_cn', 'race_date', 'race_no'], dropna=True):
    row = {
        'horse_name_cn': horse,
        'race_date': int(date),
        'race_no': int(race),
    }

    # 操練次數
    row['total_workouts'] = len(group)
    row['gallop_count'] = int(group['is_gallop'].sum())
    row['trotting_count'] = int(group['is_trotting'].sum())
    row['race_count'] = int(group['is_race'].sum())

    # 快操時間特徵
    gallops = group[group['is_gallop'] & group['total_time'].notna()]
    if len(gallops) > 0:
        row['last_gallop_time'] = float(gallops.iloc[-1]['total_time'])
        row['fastest_gallop_time'] = float(gallops['total_time'].min())
        row['avg_gallop_time'] = round(float(gallops['total_time'].mean()), 2)
    else:
        row['last_gallop_time'] = None
        row['fastest_gallop_time'] = None
        row['avg_gallop_time'] = None

    # 有冇試閘
    row['has_trial'] = 1 if row['race_count'] > 0 else 0

    results.append(row)

agg_df = pd.DataFrame(results)
print(f"✅ 聚合後：{len(agg_df)} 行")

# ===== 5. 儲存 =====
output = "trackwork_aggregated.csv"
agg_df.to_csv(output, index=False, encoding='utf-8-sig')
print(f"\n✅ 已儲存到：{output}")

# ===== 6. 預覽 =====
print(f"\n📋 預覽前 10 行：")
print(agg_df.head(10).to_string(index=False))

print(f"\n📊 統計：")
print(f"  總行數：{len(agg_df)}")
print(f"  有快操記錄嘅：{(agg_df['gallop_count'] > 0).sum()}")
print(f"  有試閘記錄嘅：{agg_df['has_trial'].sum()}")
print(f"  有快操時間嘅：{agg_df['last_gallop_time'].notna().sum()}")