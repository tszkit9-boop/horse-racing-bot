#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scrape_racecard_final.py - 準確爬取所有真實場次（用馬名驗證）
用法:
  python scrape_racecard_final.py --date 2026-09-06
"""

import os
import time
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
            
            results.append({
                '馬號': no_elem.text.strip(),
                '馬名': name_elem.text.strip(),
                '檔位': draw_elem.text.strip(),
                '負磅': wt_elem.text.strip(),
                '騎師': jockey_elem.text.strip(),
                '練馬師': trainer_elem.text.strip(),
                '場次': race_no,
                '比賽日期': date_str
            })
        except:
            continue
    
    return pd.DataFrame(results)

def fetch_all_races(date_str):
    print(f"📅 開始爬取 {date_str} 嘅所有真實場次")
    driver = get_driver()
    
    try:
        # 先爬第一場，拎馬名做參考
        print("\n⏳ 爬取第 1 場作為參考...")
        df_first = fetch_single_race(driver, date_str, 1)
        if df_first is None or df_first.empty:
            print("❌ 第 1 場冇數據，可能唔係賽馬日")
            return None
        
        # 提取第一場嘅馬名清單（用嚟比對）
        first_horses = set(df_first['馬名'].tolist())
        print(f"  ✅ 第 1 場有 {len(first_horses)} 匹馬")
        
        all_dfs = [df_first]
        total_races = 1
        
        # 由第 2 場開始試到第 15 場
        for race_no in range(2, 16):
            print(f"\n⏳ 正在檢查第 {race_no} 場...")
            df = fetch_single_race(driver, date_str, race_no)
            if df is None or df.empty:
                print(f"  ⏹️ 第 {race_no} 場無數據，停止")
                break
            
            # 檢查呢場嘅馬名是否同第一場完全一樣
            current_horses = set(df['馬名'].tolist())
            if current_horses == first_horses:
                print(f"  ⏹️ 第 {race_no} 場馬名同第 1 場完全一樣，判定為假數據，停止")
                break
            
            print(f"  ✅ 第 {race_no} 場係真實場次，共 {len(df)} 匹馬")
            all_dfs.append(df)
            total_races += 1
            time.sleep(0.5)
        
    finally:
        driver.quit()
    
    if not all_dfs:
        return None
    return pd.concat(all_dfs, ignore_index=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='YYYY-MM-DD')
    args = parser.parse_args()
    
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except:
        print("❌ 日期格式錯誤")
        return
    
    df = fetch_all_races(args.date)
    if df is None:
        print("❌ 冇任何數據")
        return
    
    output_file = f"racecard_{args.date}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    actual_races = df['場次'].nunique()
    print(f"\n✅ 已儲存至 {output_file}")
    print(f"📊 總共成功爬取 {actual_races} 場，合共 {len(df)} 匹馬")

if __name__ == '__main__':
    main()