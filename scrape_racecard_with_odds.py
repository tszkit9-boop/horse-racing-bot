#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_with_odds.py - 完整版排位表及賠率爬蟲
功能：
  - 自動偵測賽馬日（星期三、六、日）
  - 支援單日 / 日期範圍
  - 真正爬取 HKJC 排位表數據（新版投注頁面）
  - 提取中文馬名、騎師、練馬師、檔位、賠率等
  - 支援爬取全日所有場次
  - 儲存為 HKCJ_FULL_YEAR_DATA.csv

用法：
  python scrape_racecard_with_odds.py --auto              # 自動爬今日（如果係賽馬日）
  python scrape_racecard_with_odds.py --date 2026-09-06   # 指定單日（爬所有場次）
  python scrape_racecard_with_odds.py --start 2025-09-07 --end 2026-07-15  # 日期範圍
  python scrape_racecard_with_odds.py --weekdays 2,5,6    # 只在星期二、五、六執行
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
import json
from bs4 import BeautifulSoup

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

OUTPUT_FILE = 'HKCJ_FULL_YEAR_DATA.csv'

# ============================================================
# 輔助函數
# ============================================================
def is_racing_day(date=None):
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    weekday = date.weekday()
    return weekday in [2, 5, 6]

def get_racing_days(start_date, end_date):
    racing_days = []
    current = start_date
    while current <= end_date:
        if is_racing_day(current):
            racing_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return racing_days

def get_random_headers():
    headers = HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers

def parse_date(date_str):
    return datetime.strptime(date_str.strip(), '%Y-%m-%d')

def safe_request(url, retry=3, timeout=30):
    for attempt in range(retry):
        try:
            headers = get_random_headers()
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response
            else:
                print(f"  ⚠️ 狀態碼 {response.status_code}，嘗試 {attempt+1}/{retry}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  ❌ 請求失敗：{e}，嘗試 {attempt+1}/{retry}")
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
    return None

# ============================================================
# 解析新版 HTML（單一場次）
# ============================================================
def parse_single_race_html(html_content, race_date, race_no):
    """
    解析新版投注頁面（單一場次）
    回傳 DataFrame
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.select('tr.rc-odds-row')
    if not rows:
        return pd.DataFrame()
    
    races = []
    for row in rows:
        try:
            # 馬名
            horse_name_elem = row.select_one('.horseName')
            horse_name = horse_name_elem.get_text(strip=True) if horse_name_elem else ''
            
            # 檔位
            draw_elem = row.select_one('.rc-odd-draw')
            draw = draw_elem.get_text(strip=True) if draw_elem else ''
            draw_num = re.search(r'(\d+)', draw)
            draw = draw_num.group(1) if draw_num else ''
            
            # 負磅
            wt_elem = row.select_one('.rc-odd-wt')
            weight = wt_elem.get_text(strip=True) if wt_elem else ''
            weight_num = re.search(r'(\d+)', weight)
            weight = weight_num.group(1) if weight_num else ''
            
            # 騎師
            jockey_elem = row.select_one('.jocky')
            jockey = jockey_elem.get_text(strip=True) if jockey_elem else ''
            
            # 練馬師
            trainer_elem = row.select_one('.trainer')
            trainer = trainer_elem.get_text(strip=True) if trainer_elem else ''
            
            # 賠率（Win Odds）
            odds_elem = row.select_one('.rc-odd-win')
            odds = odds_elem.get_text(strip=True) if odds_elem else ''
            odds_num = re.search(r'(\d+\.?\d*)', odds)
            odds = odds_num.group(1) if odds_num else ''
            
            races.append({
                '場次': race_no,
                '馬名': horse_name,
                '馬匹編號': '',  # 新頁面無直接提供
                '檔位': draw,
                '騎師': jockey,
                '練馬師': trainer,
                '實際負磅': weight,
                '賠率': odds,
                '比賽日期': race_date
            })
        except Exception as e:
            print(f"  ⚠️ 解析行失敗：{e}")
            continue
    return pd.DataFrame(races)

# ============================================================
# 核心爬取函數（改為爬所有場次）
# ============================================================
def fetch_racecard(date_str, retry=3):
    """
    爬取指定日期所有場次嘅排位表數據
    傳入日期字串 YYYY-MM-DD
    回傳 DataFrame（合併所有場次）
    """
    dt = parse_date(date_str)
    display_date = dt.strftime('%Y-%m-%d')
    
    # 方法1：嘗試 CSV（可能包晒全日）
    url_csv = f"https://racing.hkjc.com/racing/info/racecard/csv/racecard_{dt.strftime('%Y%m%d')}.csv"
    print(f"🔍 正在爬取 {display_date}（嘗試 CSV）...")
    response = safe_request(url_csv, retry=retry)
    if response:
        try:
            df = pd.read_csv(pd.io.common.StringIO(response.text))
            if '比賽日期' not in df.columns:
                df['比賽日期'] = display_date
            print(f"  ✅ 成功下載 CSV，共 {len(df)} 筆")
            return df
        except Exception as e:
            print(f"  ⚠️ CSV 解析失敗：{e}")
    
    # 方法2：逐場爬 HTML（新版投注頁面）
    print(f"  🐎 開始逐場爬取 HTML（新版投注頁面）...")
    all_dfs = []
    max_races = 12  # 通常最多12場
    
    for race_no in range(1, max_races + 1):
        url_html = f"https://bet.hkjc.com/ch/racing/home/{display_date}/ST/{race_no}"
        print(f"    ⏳ 爬取第 {race_no} 場...")
        response = safe_request(url_html, retry=retry)
        if not response:
            print(f"    ❌ 第 {race_no} 場請求失敗，停止")
            break
        
        df = parse_single_race_html(response.text, display_date, race_no)
        if df.empty:
            # 如果某場冇馬，通常代表之後都冇場次
            print(f"    ⏹️ 第 {race_no} 場無數據，停止")
            break
        
        print(f"    ✅ 第 {race_no} 場解析成功，共 {len(df)} 匹馬")
        all_dfs.append(df)
        time.sleep(random.uniform(0.5, 1.5))  # 避免請求太快
    
    if not all_dfs:
        print(f"  ❌ 無法爬取任何場次")
        return None
    
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"  ✅ 合併完成，共 {len(combined)} 筆記錄（{len(all_dfs)} 場）")
    return combined

# ============================================================
# 其餘函數（merge_racecard_data, save_to_csv, main）保持不變
# 但 merge 需略作調整以適應新欄位
# ============================================================
def merge_racecard_data(df):
    if df is None or df.empty:
        return None
    
    # 確保有基本欄位
    required_cols = ['馬名', '檔位', '騎師', '練馬師', '實際負磅', '比賽日期']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ''
    
    if '賠率' not in df.columns and 'win_odds' not in df.columns:
        df['賠率'] = ''
    
    df.rename(columns={
        '馬名': 'horse_name',
        '馬匹編號': 'horse_id',
        '檔位': 'draw',
        '騎師': 'jockey',
        '練馬師': 'trainer',
        '實際負磅': 'act_wt',
        '賠率': 'win_odds',
        '比賽日期': 'race_date'
    }, inplace=True, errors='ignore')
    
    if 'race_date' not in df.columns:
        df['race_date'] = ''
    
    return df

def save_to_csv(df, output_file=OUTPUT_FILE):
    if df is None or df.empty:
        print("❌ 無數據可儲存")
        return False
    
    if os.path.exists(output_file):
        try:
            existing = pd.read_csv(output_file, encoding='utf-8-sig')
            combined = pd.concat([existing, df], ignore_index=True)
            # 用 horse_name + race_date + 場次 做去重
            combined.drop_duplicates(subset=['horse_name', 'race_date', '場次'], keep='last', inplace=True)
            combined.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ 已合併數據至 {output_file}，共 {len(combined)} 筆")
            return True
        except Exception as e:
            print(f"⚠️ 合併失敗：{e}")
    
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 已儲存至 {output_file}，共 {len(df)} 筆")
    return True

# ============================================================
# 主程式（不變）
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='排位表及賠率爬蟲（完整版）')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auto', action='store_true', help='自動爬今日（如果係賽馬日）')
    group.add_argument('--date', type=str, help='指定單一日期，格式 YYYY-MM-DD')
    parser.add_argument('--start', type=str, help='開始日期，格式 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='結束日期，格式 YYYY-MM-DD')
    parser.add_argument('--weekdays', type=str, default='2,5,6', help='執行星期（1-7），預設 2,5,6')
    args = parser.parse_args()

    if args.weekdays:
        allowed_days = [int(x.strip()) for x in args.weekdays.split(',')]
        today_weekday = datetime.now().weekday() + 1
        if today_weekday not in allowed_days:
            print(f"⏭️ 今日星期 {today_weekday} 不在執行列表：{args.weekdays}")
            sys.exit(0)

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

    date_list = get_racing_days(start_date, end_date)
    if not date_list:
        print("⚠️ 所選範圍內沒有賽馬日")
        sys.exit(0)

    print(f"📋 共找到 {len(date_list)} 個賽馬日")

    all_data = []
    for idx, date_str in enumerate(date_list, 1):
        print(f"\n[{idx}/{len(date_list)}] 處理 {date_str}...")
        df = fetch_racecard(date_str)
        if df is not None and not df.empty:
            df = merge_racecard_data(df)
            all_data.append(df)
        time.sleep(random.uniform(1, 3))

    if not all_data:
        print("\n❌ 沒有成功獲取任何數據")
        sys.exit(1)

    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 合併完成，共 {len(combined)} 筆記錄")
    save_to_csv(combined)

    print(f"\n✅ 排位表更新完成！")
    print(f"📁 檔案位置：{os.path.abspath(OUTPUT_FILE)}")

if __name__ == '__main__':
    main()
