#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_results.py - 爬取馬會賽果（永久保留）
用法: python scrape_results.py
"""

import os
import time
import re
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
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def fetch_single_race(driver, date_str, race_no):
    """爬取單場賽果（馬名、名次）"""
    url = f"https://bet.hkjc.com/ch/racing/results/2026-09-06/ST/1"
    print(f"  🌐 載入第 {race_no} 場: {url}")
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rc-odds-table"))
        )
    except:
        return None
    time.sleep(1)

    rows = driver.find_elements(By.CLASS_NAME, "rc-odds-row")
    if not rows:
        return None

    results = []
    for row in rows:
        try:
            name_elem = row.find_element(By.CLASS_NAME, "horseName")
            pos_elem = row.find_element(By.CLASS_NAME, "rc-odd-pos")
            pos_text = pos_elem.text.strip()
            if pos_text and pos_text != '-':
                pos = int(pos_text) if pos_text.isdigit() else None
                if pos is not None:
                    results.append({
                        'horse_name': name_elem.text.strip(),
                        'finish_position': pos,
                        'race_date': date_str,
                        'race_no': race_no
                    })
        except:
            continue
    return pd.DataFrame(results) if results else None

def fetch_results(date_str):
    """爬取指定日期所有場次賽果"""
    driver = get_driver()
    all_data = []
    try:
        for race_no in range(1, 13):  # 最多12場
            df = fetch_single_race(driver, date_str, race_no)
            if df is not None and not df.empty:
                all_data.append(df)
                print(f"  ✅ 第 {race_no} 場：{len(df)} 匹")
            else:
                # 如果連續兩場冇數據，可能已經完場
                if race_no > 2 and len(all_data) == 0:
                    break
            time.sleep(0.5)
    finally:
        driver.quit()
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return None

def main():
    # 爬昨日賽果（因為今日可能未跑完）
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"📅 正在爬取 {yesterday} 賽果...")

    df_new = fetch_results(yesterday)
    if df_new is None or df_new.empty:
        print("❌ 無新賽果數據")
        return

    output_file = "ALL_DATA_MERGED.csv"
    if os.path.exists(output_file):
        existing = pd.read_csv(output_file, encoding='utf-8-sig')
        combined = pd.concat([existing, df_new], ignore_index=True)
        combined.drop_duplicates(subset=['race_date', 'race_no', 'horse_name'], keep='last', inplace=True)
        print(f"📊 合併完成：原有 {len(existing)} 筆，新增 {len(df_new)} 筆，現有 {len(combined)} 筆")
    else:
        combined = df_new
        print(f"📊 新檔案：{len(combined)} 筆")

    combined.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 賽果已儲存至 {output_file}")

if __name__ == '__main__':
    main()
