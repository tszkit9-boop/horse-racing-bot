#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_with_odds.py - 完整版排位表及賠率爬蟲
功能：
  - 自動偵測賽馬日（星期三、六、日）
  - 支援單日 / 日期範圍
  - 真正爬取 HKJC 排位表數據
  - 提取中文馬名、騎師、練馬師、檔位、賠率等
  - 儲存為 HKCJ_FULL_YEAR_DATA.csv

用法：
  python scrape_racecard_with_odds.py --auto              # 自動爬今日（如果係賽馬日）
  python scrape_racecard_with_odds.py --date 2026-07-15   # 指定單日
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

# 輸出檔案名
OUTPUT_FILE = 'HKCJ_FULL_YEAR_DATA.csv'

# ============================================================
# 輔助函數
# ============================================================
def is_racing_day(date=None):
    """檢查指定日期是否為賽馬日（星期三、六、日）"""
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    weekday = date.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    return weekday in [2, 5, 6]

def get_racing_days(start_date, end_date):
    """獲取日期範圍內嘅所有賽馬日"""
    racing_days = []
    current = start_date
    while current <= end_date:
        if is_racing_day(current):
            racing_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return racing_days

def get_random_headers():
    """隨機取一個 User-Agent"""
    headers = HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers

def parse_date(date_str):
    """解析日期字串，回傳 datetime 物件"""
    return datetime.strptime(date_str.strip(), '%Y-%m-%d')

def safe_request(url, retry=3, timeout=30):
    """安全請求，有重試機制"""
    for attempt in range(retry):
        try:
            headers = get_random_headers()
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response
            else:
                print(f"  ⚠️ 狀態碼 {response.status_code}，嘗試 {attempt+1}/{retry}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)  # 指數退避
        except Exception as e:
            print(f"  ❌ 請求失敗：{e}，嘗試 {attempt+1}/{retry}")
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
    return None

def parse_racecard_html(html_content, race_date):
    """
    從 HTML 解析排位表數據
    返回 DataFrame
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    races = []
    
    # 搵所有場次
    race_tables = soup.select('table.horseTable') or soup.select('table[class*="race"]')
    
    for race_idx, table in enumerate(race_tables, 1):
        rows = table.select('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            
            try:
                # 提取馬匹資料
                horse_name_elem = cells[0].find('a') or cells[0]
                horse_id_elem = cells[1] if len(cells) > 1 else None
                draw_elem = cells[2] if len(cells) > 2 else None
                jockey_elem = cells[3] if len(cells) > 3 else None
                trainer_elem = cells[4] if len(cells) > 4 else None
                weight_elem = cells[5] if len(cells) > 5 else None
                odds_elem = cells[6] if len(cells) > 6 else None
                
                horse_name = horse_name_elem.get_text(strip=True) if horse_name_elem else ''
                horse_id = horse_id_elem.get_text(strip=True) if horse_id_elem else ''
                draw = draw_elem.get_text(strip=True) if draw_elem else ''
                jockey = jockey_elem.get_text(strip=True) if jockey_elem else ''
                trainer = trainer_elem.get_text(strip=True) if trainer_elem else ''
                weight = weight_elem.get_text(strip=True) if weight_elem else ''
                odds = odds_elem.get_text(strip=True) if odds_elem else ''
                
                # 提取數字
                draw_num = re.search(r'(\d+)', draw)
                draw = draw_num.group(1) if draw_num else ''
                
                weight_num = re.search(r'(\d+)', weight)
                weight = weight_num.group(1) if weight_num else ''
                
                odds_num = re.search(r'(\d+\.?\d*)', odds)
                odds = odds_num.group(1) if odds_num else ''
                
                races.append({
                    '場次': race_idx,
                    '馬名': horse_name,
                    '馬匹編號': horse_id,
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

def fetch_racecard(date_str, retry=3):
    """
    爬取單日排位表數據
    傳入日期字串 YYYY-MM-DD
    回傳 DataFrame，若失敗則回傳 None
    """
    dt = parse_date(date_str)
    display_date = dt.strftime('%Y-%m-%d')
    
    # HKJC 排位表 URL（可能需要根據實際情況調整）
    # 方法1：嘗試 CSV 下載
    url_csv = f"https://racing.hkjc.com/racing/info/racecard/csv/racecard_{dt.strftime('%Y%m%d')}.csv"
    
    # 方法2：HTML 頁面
    url_html = f"https://racing.hkjc.com/racing/racinginfo/racecard.aspx?Lang=ch&RaceDate={dt.strftime('%Y%m%d')}"
    
    print(f"🔍 正在爬取 {display_date}...")
    
    # 先嘗試 CSV
    response = safe_request(url_csv, retry=retry)
    if response:
        try:
            df = pd.read_csv(pd.io.common.StringIO(response.text))
            df['比賽日期'] = display_date
            print(f"  ✅ 成功下載 CSV，共 {len(df)} 筆")
            return df
        except Exception as e:
            print(f"  ⚠️ CSV 解析失敗：{e}")
    
    # 如果 CSV 失敗，嘗試 HTML
    response = safe_request(url_html, retry=retry)
    if response:
        try:
            df = parse_racecard_html(response.text, display_date)
            if not df.empty:
                print(f"  ✅ 成功解析 HTML，共 {len(df)} 筆")
                return df
        except Exception as e:
            print(f"  ❌ HTML 解析失敗：{e}")
    
    # 模擬數據（如果爬蟲失敗，用現有數據模擬）
    # 注意：呢度只係示範，實際使用時應刪除呢部分
    print(f"  ⚠️ 無法爬取 {display_date}，嘗試使用模擬數據")
    try:
        # 嘗試從現有 full_data 讀取
        existing_files = [f for f in os.listdir('.') if f.startswith('full_data_') and display_date in f]
        if existing_files:
            df = pd.read_csv(existing_files[0])
            print(f"  ✅ 從 existing 載入 {len(df)} 筆")
            return df
    except:
        pass
    
    return None

def merge_racecard_data(df):
    """
    將爬取嘅數據合併並標準化
    """
    if df is None or df.empty:
        return None
    
    # 確保有基本欄位
    required_cols = ['馬名', '檔位', '騎師', '練馬師', '實際負磅', '比賽日期']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ''
    
    # 如果有賠率欄位
    if '賠率' not in df.columns and 'win_odds' not in df.columns:
        df['賠率'] = ''
    
    # 標準化欄位名
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
    
    # 確保有 race_date
    if 'race_date' not in df.columns:
        df['race_date'] = ''
    
    return df

def save_to_csv(df, output_file=OUTPUT_FILE):
    """儲存為 CSV，支援合併模式"""
    if df is None or df.empty:
        print("❌ 無數據可儲存")
        return False
    
    # 如果檔案存在，合併
    if os.path.exists(output_file):
        try:
            existing = pd.read_csv(output_file, encoding='utf-8-sig')
            # 合併並移除重複
            combined = pd.concat([existing, df], ignore_index=True)
            combined.drop_duplicates(subset=['horse_id', 'race_date', '場次'], keep='last', inplace=True)
            combined.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ 已合併數據至 {output_file}，共 {len(combined)} 筆")
            return True
        except Exception as e:
            print(f"⚠️ 合併失敗：{e}")
    
    # 直接儲存
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 已儲存至 {output_file}，共 {len(df)} 筆")
    return True

# ============================================================
# 主程式
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='排位表及賠率爬蟲（完整版）')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auto', action='store_true', help='自動爬取今日（如果係賽馬日）')
    group.add_argument('--date', type=str, help='指定單一日期，格式 YYYY-MM-DD')
    parser.add_argument('--start', type=str, help='開始日期，格式 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='結束日期，格式 YYYY-MM-DD')
    parser.add_argument('--weekdays', type=str, default='2,5,6', help='執行星期（1-7），預設 2,5,6')
    args = parser.parse_args()

    # 檢查今日是否在指定星期
    if args.weekdays:
        allowed_days = [int(x.strip()) for x in args.weekdays.split(',')]
        today_weekday = datetime.now().weekday() + 1  # 1=Mon, 7=Sun
        if today_weekday not in allowed_days:
            print(f"⏭️ 今日星期 {today_weekday} 不在執行列表：{args.weekdays}")
            sys.exit(0)

    # 決定日期範圍
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
        # 互動模式
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

    # 產生日期清單（只取賽馬日）
    date_list = get_racing_days(start_date, end_date)
    if not date_list:
        print("⚠️ 所選範圍內沒有賽馬日")
        sys.exit(0)

    print(f"📋 共找到 {len(date_list)} 個賽馬日")

    # 爬取每個日期
    all_data = []
    for idx, date_str in enumerate(date_list, 1):
        print(f"\n[{idx}/{len(date_list)}] 處理 {date_str}...")
        df = fetch_racecard(date_str)
        if df is not None and not df.empty:
            # 標準化數據
            df = merge_racecard_data(df)
            all_data.append(df)
        # 避免請求太快
        time.sleep(random.uniform(1, 3))

    if not all_data:
        print("\n❌ 沒有成功獲取任何數據")
        sys.exit(1)

    # 合併所有數據
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 合併完成，共 {len(combined)} 筆記錄")

    # 儲存
    save_to_csv(combined)

    print(f"\n✅ 排位表更新完成！")
    print(f"📁 檔案位置：{os.path.abspath(OUTPUT_FILE)}")

if __name__ == '__main__':
    main()
