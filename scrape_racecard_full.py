#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
香港賽馬會排位 + 賠率爬蟲（自動累積版）
- 加入 crawl_time 欄位
- 追加模式寫入 odds_history.csv
- 自動偵測當日總場次，唔會爬多餘場次
- 備份檔案只保留 9 個欄位
- 自動複製一份為 racecard_uploaded.csv
- 🆕 支援 --skip-finished 參數，跳過已跑完場次
- 🆕 修正 is_race_finished()，改用元素檢查而非關鍵字搜尋
- 🆕 加入 is_hk_local_race()，確保只爬香港本地賽事
"""

import os
import time
import argparse
import pandas as pd
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

OUTPUT_FILE = "odds_history.csv"

# 備份檔案只保留呢 9 個欄位
BACKUP_COLS = [
    'race_date', 'race_no', 'horse_no', 'horse_name',
    'draw', 'weight', 'jockey', 'trainer', 'win_odds'
]

# 🆕 越洋轉播相關關鍵字
OVERSEAS_KEYWORDS = ['越洋轉播', '海外賽事', '海外轉播', '轉播賽事', 'Simulcast', '海外賽馬']


def find_column_index(header_row, keywords):
    cells = header_row.find_all(['th', 'td'])
    for idx, cell in enumerate(cells):
        text = cell.text.strip()
        for kw in keywords:
            if kw in text:
                return idx
    return None


def is_hk_local_race(page):
    """
    🆕 檢查頁面係咪香港本地賽事
    透過檢查頁面係咪包含越洋轉播、海外賽事等關鍵字
    如果包含，回傳 False（唔係香港本地賽事）
    """
    try:
        body_text = page.inner_text('body')
        for kw in OVERSEAS_KEYWORDS:
            if kw in body_text:
                return False
        return True
    except Exception:
        return True


def is_race_finished(page):
    """
    檢查賽事係咪已跑完
    透過檢查頁面特定元素，而非關鍵字搜尋，避免誤判
    """
    try:
        title_elements = page.query_selector_all('h1, h2, h3, .race-title, .race-header')
        for el in title_elements:
            text = el.inner_text().strip()
            if '賽果' in text or '結果' in text:
                return True

        result_tables = page.query_selector_all('table')
        for table in result_tables:
            header = table.query_selector('tr')
            if header:
                header_text = header.inner_text()
                if '名次' in header_text and '馬號' in header_text:
                    return True

        return False
    except Exception:
        return False


def scrape_odds_from_wp(page, date_str, racecourse, race_no, horse_names):
    url = f"https://bet.hkjc.com/ch/racing/wp/{date_str}/{racecourse}/{race_no}"
    print(f"  📊 載入賠率: {url}")

    try:
        page.goto(url, wait_until="load", timeout=30000)
        time.sleep(3)

        body_text = page.inner_text('body')
        if "系統將於稍後恢復" in body_text:
            print("  ⚠️ 賠率頁面系統維護中")
            return {}

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        odds_data = {}

        tables = soup.find_all('table')
        target_table = None
        for table in tables:
            if "獨贏" in table.text:
                target_table = table
                break

        if not target_table:
            print("  ⚠️ 找不到包含『獨贏』的表格")
            return {}

        rows = target_table.find_all('tr')
        if len(rows) < 2:
            return {}

        HORSE_COL = 2
        WIN_COL = 7

        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) <= WIN_COL:
                continue
            horse_name = cells[HORSE_COL].text.strip()
            if not horse_name and HORSE_COL + 1 < len(cells):
                horse_name = cells[HORSE_COL + 1].text.strip()
            if not horse_name or len(horse_name) < 2:
                continue
            odds_text = cells[WIN_COL].text.strip()
            if odds_text and odds_text != '-':
                try:
                    float(odds_text)
                    odds_data[horse_name] = odds_text
                except:
                    pass

        if len(odds_data) < len(horse_names):
            odds_section = re.search(r'獨贏(?:賠率)?走勢(.*?)(?=投注額|$)', body_text, re.DOTALL)
            if odds_section:
                section_text = odds_section.group(1)
                matches = re.findall(r'([\u4e00-\u9fff]{2,})\s*(\d+\.?\d*)', section_text)
                for horse_name, odds in matches:
                    horse_name = horse_name.strip()
                    if horse_name not in odds_data:
                        odds_data[horse_name] = odds

        return odds_data

    except Exception as e:
        print(f"  ❌ 賠率錯誤: {e}")
        return {}


def detect_max_races(page, date_str, racecourse):
    """從頁面頂部嘅場次按鈕自動偵測當日總場次"""
    url = f"https://bet.hkjc.com/ch/racing/home/{date_str}/{racecourse}/1"
    try:
        page.goto(url, wait_until="load", timeout=30000)
        time.sleep(3)
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        max_race = 0
        for tag in soup.find_all(['a', 'button', 'li']):
            text = tag.text.strip()
            if text.isdigit():
                num = int(text)
                if 1 <= num <= 12:
                    max_race = max(max_race, num)

        if max_race > 0:
            return max_race

        matches = re.findall(r'第\s*(\d+)\s*場', html)
        if matches:
            return max(int(m) for m in matches)

        return 11
    except Exception as e:
        print(f"  ⚠️ 偵測場次失敗：{e}，預設 11 場")
        return 11


def scrape_racecard(date_str, racecourse="HV", skip_finished=False):
    all_data = []
    crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # 🆕 檢查係咪香港本地賽事
        url_check = f"https://bet.hkjc.com/ch/racing/home/{date_str}/{racecourse}/1"
        try:
            page.goto(url_check, wait_until="load", timeout=30000)
            time.sleep(3)
            if not is_hk_local_race(page):
                print(f"⏭️ {date_str} 唔係香港本地賽事（可能係越洋轉播），跳過")
                browser.close()
                return pd.DataFrame()
        except Exception as e:
            print(f"  ⚠️ 檢查賽事類型失敗：{e}，繼續嘗試爬取")

        max_races = detect_max_races(page, date_str, racecourse)
        print(f"📊 自動偵測到當日共有 {max_races} 場")
        if skip_finished:
            print(f"⏭️ 已啟用跳過已跑完場次模式")

        for race_no in range(1, max_races + 1):
            url_home = f"https://bet.hkjc.com/ch/racing/home/{date_str}/{racecourse}/{race_no}"
            print(f"🌐 載入第 {race_no} 場排位: {url_home}")

            success = False
            for attempt in range(3):
                try:
                    page.goto(url_home, wait_until="load", timeout=30000)
                    page.wait_for_selector("text=馬名", timeout=20000)
                    time.sleep(3)

                    if skip_finished and is_race_finished(page):
                        print(f"  ⏭️ 第 {race_no} 場已跑完，跳過")
                        success = True
                        break

                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')

                    tables = soup.find_all('table')
                    target = None
                    for table in tables:
                        if "馬名" in table.text and "檔位" in table.text:
                            target = table
                            break

                    race_horses = []

                    if target:
                        header_row = target.find('tr')
                        col_map = {}
                        if header_row:
                            col_map['horse_no'] = find_column_index(header_row, ['馬號'])
                            col_map['horse_name'] = find_column_index(header_row, ['馬名'])
                            col_map['draw'] = find_column_index(header_row, ['檔位'])
                            col_map['weight'] = find_column_index(header_row, ['負磅'])
                            col_map['jockey'] = find_column_index(header_row, ['騎師'])
                            col_map['trainer'] = find_column_index(header_row, ['練馬師'])

                        rows = target.find_all('tr')[1:]
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) < 7:
                                continue
                            if "馬名" in cells[0].text or "馬號" in cells[0].text:
                                continue
                            if "王/優" in cells[0].text:
                                continue

                            horse_no = cells[col_map.get('horse_no', 0)].text.strip() if col_map.get('horse_no') is not None else ''
                            horse_name = cells[col_map.get('horse_name', 1)].text.strip() if col_map.get('horse_name') is not None else ''
                            if not horse_name or horse_name in ["馬名", "馬號"]:
                                continue
                            if "綠衣" in horse_name:
                                continue

                            is_reserve = False
                            for cell in cells:
                                if "後備" in cell.text:
                                    is_reserve = True
                                    break
                            if is_reserve:
                                continue

                            draw = cells[col_map.get('draw', 2)].text.strip() if col_map.get('draw') is not None else ''
                            weight = cells[col_map.get('weight', 3)].text.strip() if col_map.get('weight') is not None else ''
                            jockey = cells[col_map.get('jockey', 4)].text.strip() if col_map.get('jockey') is not None else ''
                            trainer = cells[col_map.get('trainer', 5)].text.strip() if col_map.get('trainer') is not None else ''

                            race_horses.append({
                                'crawl_time': crawl_time,
                                'race_date': date_str,
                                'racecourse': racecourse,
                                'race_no': race_no,
                                'horse_no': horse_no,
                                'horse_name': horse_name,
                                'draw': draw,
                                'weight': weight,
                                'jockey': jockey,
                                'trainer': trainer,
                                'win_odds': ''
                            })
                    else:
                        lines = html.split('\n')
                        for line in lines:
                            if '|' not in line:
                                continue
                            if '馬名' in line or '馬號' in line or '王/優' in line:
                                continue
                            if '綠衣' in line:
                                continue
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            if len(parts) < 7:
                                continue
                            horse_no = parts[0]
                            horse_name = parts[1] if len(parts) > 1 else ''
                            if not horse_name or not re.search(r'[\u4e00-\u9fff]', horse_name):
                                continue
                            if '後備' in line:
                                continue
                            race_horses.append({
                                'crawl_time': crawl_time,
                                'race_date': date_str,
                                'racecourse': racecourse,
                                'race_no': race_no,
                                'horse_no': horse_no,
                                'horse_name': horse_name,
                                'draw': parts[2] if len(parts) > 2 else '',
                                'weight': parts[3] if len(parts) > 3 else '',
                                'jockey': parts[4] if len(parts) > 4 else '',
                                'trainer': parts[5] if len(parts) > 5 else '',
                                'win_odds': ''
                            })

                    if not race_horses:
                        print(f"  ⚠️ 第 {race_no} 場無馬匹，停止爬取")
                        success = True
                        break

                    horse_names = [h['horse_name'] for h in race_horses]
                    odds_data = scrape_odds_from_wp(page, date_str, racecourse, race_no, horse_names)
                    if odds_data:
                        print(f"  📊 第 {race_no} 場賠率: {len(odds_data)} 匹馬有賠率")
                        for horse in race_horses:
                            if horse['horse_name'] in odds_data:
                                horse['win_odds'] = odds_data[horse['horse_name']]
                    else:
                        print(f"  ⚠️ 第 {race_no} 場搵唔到賠率")

                    all_data.extend(race_horses)
                    print(f"  ✅ 第 {race_no} 場成功解析 {len(race_horses)} 匹馬（含排位及賠率）")
                    success = True
                    break

                except Exception as e:
                    print(f"  ❌ 錯誤: {e}，重試 ({attempt+1}/3)")
                    time.sleep(3)

            if not success:
                print(f"  ❌ 第 {race_no} 場重試失敗，停止")
                break

            if race_no >= max_races:
                break

            time.sleep(2)

        browser.close()

    return pd.DataFrame(all_data)


def get_user_input():
    print("=" * 60)
    print("🏇 排位 + 賠率爬蟲（自動偵測場次版）")
    print("=" * 60)
    date_str = input("請輸入日期 (例如 2026-10-07): ").strip()
    if not date_str:
        print("❌ 日期不能為空")
        return None, None
    course = input("請輸入馬場 (ST=沙田, HV=跑馬地，直接 Enter 預設 HV): ").strip().upper()
    if course not in ["ST", "HV"]:
        course = "HV"
    return date_str, course


def save_to_csv(df_new, output_file=OUTPUT_FILE):
    """追加模式儲存，保留全部欄位"""
    if df_new.empty:
        print("\n❌ 沒有新數據需要儲存")
        return

    if os.path.exists(output_file):
        try:
            old_df = pd.read_csv(output_file, encoding='utf-8-sig', low_memory=False)
            combined = pd.concat([old_df, df_new], ignore_index=True)
            combined = combined.drop_duplicates(
                subset=['crawl_time', 'race_date', 'racecourse', 'race_no', 'horse_no'],
                keep='last'
            )
            combined.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n📊 已追加至 {output_file}")
            print(f"   舊數據：{len(old_df)} 筆，新增：{len(df_new)} 筆，總計：{len(combined)} 筆")
        except Exception as e:
            print(f"⚠️ 讀取舊檔案失敗：{e}，將以新檔案模式儲存")
            df_new.to_csv(output_file, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n📊 已建立新檔案 {output_file}（{len(df_new)} 筆）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='日期 YYYY-MM-DD')
    parser.add_argument('--racecourse', default='HV', choices=['ST', 'HV'])
    parser.add_argument('--skip-finished', action='store_true', help='跳過已跑完場次')
    args = parser.parse_args()

    if args.date:
        date_str = args.date
        racecourse = args.racecourse
    else:
        result = get_user_input()
        if result is None:
            exit(1)
        date_str, racecourse = result

    print(f"📅 日期: {date_str}, 馬場: {racecourse}")
    df = scrape_racecard(date_str, racecourse, skip_finished=args.skip_finished)

    if not df.empty:
        all_columns = ['crawl_time', 'race_date', 'racecourse', 'race_no',
                       'horse_no', 'horse_name', 'draw', 'weight', 'jockey', 'trainer', 'win_odds']
        for c in all_columns:
            if c not in df.columns:
                df[c] = ''
        df = df[all_columns]

        backup_df = df[BACKUP_COLS].copy()
        backup_file = f"racecard_{date_str}_{racecourse}.csv"
        backup_df.to_csv(backup_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 已儲存當日備份：{backup_file}（{len(BACKUP_COLS)} 欄位）")

        backup_df.to_csv("racecard_uploaded.csv", index=False, encoding='utf-8-sig')
        print(f"💾 已自動更新 racecard_uploaded.csv（可直接上傳 GitHub）")

        save_to_csv(df)

        print(f"\n✅ 成功爬取 {len(df)} 條數據")
        print(f"📊 場次分佈：\n{df.groupby('race_no').size()}")
        print("\n📋 頭 10 筆預覽：")
        print(df.head(10))
        has_odds = df[df['win_odds'].astype(str).str.strip() != '']
        print(f"\n💰 有賠率嘅馬匹: {len(has_odds)} 匹")
    else:
        print("\n❌ 沒有爬取到任何數據")