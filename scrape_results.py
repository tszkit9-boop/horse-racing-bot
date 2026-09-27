def main():
    # 🆕 模式 0：讀取 GitHub Actions 傳入嘅環境變數（優先）
    env_date = os.environ.get('INPUT_TARGET_DATE', '').strip()
    
    if env_date:
        date_str = env_date
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            # 自動判斷馬場：星期三 = HV（跑馬地），其他 = ST（沙田）
            racecourse = 'HV' if dt.weekday() == 2 else 'ST'
        except ValueError:
            print("❌ 日期格式錯誤，請用 YYYY-MM-DD")
            return
        print(f"📅 GitHub Actions 輸入日期：{date_str} ({racecourse})")
        df_new = fetch_results(date_str, racecourse)

    # 模式 1：爬日期範圍  python scrape_results.py --range 2026-01-01 2026-09-13
    elif len(sys.argv) >= 4 and sys.argv[1] == '--range':
        try:
            start = datetime.strptime(sys.argv[2], '%Y-%m-%d')
            end = datetime.strptime(sys.argv[3], '%Y-%m-%d')
        except ValueError:
            print("❌ 日期格式錯誤，請用 YYYY-MM-DD")
            return
        print(f"📅 爬取範圍：{start.date()} 至 {end.date()}")
        df_new = fetch_date_range(start, end)

    # 模式 2：手動指定一日  python scrape_results.py 2026-09-16 ST
    elif len(sys.argv) >= 3:
        date_str = sys.argv[1]
        racecourse = sys.argv[2].upper()
        print(f"📅 手動指定：{date_str} ({racecourse})")
        df_new = fetch_results(date_str, racecourse)

    # 模式 3：自動搜尋最近 7 日（原本行為）
    else:
        print(f"📅 自動搜尋最近有賽事嘅日子...")
        df_new = try_fetch_multiple_days()

    if df_new is None or df_new.empty:
        print("❌ 冇新賽果數據")
        return

    merge_and_save(df_new)


if __name__ == '__main__':
    main()
