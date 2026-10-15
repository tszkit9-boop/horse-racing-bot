# scrape_trackwork_full.py
# 爬取所有晨操記錄
# ⚠️ 呢個係獨立爬蟲，唔會影響網站

import requests
import pandas as pd
import json
import time
import os
from datetime import datetime, timedelta

# ===== 設定 =====
START_DATE = "2024-09-01"          # 開始日期
END_DATE = "2026-10-14"            # 結束日期
OUTPUT_FILE = "trackwork_all.csv"  # 輸出檔案
DELAY_SECONDS = 1.5                # 每次請求之間嘅延遲（避免封 IP）

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
    "Referer": "https://racing.hkjc.com/zh-hk/local/information/localtrackwork",
    "X-Requested-With": "XMLHttpRequest",
}

def get_race_dates(start, end):
    """產生所有星期三同日（賽馬日）"""
    dates = []
    d = datetime.strptime(start, "%Y-%m-%d")
    end_d = datetime.strptime(end, "%Y-%m-%d")
    while d <= end_d:
        # 星期三（weekday=2）= 跑馬地，星期日（weekday=6）= 沙田
        if d.weekday() in [2, 6]:
            dates.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return dates

def scrape_one_race(date_str, race_no, page_num=1):
    """爬取一場賽事嘅晨操數據"""
    url = f"https://racing.hkjc.com/racing/information/json/TrackworkOneDayRecords/{date_str}{race_no}E.aspx?PageNum={page_num}"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            return data.get('Records', [])
    except Exception as e:
        print(f"  ⚠️ {date_str} 第 {race_no} 場失敗：{e}")
    return []

def main():
    print(f"🚀 開始爬取晨操：{START_DATE} 至 {END_DATE}")
    dates = get_race_dates(START_DATE, END_DATE)
    print(f"📅 共 {len(dates)} 個賽馬日\n")
    
    all_records = []
    
    for i, date_str in enumerate(dates):
        print(f"[{i+1}/{len(dates)}] 爬取 {date_str}...")
        
        # 爬取該日嘅所有場次（先試 1-11 場）
        for race_no in range(1, 12):
            records = scrape_one_race(date_str, race_no)
            if records:
                for r in records:
                    r['race_date'] = date_str
                    r['race_no'] = race_no
                all_records.extend(records)
                print(f"  ✅ 第 {race_no} 場：{len(records)} 條")
            time.sleep(DELAY_SECONDS)  # 延遲，避免封 IP
        
        # 每爬完一日，儲存一次（防止中途斷線）
        if all_records:
            df = pd.DataFrame(all_records)
            df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ 完成！共爬取 {len(all_records)} 條晨操紀錄")
    print(f"📁 已儲存到：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()