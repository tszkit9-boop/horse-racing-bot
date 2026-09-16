def fetch_single_race(driver, date_str, racecourse, race_no):
    """爬取單場賽果（改用官方 LocalResults.aspx 頁面）"""
    # 🛡️ 關鍵修正：改用 racing.hkjc.com 嘅官方賽果頁面
    date_formatted = date_str.replace('-', '/')
    url = f"https://racing.hkjc.com/zh-hk/local/information/localresults"
    print(f"  🌐 載入第 {race_no} 場: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.f_fs12"))
        )
    except Exception:
        return None

    time.sleep(1)
    results = []

    try:
        # 官方頁面嘅賽果表格 class 係 f_fs12
        rows = driver.find_elements(By.CSS_SELECTOR, "table.f_fs12 tr")
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
