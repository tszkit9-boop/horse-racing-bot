#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_results.py - 終極版賽果爬蟲（自動 Push + 數據去重 + 拆 horse_id）
"""

import os
import sys
import re
import time
import pandas as pd
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 香港時區
HK_TZ = timezone(timedelta(hours=8))


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def fetch_single_race(driver, date_str, racecourse, race_no):
    """爬取單場賽果（多重選擇器 + 去重 + 限制 14 匹 + 拆 horse_id）"""
    date_formatted = date_str.replace('-', '/')
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={date_formatted}&Racecourse={racecourse}&RaceNo={race_no}"
    print(f"  🌐 載入第 {race_no} 場: {url}")
    driver.get(url)

    time.sleep(3)

    page_text = driver.page_source
    if "賽事尚未舉行" in page_text or "賽事還未舉行" in page_text:
        print(f"  ⏳ 第 {race_no} 場賽事未跑")
        return None

    if "找不到" in page_text or "無此賽事" in page_text:
        print(f"  ❌ 第 {race_no} 場冇呢場賽事")
        return None

    results = []

    selectors = [
        "table.f_fs12 tr",
        "table.table_bd tr",
        "table tr",
    ]

    rows = []
    for sel in selectors:
        rows = driver.find_elements(By.CSS_SELECTOR, sel)
        if len(rows) > 5:
            print(f"  📋 使用選擇器: {sel}（{len(rows)} 行）")
            break

    if not rows:
        print(f"  ⚠️ 第 {race_no} 場搵唔到表格")
        return None

    for row in rows:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:
                continue
            pos_text = cells[0].text.strip()
            if not pos_text or not pos_text.isdigit():
                continue
            raw_name = cells[2].text.strip()
            if raw_name:
                # 🛡️ 拆 "藤王駒 (K143)" → horse_name="藤王駒", horse_id="K143"
                m = re.match(r'^(.+?)\s*\(([A-Z]\d+)\)\s*$', raw_name)
                if m:
                    horse_name = m.group(1).strip()
                    horse_id = m.group(2).strip()
                else:
                    horse_name = raw_name
                    horse_id = ''
                results.append({
                    'race_date': date_str,
                    'race_no': race_no,
                    'horse_name': horse_name,
                    'horse_id': horse_id,
                    'finish_position': int(pos_text)
                })
        except Exception:
            continue

    # 🛡️ 關鍵修正：去重 + 限制最多 14 匹馬
    seen_horses = set()
    cleaned_results = []
    for r in results:
        if r['horse_name'] not in seen_horses:
            seen_horses.add(r['horse_name'])
            cleaned_results.append(r)
    results = cleaned_results[:14]  # 只保留頭 14 匹

    if results:
        print(f"  ✅ 第 {race_no} 場：{len(results)} 匹")
    else:
        print(f"  ⚠️ 第 {race_no} 場解析唔到馬名")

    return pd.DataFrame(results) if results else None


def fetch_results(date_str, racecourse):
    """爬取指定日期同馬場嘅所有場次"""
    driver = get_driver()
    all_data = []
    try:
        for race_no in range(1, 13):
            df = fetch_single_race(driver, date_str, racecourse, race_no)
            if df is not None and not df.empty:
                all_data.append(df)
            else:
                if race_no > 2 and len(all_data) == 0:
                    break
            time.sleep(0.5)
    finally:
        driver.quit()

    return pd.concat(all_data, ignore_index=True) if all_data else None


def fetch_date_range(start_date, end_date):
    """🆕 爬指定日期範圍內所有賽馬日（只試星期二、三、六、日）"""
    all_data = []
    current = start_date
    while current <= end_date:
        weekday = current.weekday()
        # 只試星期二、三、六、日（香港賽馬日）
        if weekday in [1, 2, 5, 6]:
            date_str = current.strftime('%Y-%m-%d')
            racecourse = 'HV' if weekday == 2 else 'ST'
            print(f"\n📅 爬取 {date_str} ({racecourse})...")
            df = fetch_results(date_str, racecourse)
            if df is not None and not df.empty:
                all_data.append(df)
            else:
                print(f"  ⚠️ {date_str} 冇賽果")
        current += timedelta(days=1)

    return pd.concat(all_data, ignore_index=True) if all_data else None


def try_fetch_multiple_days():
    """自動試最近 7 日，搵到有賽事嘅日子為止"""
    now_hk = datetime.now(HK_TZ)
    for days_back in range(1, 8):
        target = now_hk - timedelta(days=days_back)
        date_str = target.strftime('%Y-%m-%d')
        weekday = target.weekday()

        racecourse = 'HV' if weekday == 2 else 'ST'

        # 只試星期二、三、六、日（香港賽馬日）
        if weekday not in [1, 2, 5, 6]:
            print(f"⏭️ {date_str} 非賽馬日，跳過")
            continue

        print(f"\n📅 嘗試爬取 {date_str} ({racecourse})...")
        df = fetch_results(date_str, racecourse)
        if df is not None and not df.empty:
            return df
        print(f"  ⚠️ {date_str} 冇賽果，試前一日...")

    return None


def merge_and_save(df_new, output_file="race_results_clean.csv"):
    """合併新舊數據並儲存"""
    if os.path.exists(output_file):
        existing = pd.read_csv(output_file, encoding='utf-8-sig')
        existing.columns = [str(c).replace('\ufeff', '').strip() for c in existing.columns]
        existing['race_date'] = existing['race_date'].astype(str).str[:10]

        # 🛡️ 確保舊數據有 horse_id 欄
        if 'horse_id' not in existing.columns:
            existing['horse_id'] = ''

        # 🛡️ 先刪除同一日期嘅舊數據，避免重複
        existing = existing[~existing['race_date'].isin(df_new['race_date'].unique())]

        combined = pd.concat([existing, df_new], ignore_index=True)
        combined.drop_duplicates(subset=['race_date', 'race_no', 'horse_name'], keep='first', inplace=True)

        # 🛡️ 統一欄位順序
        cols = ['race_date', 'race_no', 'horse_name', 'horse_id', 'finish_position']
        for c in combined.columns:
            if c not in cols:
                cols.append(c)
        combined = combined[[c for c in cols if c in combined.columns]]

        print(f"\n📊 合併完成：保留 {len(existing)} 筆舊數據，新增 {len(df_new)} 筆，現有 {len(combined)} 筆")
    else:
        combined = df_new
        print(f"\n📊 新檔案：{len(combined)} 筆")

    combined.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 賽果已儲存至 {output_file}")


def main():
    # 🆕 模式 1：爬日期範圍  python scrape_results.py --range 2026-01-01 2026-09-13
    if len(sys.argv) >= 4 and sys.argv[1] == '--range':
        try:
            start = datetime.strptime(sys.argv[2], '%Y-%m-%d')
            end = datetime.strptime(sys.argv[3], '%Y-%m-%d')
        except ValueError:
            print("❌ 日期格式錯誤，請用 YYYY-MM-DD")
            return
        print(f"📅 爬取範圍：{start.date()} 至 {end.date()}")
        df_new = fetch_date_range(start, end)

    # 模式 2：手動指定一日  python scrape_results.py 2026-09-16 ST
    elif len(sys.argv) >= 3:
        date_str = sys.argv[1]
        racecourse = sys.argv[2].upper()
        print(f"📅 手動指定：{date_str} ({racecourse})")
        df_new = fetch_results(date_str, racecourse)

    # 模式 3：自動搜尋最近 7 日（原本行為）
    else:
        print(f"📅 自動搜尋最近有賽事嘅日子...")
        df_new = try_fetch_multiple_days()

    if df_new is None or df_new.empty:
        print("❌ 冇新賽果數據")
        return

    merge_and_save(df_new)


if __name__ == '__main__':
    main()
