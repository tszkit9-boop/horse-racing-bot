#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
migrate_passwords.py - 一次性將所有明文密碼轉 bcrypt hash
安全：已加密會自動跳過，可重複執行
"""

import os
import sys
import requests
import bcrypt

# ============================================================
# 從環境變數讀取 Supabase 設定
# ============================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

# ============================================================
# 檢查環境變數
# ============================================================
if not SUPABASE_URL:
    print("❌ 錯誤：SUPABASE_URL 未設定")
    print("   請去 GitHub → Settings → Secrets and variables → Actions")
    print("   加一個 Secret 叫 SUPABASE_URL")
    sys.exit(1)

if not SUPABASE_KEY:
    print("❌ 錯誤：SUPABASE_KEY 未設定")
    print("   請去 GitHub → Settings → Secrets and variables → Actions")
    print("   加一個 Secret 叫 SUPABASE_KEY")
    sys.exit(1)

print(f"✅ SUPABASE_URL = {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY = {SUPABASE_KEY[:20]}...（已遮蓋）")
print()

# ============================================================
# 工具函數
# ============================================================
def hash_password(plain_password):
    """將明文密碼轉為 bcrypt hash"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(str(plain_password).encode('utf-8'), salt)
    return hashed.decode('utf-8')


def is_bcrypt_hash(pw):
    """檢查係咪已經係 bcrypt hash"""
    pw = str(pw).strip()
    return pw.startswith('$2') and len(pw) == 60


# ============================================================
# 主程式
# ============================================================
def main():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    print("📊 讀取所有用戶...")
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?select=username,password",
            headers=headers,
            timeout=30
        )
    except Exception as e:
        print(f"❌ 連線錯誤: {e}")
        sys.exit(1)

    if res.status_code != 200:
        print(f"❌ 讀取失敗: HTTP {res.status_code}")
        print(f"   回應: {res.text}")
        sys.exit(1)

    users = res.json()
    if not isinstance(users, list):
        print(f"❌ 回應格式錯誤: {users}")
        sys.exit(1)

    print(f"✅ 共 {len(users)} 個用戶")
    print("=" * 50)

    migrated = 0
    skipped = 0
    failed = 0

    for u in users:
        uname = u.get('username', '').strip()
        pw = str(u.get('password', '')).strip()

        if not uname:
            continue

        # 冇密碼，跳過
        if not pw:
            print(f"⏭️  {uname} — 冇密碼，跳過")
            skipped += 1
            continue

        # 已經係 bcrypt hash，跳過
        if is_bcrypt_hash(pw):
            print(f"⏭️  {uname} — 已加密，跳過")
            skipped += 1
            continue

        # 轉 hash
        try:
            new_hash = hash_password(pw)
            patch_res = requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?username=eq.{uname}",
                headers=headers,
                json={"password": new_hash},
                timeout=30
            )

            if patch_res.status_code in (200, 204):
                print(f"✅ {uname} — 已加密")
                migrated += 1
            else:
                print(f"❌ {uname} — 失敗: HTTP {patch_res.status_code}")
                print(f"   {patch_res.text}")
                failed += 1
        except Exception as e:
            print(f"❌ {uname} — 錯誤: {e}")
            failed += 1

    print("=" * 50)
    print(f"🎉 完成！")
    print(f"   ✅ 成功加密：{migrated} 個")
    print(f"   ⏭️  跳過：{skipped} 個")
    print(f"   ❌ 失敗：{failed} 個")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
