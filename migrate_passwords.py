#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
migrate_passwords.py - 一次性將所有明文密碼轉 bcrypt hash
"""

import os
import requests
import bcrypt

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def hash_password(pw):
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(str(pw).encode('utf-8'), salt).decode('utf-8')

def main():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # 讀取所有用戶
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?select=username,password",
        headers=headers, timeout=15
    )
    if res.status_code != 200:
        print(f"❌ 讀取失敗: {res.status_code} - {res.text}")
        return

    users = res.json()
    print(f"📊 共 {len(users)} 個用戶")

    migrated = 0
    skipped = 0

    for u in users:
        uname = u.get('username')
        pw = str(u.get('password', '')).strip()
        if not pw:
            skipped += 1
            continue

        # 如果已經係 bcrypt hash，跳過
        if pw.startswith('$2') and len(pw) == 60:
            print(f"⏭️ {uname} 已加密")
            skipped += 1
            continue

        # 轉 hash
        new_hash = hash_password(pw)
        patch_res = requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{uname}",
            headers=headers,
            json={"password": new_hash},
            timeout=15
        )
        if patch_res.status_code in (200, 204):
            print(f"✅ {uname} 已加密")
            migrated += 1
        else:
            print(f"❌ {uname} 失敗: {patch_res.status_code}")

    print(f"\n🎉 完成！成功 {migrated}，跳過 {skipped}")

if __name__ == '__main__':
    main()
