#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_selenium.py - 爬取馬會排位表（含賠率）
用法:
  python scrape_racecard_selenium.py --date 2026-09-13
"""

import os
import time
import re
import argparse
import pandas as pd
from datetime import datetime
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


def get_venue(driver, date_str):
    """從 racecard 頁面提取場地縮寫 (ST / HV)"""
    for venue in ['ST', 'HV']:
        date_fmt = date_str.replace('-', '/')
        url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={date_fmt}&Racecourse={venue}&RaceNo=1"
        try:
            driver.get(url)
            time.sleep(2)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "沙田" in body_text:
                return "ST"
            elif "跑馬地" in body_text:
                return "HV"
        except Exception:
            continue
    return "ST"


def fetch_single_race(driver, date_str, venue, race_no):
    """爬取單一場次排位表"""
    date_fmt = date_str.replace('-', '/')
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={date_fmt}&Racecourse={venue}&RaceNo={race_no}"
    print(f"  🌐 載入: {url}")
    driver.get(url)
    time.sleep(2)

    # 檢查有冇賽事
    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "賽事尚未公佈" in body_text or "無此賽事" in body_text or "找不到" in body_text:
        return None

    # 嘗試搵表格
    rows = []
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_bd"))
        )
        tables = driver.find_elements(By.CSS_SELECTOR, "table.table_bd")
        if tables:
            rows = tables[0].find_elements(By.TAG_NAME, "tr")
    except Exception:
        pass

    if not rows:
        # Fallback: 試其他 selector
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        except Exception:
            pass

    if not rows or len(rows) < 3:
        return None

    results = []
    for row in rows:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                continue

            # 試下解析：通常格式係 馬號 | 馬名 | 騎師 | 練馬師 | 檔位 | 負磅 | 賠率
            no_text = cells[0].text.strip()
            if not no_text or not no_text.isdigit():
                continue

            results.append({
                '馬號': no_text,
                '馬名': cells[1].text.strip() if len(cells) > 1 else '',
                '騎師': cells[2].text.strip() if len(cells) > 2 else '',
                '練馬師': cells[3].text.strip() if len(cells) > 3 else '',
                '檔位': cells[4].text.strip() if len(cells) > 4 else '',
                '負磅': cells[5].text.strip() if len(cells) > 5 else '',
                '賠率': cells[6].text.strip() if len(cells) > 6 else '',
                '場次': race_no,
                '比賽日期': date_str
            })
        except Exception:
            continue

    return pd.DataFrame(results) if results else None


def fetch_all_races(date_str, max_race=15):
    print(f"📅 開始爬取 {date_str} 嘅排位表")
    driver = get_driver()
    all_dfs = []

    try:
        venue = get_venue(driver, date_str)
        print(f"📋 場地：{venue}")

        for race_no in range(1, max_race + 1):
            print(f"\n⏳ 正在檢查第 {race_no} 場...")
            df = fetch_single_race(driver, date_str, venue, race_no)
            if df is None or df.empty:
                print(f"  ⏹️ 第 {race_no} 場無數據，停止")
                break
            print(f"  ✅ 第 {race_no} 場有 {len(df)} 匹馬")
            all_dfs.append(df)
            time.sleep(0.5)
    finally:
        driver.quit()

    if not all_dfs:
        return None, venue
    return pd.concat(all_dfs, ignore_index=True), venue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='YYYY-MM-DD')
    parser.add_argument('--max-race', type=int, default=15)
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except Exception:
        print("❌ 日期格式錯誤")
        return

    df, venue = fetch_all_races(args.date, max_race=args.max_race)
    if df is None or df.empty:
        print("❌ 冇任何數據")
        return

    output_file = f"racecard_{args.date}_{venue}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    df.to_csv("racecard_uploaded.csv", index=False, encoding='utf-8-sig')

    actual_races = df['場次'].nunique()
    print(f"\n✅ 已儲存至 {output_file} 同 racecard_uploaded.csv")
    print(f"📊 總共成功爬取 {actual_races} 場，合共 {len(df)} 匹馬")


if __name__ == '__main__':
    main()
