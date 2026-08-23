#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_with_odds.py - 排位表及賠率爬蟲（支援自動賽馬日檢查）
"""

import sys
import os
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import re

# ============================================================
# 設定
# ============================================================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
]
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# ============================================================
# 輔助函數
# ============================================================
def is_racing_day(date=None):
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    weekday = date.weekday()
    return weekday in [2, 5, 6]  # 三、六、日

def get_random_headers():
    headers = HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers

def parse_date(date_str):
    return datetime.strptime(date_str.strip(), '%Y-%m-%d')

def fetch_racecard(date_str, retry=3):
    dt = parse_date(date_str)
    url_date = dt.strftime('%Y%m%d')
    display_date = dt.strftime('%Y-%m-%d')
    url = f"https://racing.hkjc.com/racing/info/racecard/csv/racecard_{url_date}.csv"
    for attempt in range(retry):
        try:
            headers = get_random_headers()
            print(f"  嘗試 {attempt+1}/{retry}：下載 {display_date}...")
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                df = pd.read_csv(pd.io.common.StringIO(response.text))
                df['比賽日期'] = display_date
                print(f"  ✅ 成功下載 {display_date}，共 {len(df)} 筆")
                return df
            else:
                print(f"  ⚠️ 狀態碼 {response.status_code}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  ❌ 錯誤：{e}")
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
    return None

# ============================================================
# 主程式
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='排位表及賠率爬蟲')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auto', action='store_true', help='自動爬取今日（如果係賽馬日）')
    group.add_argument('--date', type=str, help='指定單一日期，格式 YYYY-MM-DD')
    parser.add_argument('--start', type=str, help='開始日期')
    parser.add_argument('--end', type=str, help='結束日期')
    args = parser.parse_args()

    start_date = None
    end_date = None

    if args.auto:
        today = datetime.now().date()
        if is_racing_day(today):
            start_date = today
            end_date = today
            print(f"📅 今日 ({today}) 係賽馬日，開始爬取")
        else:
            print("📅 今日唔係賽馬日，跳過")
            sys.exit(0)
    elif args.date:
        dt = parse_date(args.date)
        start_date = dt
        end_date = dt
        print(f"📅 指定日期：{args.date}")
    elif args.start and args.end:
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
        print(f"📅 日期範圍：{args.start} 至 {args.end}")
    else:
        date_input = input("請輸入日期 (YYYY-MM-DD): ").strip()
        try:
            dt = parse_date(date_input)
            start_date = dt
            end_date = dt
        except:
            print("❌ 日期格式錯誤")
            sys.exit(1)

    if start_date is None or end_date is None:
        print("❌ 無效日期")
        sys.exit(1)

    if start_date > end_date:
        print("❌ 開始日期不能大於結束日期")
        sys.exit(1)

    date_list = []
    current = start_date
    while current <= end_date:
        if is_racing_day(current):
            date_list.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    if not date_list:
        print("⚠️ 所選範圍內沒有賽馬日")
        sys.exit(0)

    print(f"📋 共找到 {len(date_list)} 個賽馬日")

    all_data = []
    for idx, date_str in enumerate(date_list, 1):
        print(f"\n[{idx}/{len(date_list)}] 處理 {date_str}...")
        df = fetch_racecard(date_str)
        if df is not None and not df.empty:
            all_data.append(df)
        time.sleep(random.uniform(1, 3))

    if not all_data:
        print("\n❌ 沒有成功獲取任何數據")
        sys.exit(1)

    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 合併完成，共 {len(combined)} 筆記錄")

    output_file = 'HKCJ_FULL_YEAR_DATA.csv'
    combined.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 已儲存至 {output_file}")

if __name__ == '__main__':
    main()
