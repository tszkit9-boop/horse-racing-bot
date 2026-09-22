import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=zh-HK"
OUTPUT_FILE = "odds_history.csv"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 👇 終極關鍵：使用 webdriver-manager 下載匹配嘅 Driver，並用 Service 強制指定，完全無視系統 PATH 嗰個舊版！
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_odds():
    print("🚀 開始爬取賠率...")
    driver = setup_driver()
    all_data = []
    try:
        driver.get(URL)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "oddsTable"))) 
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            print("⚠️ 搵唔到任何表格，可能網站結構已變或被封鎖。")
            return
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    horse_no = cols[0].get_text(strip=True)
                    horse_name = cols[1].get_text(strip=True)
                    odds = cols[2].get_text(strip=True)
                    if horse_no.isdigit():
                        all_data.append({
                            "日期": pd.Timestamp.now(tz='Asia/Hong_Kong').strftime('%Y-%m-%d'),
                            "場次": "待確認",
                            "馬號": horse_no,
                            "馬名": horse_name,
                            "賠率": odds,
                            "爬取時間": pd.Timestamp.now(tz='Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                        })
        if not all_data:
            print("⚠️ 冇抓到任何數據，可能賠率未更新或網站被封。")
            return
        new_df = pd.DataFrame(all_data)
        print(f"✅ 成功抓取 {len(new_df)} 條賠率記錄。")
        if os.path.exists(OUTPUT_FILE):
            old_df = pd.read_csv(OUTPUT_FILE)
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["日期", "場次", "馬號"], keep="last")
            combined_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
            print(f"📁 已更新 {OUTPUT_FILE}")
        else:
            new_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
            print(f"📁 已建立新檔案 {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 爬取過程出錯：{e}")
    finally:
        driver.quit()
        print("🏁 爬蟲結束。")

if __name__ == "__main__":
    scrape_odds()
