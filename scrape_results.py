def fetch_single_race(driver, date_str, racecourse, race_no):
    """爬取單場賽果（多重選擇器 + 除錯）"""
    date_formatted = date_str.replace('-', '/')
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={date_formatted}&Racecourse={racecourse}&RaceNo={race_no}"
    print(f"  🌐 載入第 {race_no} 場: {url}")
    driver.get(url)

    time.sleep(3)  # 等耐啲，確保頁面完全載入

    # 檢查頁面有冇「賽事尚未舉行」字眼
    page_text = driver.page_source
    if "賽事尚未舉行" in page_text or "賽事還未舉行" in page_text:
        print(f"  ⏳ 第 {race_no} 場賽事未跑")
        return None

    # 檢查頁面有冇「找不到」字眼
    if "找不到" in page_text or "無此賽事" in page_text:
        print(f"  ❌ 第 {race_no} 場冇呢場賽事")
        return None

    results = []

    # 🛡️ 嘗試多個可能嘅表格選擇器
    selectors = [
        "table.f_fs12 tr",           # 原本嘅
        "table.table_bd tr",         # 常見賽果表
        "table tr",                  # 所有表格
    ]

    rows = []
    for sel in selectors:
        rows = driver.find_elements(By.CSS_SELECTOR, sel)
        if len(rows) > 5:  # 搵到有意義嘅表格
            print(f"  📋 使用選擇器: {sel}（{len(rows)} 行）")
            break

    if not rows:
        print(f"  ⚠️ 第 {race_no} 場搵唔到表格")
        return None

    for row in rows:
        try:
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
        except Exception:
            continue

    if results:
        print(f"  ✅ 第 {race_no} 場：{len(results)} 匹")
    else:
        print(f"  ⚠️ 第 {race_no} 場解析唔到馬名")

    return pd.DataFrame(results) if results else None
