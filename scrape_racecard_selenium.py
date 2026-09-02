#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_selenium.py - 爬取馬會投注頁面所有真實場次（含賠率，自動分辨場地）
用法:
  python scrape_racecard_selenium.py --date 2026-09-06
  python scrape_racecard_selenium.py --date 2026-09-06 --max-race 15
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

def fetch_single_race(driver, date_str, race_no):
    """爬取單一場次詳細數據（含賠率），回傳 DataFrame，若無效則回傳 None"""
    url = f"https://bet.hkjc.com/ch/racing/home/{date_str}/ST/{race_no}"
    print(f"  🌐 載入: {url}")
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rc-odds-table"))
        )
    except:
        return None
    time.sleep(0.8)
    rows = driver.find_elements(By.CLASS_NAME, "rc-odds-row")
    if not rows:
        return None

    results = []
    for row in rows:
        try:
            no_elem = row.find_element(By.CLASS_NAME, "rc-no")
            name_elem = row.find_element(By.CLASS_NAME, "horseName")
            draw_elem = row.find_element(By.CLASS_NAME, "rc-odd-draw")
            wt_elem = row.find_element(By.CLASS_NAME, "rc-odd-wt")
            jockey_elem = row.find_element(By.CLASS_NAME, "jocky")
            trainer_elem = row.find_element(By.CLASS_NAME, "trainer")
            odds_elem = row.find_element(By.CLASS_NAME, "rc-odd-win")
            odds = odds_elem.text.strip() if odds_elem else ''

            results.append({
                '馬號': no_elem.text.strip(),
                '馬名': name_elem.text.strip(),
                '檔位': draw_elem.text.strip(),
                '負磅': wt_elem.text.strip(),
                '騎師': jockey_elem.text.strip(),
                '練馬師': trainer_elem.text.strip(),
                '賠率': odds,
                '場次': race_no,
                '比賽日期': date_str
            })
        except:
            continue
    return pd.DataFrame(results)

def is_real_race(df, reference_df):
    """
    判斷一個場次係咪真實場次：
    - 如果馬名同 reference 場次（第1場）完全相同，則視為假數據（因為馬會冇賽事時會複製第1場）
    - 如果馬匹數量少於 3，亦視為假
    """
    if df is None or df.empty:
        return False
    if len(df) < 3:
        return False
    # 比對馬名是否與第1場完全相同
    if reference_df is not None and not reference_df.empty:
        ref_names = set(reference_df['馬名'])
        current_names = set(df['馬名'])
        if current_names == ref_names:
            return False
    return True

def get_venue(driver, date_str):
    """從第一場頁面提取場地縮寫 (ST / HV)"""
    url = f"https://bet.hkjc.com/ch/racing/home/{date_str}/ST/1"
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "meeting-info"))
        )
    except:
        return "ST"  # fallback
    time.sleep(1)
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "沙田" in body_text:
            return "ST"
        elif "跑馬地" in body_text:
            return "HV"
        else:
            return "ST"
    except:
        return "ST"

def fetch_all_races(date_str, max_race=15):
    print(f"📅 開始爬取 {date_str} 嘅所有真實場次（含賠率）")
    driver = get_driver()
    all_dfs = []
    reference_df = None
    venue = get_venue(driver, date_str)
    print(f"📋 場地：{venue}")

    try:
        for race_no in range(1, max_race + 1):
            print(f"\n⏳ 正在檢查第 {race_no} 場...")
            df = fetch_single_race(driver, date_str, race_no)
            if df is None or df.empty:
                print(f"  ⏹️ 第 {race_no} 場無數據，停止")
                break

            # 用第1場做參考，判斷真偽
            if race_no == 1:
                reference_df = df
                print(f"  ✅ 第 1 場有 {len(df)} 匹馬（作為參考）")
                all_dfs.append(df)
                continue

            if is_real_race(df, reference_df):
                print(f"  ✅ 第 {race_no} 場係真實場次，共 {len(df)} 匹馬")
                all_dfs.append(df)
            else:
                print(f"  ⏹️ 第 {race_no} 場馬名同第 1 場完全一樣，判定為假數據，停止")
                break

            time.sleep(0.5)
    finally:
        driver.quit()

    if not all_dfs:
        return None, venue
    return pd.concat(all_dfs, ignore_index=True), venue

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='YYYY-MM-DD')
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except:
        print("❌ 日期格式錯誤")
        return

    df, venue = fetch_all_races(args.date)
    if df is None or df.empty:
        print("❌ 冇任何數據")
        return

    output_file = f"racecard_{args.date}_{venue}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    actual_races = df['場次'].nunique()
    print(f"\n✅ 已儲存至 {output_file}")
    print(f"📊 總共成功爬取 {actual_races} 場，合共 {len(df)} 匹馬")

if __name__ == '__main__':
    main()
