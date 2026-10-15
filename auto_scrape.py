#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_scrape.py - 自動探測賽馬日，執行 scrape_racecard_full.py，並自動 push 上 GitHub
- 完全無視星期幾，靠探測 HKJC 網站決定今日係咪賽馬日
- 支援特別賽馬日（星期一、四、五、公眾假期）
- 自動更新 race_schedule.json
- 自動 push racecard_uploaded.csv, odds_history.csv, race_schedule.json
"""

import subprocess
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta


def probe_future_races():
    """
    自動探測未來 7 日嘅賽期，並寫入 race_schedule.json。
    做法：用 scrape_racecard_full.py 試爬每一日，爬到有數據就記錄低。
    完全無視星期幾，純粹基於實際爬取結果。
    """
    schedule_file = "race_schedule.json"
    schedule = {}
    if os.path.exists(schedule_file):
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except Exception:
            pass

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # 清理過期賽事
    schedule = {k: v for k, v in schedule.items() if k >= today_str}

    # 探測未來 7 日
    for i in range(0, 8):
        check_date = (now + timedelta(days=i)).strftime('%Y-%m-%d')
        if check_date in schedule:
            continue  # 已經記錄咗，跳過

        # 試下 HV 同 ST
        for course in ["HV", "ST"]:
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    # 將 scrape_racecard_full.py 複製到臨時目錄
                    shutil.copy("scrape_racecard_full.py", os.path.join(tmpdir, "scrape_racecard_full.py"))

                    cmd = [
                        sys.executable, "scrape_racecard_full.py",
                        "--date", check_date,
                        "--racecourse", course,
                        "--skip-finished"
                    ]
                    # 喺臨時目錄執行爬蟲，唔會覆蓋原本嘅 racecard_uploaded.csv
                    subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=90)

                    tmp_csv = os.path.join(tmpdir, "racecard_uploaded.csv")
                    if os.path.exists(tmp_csv):
                        import pandas as pd
                        df = pd.read_csv(tmp_csv, encoding='utf-8-sig')
                        if len(df) > 0:
                            schedule[check_date] = course
                            print(f"✅ 探測到 {check_date} 係賽馬日（{course}）")
                            break  # 搵到就唔使試另一個馬場
            except Exception:
                pass

    # 寫入 race_schedule.json
    with open(schedule_file, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    print(f"📅 已更新賽期表：{schedule}")


def main():
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')

    # 🆕 第一步：無論今日係咩日子，都先探測未來賽期
    print("🔍 開始探測未來賽期...")
    probe_future_races()

    # 🆕 第二步：檢查今日係唔係賽馬日（基於探測結果）
    schedule_file = "race_schedule.json"
    today_is_race_day = False
    racecourse = None
    if os.path.exists(schedule_file):
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
                if date_str in schedule:
                    today_is_race_day = True
                    racecourse = schedule[date_str]
        except Exception:
            pass

    if not today_is_race_day:
        print(f"⚠️ 今日 {date_str} 唔係賽馬日（探測結果），唔執行爬蟲")
        return

    print(f"📅 今日 {date_str} 係賽馬日，馬場：{racecourse}")

    # ===== 下面保持爬取同 Push 邏輯 =====
    csv_file = "racecard_uploaded.csv"
    before_mtime = os.path.getmtime(csv_file) if os.path.exists(csv_file) else 0

    cmd = [
        sys.executable, "scrape_racecard_full.py",
        "--date", date_str,
        "--racecourse", racecourse,
        "--skip-finished"
    ]
    print(f"🚀 執行：{' '.join(cmd)}")
    subprocess.run(cmd)

    after_mtime = os.path.getmtime(csv_file) if os.path.exists(csv_file) else 0
    if after_mtime <= before_mtime:
        print("ℹ️ racecard_uploaded.csv 冇更新，唔需要 push")
        return

    print("📤 開始上傳 racecard_uploaded.csv, odds_history.csv, race_schedule.json 上 GitHub...")
    try:
        subprocess.run(["git", "add", "racecard_uploaded.csv", "odds_history.csv", "race_schedule.json"], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", f"Auto update racecard & odds ({date_str})"],
                check=True
            )
            subprocess.run(["git", "push"], check=True)
            print("✅ 已成功 push 上 GitHub")
        else:
            print("ℹ️ 檔案冇變更，唔需要 push")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git 操作失敗：{e}")
    except Exception as e:
        print(f"⚠️ 上傳失敗：{e}")


if __name__ == "__main__":
    main()