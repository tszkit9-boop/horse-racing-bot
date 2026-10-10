#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_scrape.py - 自動判斷賽馬日，執行 scrape_racecard_full.py，並自動 push 上 GitHub
- 加入檔案更新檢查：只有 racecard_uploaded.csv 真正更新過，才會 push
"""

import subprocess
import sys
import os
from datetime import datetime


def main():
    now = datetime.now()
    weekday = now.weekday()

    if weekday == 2:
        racecourse = "HV"
    elif weekday in [5, 6]:
        racecourse = "ST"
    else:
        print(f"⚠️ 今日唔係賽馬日（weekday={weekday+1}），唔執行爬蟲")
        return

    date_str = now.strftime('%Y-%m-%d')
    print(f"📅 今日係 {date_str}（星期{weekday+1}），爬取馬場：{racecourse}")

    # 🆕 記錄爬蟲之前嘅檔案修改時間
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

    # 🆕 檢查檔案有冇更新
    after_mtime = os.path.getmtime(csv_file) if os.path.exists(csv_file) else 0
    if after_mtime <= before_mtime:
        print("ℹ️ racecard_uploaded.csv 冇更新（可能係非賽馬日），唔需要 push")
        return

    # ===== 自動 push racecard_uploaded.csv 上 GitHub =====
    print("📤 開始上傳 racecard_uploaded.csv 上 GitHub...")
    try:
        subprocess.run(["git", "add", "racecard_uploaded.csv"], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", f"Auto update racecard_uploaded.csv ({date_str})"],
                check=True
            )
            subprocess.run(["git", "push"], check=True)
            print("✅ 已成功 push 上 GitHub")
        else:
            print("ℹ️ racecard_uploaded.csv 冇變更，唔需要 push")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git 操作失敗：{e}")
    except Exception as e:
        print(f"⚠️ 上傳失敗：{e}")


if __name__ == "__main__":
    main()