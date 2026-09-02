#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_selenium.py - 爬取馬會投注頁面所有場次（含賠率，自動分辨場地）
用法:
  python scrape_racecard_selenium.py --date 2026-09-06
  或
  python scrape_racecard_selenium.py  (自動用今日日期)
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

def get_race_info(driver, date_str):
    """
    從第一場頁面獲取總場次數同場地縮寫
    返回 (total_races, venue_abbr)
    """
    url = f"https://bet.hkjc.com/ch/racing/home/{date_str}/ST/1"
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "meeting-info"))
        )
    except:
        return 0, ""

    time.sleep(1)
    total = 0
    venue = ""

    # 1. 從 meeting-info 提取總場次
    try:
        info_elem = driver.find_element(By.CLASS_NAME, "meeting-info")
        info_text = info_elem.text.strip()
        match = re.search(r'(\d+)\s*場', info_text)
        if match:
            total = int(match.group(1))
    except:
        pass

    # 2. 從同一元素提取場地（沙田 / 跑馬地）
    try:
        info_elem = driver.find_element(By.CLASS_NAME, "meeting-info")
        info_text = info_elem.text.strip()
        if "沙田" in info_text:
            venue = "ST"
        elif "跑馬地" in info_text or "跑馬地" in info_text:
            venue = "HV"
        else:
            # 嘗試從頁面其他地方搵
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "沙田" in body_text:
                venue = "ST"
            elif "跑馬地" in body_text:
                venue = "HV"
    except:
        pass

    # 如果上面都搵唔到，預設 ST
    if not venue:
        venue = "ST"

    # 如果 total 仍然係 0，試用場次按鈕
    if total == 0:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, ".rc-race-tab a, .rc-tab a, [class*='race-tab'] a")
            race_nos = []
            for btn in buttons:
                text = btn.text.strip()
                if text.isdigit():
                    race_nos.append(int(text))
            if race_nos:
                total = max(race_nos)
        except:
            pass

    if total == 0:
        total = 10  # fallback

    return total, venue

def fetch_single_race(driver, date_str, race_no):
    """爬取單一場次詳細數據（含賠率）"""
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

def fetch_all_races(date_str):
    print(f"📅 開始爬取 {date_str} 嘅所有場次（含賠率）")
    driver = get_driver()
    try:
        total_races, venue_abbr = get_race_info(driver, date_str)
        print(f"📋 場地：{venue_abbr}，共有 {total_races} 場賽事")
        if total_races == 0:
            print("❌ 無法偵測場次數量")
            return None, None

        all_dfs = []
        for race_no in range(1, total_races + 1):
            print(f"\n⏳ 正在爬取第 {race_no} 場（共 {total_races} 場）...")
            df = fetch_single_race(driver, date_str, race_no)
            if df is None or df.empty:
                print(f"  ⚠️ 第 {race_no} 場無數據，跳過")
                continue
            print(f"  ✅ 第 {race_no} 場成功，共 {len(df)} 匹馬")
            all_dfs.append(df)
            time.sleep(0.5)
    finally:
        driver.quit()

    if not all_dfs:
        return None, None
    return pd.concat(all_dfs, ignore_index=True), venue_abbr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='YYYY-MM-DD，預設今日')
    args = parser.parse_args()

    if args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except:
        print("❌ 日期格式錯誤")
        return

    df, venue = fetch_all_races(date_str)
    if df is None or df.empty:
        print("❌ 冇任何數據")
        return

    # 檔案名：racecard_日期_場地縮寫.csv
    output_file = f"racecard_{date_str}_{venue}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    actual_races = df['場次'].nunique()
    print(f"\n✅ 已儲存至 {output_file}")
    print(f"📊 總共成功爬取 {actual_races} 場，合共 {len(df)} 匹馬")

if __name__ == '__main__':
    main()
