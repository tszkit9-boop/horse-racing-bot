# fetch_odds.py
# 賠率爬蟲自動化腳本（每 30 分鐘紀錄一次）
# 用法: python fetch_odds.py YYYY-MM-DD ST 或 python fetch_odds.py YYYY-MM-DD HV

import sys
import time
import csv
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

OUTPUT_CSV = "odds_history.csv"

def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)

def fetch_odds(date_str, racecourse):
    driver = make_driver()
    all_records = []
    crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        for race_no in range(1, 12): # 假設最多 11 場
            url = f"https://bet.hkjc.com/ch/racing/wp/{date_str}/{racecourse}/{race_no}"
            print(f"📊 載入賠率: {url}")
            
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                time.sleep(2)
            except Exception as e:
                print(f"  ⚠️ 第 {race_no} 場載入失敗: {e}")
                continue

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 尋找包含「獨贏」的表格
            target_table = None
            for table in soup.find_all('table'):
                if "獨贏" in table.text:
                    target_table = table
                    break
            
            if not target_table:
                print(f"  ⚠️ 第 {race_no} 場搵唔到賠率表")
                continue

            rows = target_table.find_all('tr')
            for row in rows[1:]: # 跳過表頭
                cells = row.find_all('td')
                if len(cells) < 8:
                    continue
                
                horse_no = cells[0].text.strip()
                horse_name = cells[2].text.strip()
                win_odds = cells[7].text.strip()
                
                # 清理數據
                if horse_name and win_odds and win_odds != '-':
                    all_records.append({
                        "crawl_time": crawl_time,
                        "race_date": date_str,
                        "racecourse": racecourse,
                        "race_no": race_no,
                        "horse_no": horse_no,
                        "horse_name": horse_name,
                        "win_odds": win_odds
                    })

    finally:
        driver.quit()

    return all_records

def main():
    if len(sys.argv) < 3:
        print("用法: python fetch_odds.py YYYY-MM-DD ST/HV")
        sys.exit(1)

    date_str = sys.argv[1]
    racecourse = sys.argv[2].upper()

    records = fetch_odds(date_str, racecourse)

    if not records:
        print("⚠️ 冇爬到任何賠率數據。")
        return

    # 寫入 CSV（如果檔案存在就 Append，唔存在就建立並寫 Header）
    file_exists = os.path.isfile(OUTPUT_CSV)
    fieldnames = ["crawl_time", "race_date", "racecourse", "race_no", "horse_no", "horse_name", "win_odds"]

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(records)

    print(f"✅ 成功寫入 {len(records)} 條賠率記錄到 {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
