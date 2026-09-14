import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "predictions.db"

def init_db():
    """初始化數據庫，建立 predictions 表"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            key TEXT PRIMARY KEY,
            date TEXT,
            race INTEGER,
            top_horse TEXT,
            top_prob REAL,
            all_horses TEXT,
            model_used TEXT,
            predicted_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_prediction(key, data):
    """儲存預測記錄（如果已存在就更新）"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO predictions (key, date, race, top_horse, top_prob, all_horses, model_used, predicted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        key,
        data.get('date'),
        data.get('race'),
        data.get('top_horse'),
        data.get('top_prob'),
        json.dumps(data.get('all_horses', []), ensure_ascii=False),
        json.dumps(data.get('model_used', []), ensure_ascii=False),
        data.get('predicted_at', datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()

def load_predictions():
    """讀取所有預測記錄，回傳與舊 JSON 格式一樣嘅 dict"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, date, race, top_horse, top_prob, all_horses, model_used, predicted_at FROM predictions")
    rows = c.fetchall()
    conn.close()
    
    result = {}
    for row in rows:
        result[row[0]] = {
            "date": row[1],
            "race": row[2],
            "top_horse": row[3],
            "top_prob": row[4],
            "all_horses": json.loads(row[5]) if row[5] else [],
            "model_used": json.loads(row[6]) if row[6] else [],
            "predicted_at": row[7]
        }
    return result
