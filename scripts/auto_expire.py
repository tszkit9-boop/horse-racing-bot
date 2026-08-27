#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自動檢查過期 VIP 會員並降級為免費
執行後會自動 commit 更新 users.json
"""

import json
import os
from datetime import datetime, timedelta
import sys

# 檔案路徑
USERS_FILE = 'users.json'

def load_users():
    """載入 users.json"""
    if not os.path.exists(USERS_FILE):
        print("❌ users.json 不存在")
        sys.exit(1)
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    """儲存 users.json"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def main():
    today = datetime.now().date()
    users = load_users()
    expired_users = []

    for username, user_data in users.items():
        # 只處理 VIP 用戶
        if user_data.get('group') != 'VIP':
            continue

        expiry_str = user_data.get('expiry_date')
        if not expiry_str:
            continue

        try:
            # 嘗試解析日期（支援 ISO 格式）
            expiry_date = datetime.fromisoformat(expiry_str).date()
        except:
            # 如果解析失敗，跳過
            continue

        if expiry_date < today:
            # 過期！降級為免費
            user_data['group'] = 'free'
            user_data['is_paid'] = False
            user_data['plan'] = None
            user_data['predictions_limit'] = 2  # 還原為預設免費次數
            # 記錄降級原因
            user_data['note'] = (user_data.get('note', '') + f' [於 {today.isoformat()} 自動降級（過期）]').strip()
            expired_users.append(username)

    if expired_users:
        save_users(users)
        print(f"✅ 已將 {len(expired_users)} 個過期會員降級：{', '.join(expired_users)}")
        # 設定環境變數，讓 workflow 知道有更改
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"changed=true\n")
            f.write(f"users={','.join(expired_users)}\n")
    else:
        print("✅ 目前沒有過期會員")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write("changed=false\n")

if __name__ == '__main__':
    main()
