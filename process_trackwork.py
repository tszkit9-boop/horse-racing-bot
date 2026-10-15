# process_trackwork.py
# 清洗晨操數據：英文馬名 → 中文馬名 + 拆解時間格式
# ⚠️ 呢個腳本只係讀寫 CSV，唔會影響網站

import pandas as pd
import re

# ===== 1. 讀取原始數據 =====
print("📂 讀取 trackwork_all.csv...")
df = pd.read_csv("trackwork_all.csv", encoding='utf-8-sig')
print(f"✅ 讀取到 {len(df)} 條紀錄")

# ===== 2. 讀取對照表 =====
print("\n📂 讀取馬名對照表...")
en_map = pd.read_csv("horse_name_mapping.csv", encoding='utf-8-sig')
cn_map = pd.read_csv("horse_name_mapping_cn.csv", encoding='utf-8-sig')
print(f"✅ 英文對照表：{len(en_map)} 條")
print(f"✅ 中文對照表：{len(cn_map)} 條")

# 統一欄位格式
en_map.columns = [str(c).replace('\ufeff', '').strip() for c in en_map.columns]
cn_map.columns = [str(c).replace('\ufeff', '').strip() for c in cn_map.columns]

# 建立英文馬名 → horse_id 嘅 lookup
en_map['horse_name'] = en_map['horse_name'].astype(str).str.strip().str.upper()
en_to_id = dict(zip(en_map['horse_name'], en_map['horse_id'].astype(str).str.strip()))

# 建立 horse_id → 中文馬名 嘅 lookup
id_to_cn = dict(zip(cn_map['horse_id'].astype(str).str.strip(), cn_map['horse_name_cn']))

print(f"✅ 英文→ID 對照：{len(en_to_id)} 條")
print(f"✅ ID→中文 對照：{len(id_to_cn)} 條")

# ===== 3. 將英文馬名轉為中文馬名 =====
def translate_horse(en_name):
    if pd.isna(en_name):
        return None, None
    key = str(en_name).strip().upper()
    horse_id = en_to_id.get(key)
    cn_name = id_to_cn.get(horse_id) if horse_id else None
    return horse_id, cn_name

print("\n🔧 轉換馬名中...")
df[['horse_id', 'horse_name_cn']] = df['Horse'].apply(
    lambda x: pd.Series(translate_horse(x))
)

matched = df['horse_name_cn'].notna().sum()
print(f"✅ 成功匹配：{matched} / {len(df)}（{matched/len(df)*100:.1f}%）")

# ===== 4. 拆解 Workouts 欄位 =====
def parse_workout(workout_str):
    """將 '29.3 24.4 (53.7) (R.B.)' 拆做數字特徵"""
    if pd.isna(workout_str):
        return pd.Series([None, None, None, 0])
    s = str(workout_str).strip()
    seg1 = seg2 = total = None
    total_match = re.search(r'\((\d+\.\d+)\)', s)
    if total_match:
        total = float(total_match.group(1))
    times = re.findall(r'\b(\d+\.\d+)\b', s)
    if len(times) >= 1:
        seg1 = float(times[0])
    if len(times) >= 2:
        seg2 = float(times[1])
    has_time = 1 if total is not None else 0
    return pd.Series([seg1, seg2, total, has_time])

print("\n🔧 拆解操練時間...")
df[['seg1_time', 'seg2_time', 'total_time', 'has_time']] = df['Workouts'].apply(parse_workout)

# ===== 5. 統計 =====
print(f"\n📊 統計：")
print(f"  總紀錄：{len(df)}")
print(f"  成功轉中文馬名：{matched}")
print(f"  有時間數據：{df['has_time'].sum()}")

# ===== 6. 儲存 =====
output_file = "trackwork_processed.csv"
df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n✅ 已儲存到：{output_file}")

# ===== 7. 預覽 =====
print(f"\n📋 預覽前 5 條（睇下馬名轉換）：")
preview = df[['Horse', 'horse_id', 'horse_name_cn', 'Type', 'total_time']].head()
print(preview.to_string(index=False))