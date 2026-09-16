#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_results.py - 爬取馬會賽果（自動判斷日期同馬場，防止重覆場次）
用法:
    python scrape_results.py              # 自動爬昨日賽果
    python scrape_results.py 2026-09-16 HV  # 手動指定日期同馬場
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


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
    url = f"https://bet.hkjc.com/ch/racing/results/{date_str}/{racecourse}/{race_no}"
    print(f"  🌐 載入第 {race_no} 場: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rc-odds-table"))
        )
    except Exception:
        return None

    time.sleep(1)
    results = []
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.rc-odds-table tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:
                continue
            pos_text = cells[0].text.strip()
            if not pos_text or not pos_text.isdigit():
                continue
            horse_name = cells[2].text.strip()
            if horse_name:
                results.append({
                    'race_date': date_str,
                    'race_no': race_no,
                    'horse_name': horse_name,
                    'finish_position': int(pos_text)
                })
    except Exception as e:
        print(f"  ⚠️ 解析失敗: {e}")
        return None

    return pd.DataFrame(results) if results else None


def fetch_results(date_str, racecourse):
    driver = get_driver()
    all_data = []
    try:
        for race_no in range(1, 13):
            df = fetch_single_race(driver, date_str, racecourse, race_no)
            if df is not None and not df.empty:
                all_data.append(df)
                print(f"  ✅ 第 {race_no} 場：{len(df)} 匹")
            else:
                print(f"  ⚠️ 第 {race_no} 場無數據")
                if race_no > 2 and len(all_data) == 0:
                    break
            time.sleep(0.5)
    finally:
        driver.quit()

    return pd.concat(all_data, ignore_index=True) if all_data else None


def main():
    if len(sys.argv) >= 3:
        date_str = sys.argv[1]
        racecourse = sys.argv[2].upper()
    else:
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()
        racecourse = 'HV' if weekday == 2 else 'ST'

    print(f"📅 正在爬取 {date_str} ({racecourse}) 賽果...")

    df_new = fetch_results(date_str, racecourse)
    if df_new is None or df_new.empty:
        print("❌ 無新賽果數據")
        return

    output_file = "race_results_clean.csv"

    if os.path.exists(output_file):
        existing = pd.read_csv(output_file, encoding='utf-8-sig')
        existing.columns = [str(c).replace('\ufeff', '').strip() for c in existing.columns]
        existing['race_date'] = existing['race_date'].astype(str).str[:10]

        # 🛡️ 先刪除同一日期嘅舊數據，避免重覆
        existing = existing[~existing['race_date'].isin(df_new['race_date'].unique())]

        combined = pd.concat([existing, df_new], ignore_index=True)
        combined.drop_duplicates(subset=['race_date', 'race_no', 'horse_name'], keep='first', inplace=True)

        print(f"📊 合併完成：保留 {len(existing)} 筆舊數據，新增 {len(df_new)} 筆，現有 {len(combined)} 筆")
    else:
        combined = df_new
        print(f"📊 新檔案：{len(combined)} 筆")

    combined.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 賽果已儲存至 {output_file}")


if __name__ == '__main__':
    main()
