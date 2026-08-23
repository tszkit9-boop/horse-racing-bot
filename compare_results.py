#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compare_results.py - 賽果對比：預測 vs 實際
用法：
  python compare_results.py --date 2025-04-09           # 全部場次
  python compare_results.py --date 2025-04-09 --race 5  # 單一場次
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
import pandas as pd
import os
import glob
from datetime import datetime

# ============================================================
# 參數
# ============================================================
parser = argparse.ArgumentParser(description='賽果對比工具')
parser.add_argument('--date', type=str, required=True, help='日期 YYYY-MM-DD')
parser.add_argument('--race', type=int, help='場次（可選）')
args = parser.parse_args()

target_date = args.date
target_race = args.race

print(f"📊 賽果對比：{target_date}" + (f" 第{target_race}場" if target_race else " 全部場次"))

# ============================================================
# 1. 讀取預測結果
# ============================================================
def load_prediction(date_str, race_no=None):
    """讀取 prediction_history 中指定日期的預測結果"""
    history_folder = 'prediction_history'
    if not os.path.exists(history_folder):
        print(f"❌ 找不到資料夾 {history_folder}")
        return None
    
    # 搜尋匹配的預測檔案
    pattern = f"prediction_{date_str}*"
    files = glob.glob(os.path.join(history_folder, pattern))
    if not files:
        print(f"❌ 找不到 {date_str} 的預測記錄")
        return None
    
    # 取最新一個（或指定場次）
    files.sort(reverse=True)
    
    for file in files:
        df = pd.read_csv(file, encoding='utf-8-sig')
        if race_no:
            df = df[df['場次'] == race_no]
            if not df.empty:
                return df
        else:
            return df
    
    print(f"❌ 找不到 {date_str} 第{race_no}場的預測記錄" if race_no else f"❌ 找不到 {date_str} 的預測記錄")
    return None

# ============================================================
# 2. 讀取實際賽果
# ============================================================
def load_result(date_str, race_no=None):
    """從 full_data_*.csv 讀取實際賽果"""
    # 嘗試多種日期格式
    files = glob.glob(f"full_data_*.csv")
    target_file = None
    for f in files:
        # 提取日期部分
        f_name = os.path.basename(f)
        # 假設格式 full_data_YYYY-MM-DD.csv
        if date_str in f_name:
            target_file = f
            break
    
    if not target_file:
        print(f"❌ 找不到 {date_str} 的賽果數據")
        return None
    
    df = pd.read_csv(target_file, encoding='utf-8-sig')
    
    # 如果有場次篩選
    if race_no and '場次' in df.columns:
        df = df[df['場次'] == race_no]
    elif race_no and 'race_no' in df.columns:
        df = df[df['race_no'] == race_no]
    
    if df.empty:
        print(f"❌ {date_str}" + (f" 第{race_no}場" if race_no else "") + " 無賽果數據")
        return None
    
    return df

# ============================================================
# 3. 對比分析
# ============================================================
def compare(pred_df, result_df, race_no=None):
    """執行對比分析"""
    # 標準化欄位名
    result_cols = result_df.columns.tolist()
    
    # 找馬名欄位
    name_col = '馬名' if '馬名' in result_cols else 'horse_id'
    if name_col not in result_cols:
        for col in ['馬匹ID', 'horse_id', '馬號']:
            if col in result_cols:
                name_col = col
                break
    
    # 找名次欄位
    rank_col = '名次' if '名次' in result_cols else 'finish_position'
    if rank_col not in result_cols:
        for col in ['Result', 'Position', 'rank']:
            if col in result_cols:
                rank_col = col
                break
    
    print(f"📋 使用欄位：馬名='{name_col}', 名次='{rank_col}'")
    
    # 提取預測 TOP 5
    pred_top5 = pred_df.head(5)[['馬匹名稱', '檔位', '預測勝率', '值博指數']].copy()
    pred_top5['預測排名'] = range(1, len(pred_top5) + 1)
    
    # 提取實際賽果
    results = []
    for idx, row in pred_top5.iterrows():
        horse_name = row['馬匹名稱']
        
        # 嘗試在賽果中找同名馬
        actual_rank = '?'
        actual_place = '?'
        
        if name_col in result_df.columns:
            # 先嚐試完全匹配
            actual = result_df[result_df[name_col] == horse_name]
            if actual.empty:
                # 嘗試包含匹配
                actual = result_df[result_df[name_col].astype(str).str.contains(horse_name, na=False, case=False)]
            if actual.empty:
                actual_rank = '未出賽'
                actual_place = '未出賽'
            else:
                if rank_col in actual.columns:
                    actual_rank = actual.iloc[0][rank_col]
                    try:
                        rank_val = int(actual_rank)
                        if rank_val == 1:
                            actual_place = '冠軍 ✅'
                        elif rank_val in [2, 3]:
                            actual_place = f'第{rank_val}名 🏆'
                        else:
                            actual_place = f'第{rank_val}名'
                    except:
                        actual_place = str(actual_rank)
                else:
                    actual_rank = '?'
                    actual_place = '?'
        else:
            actual_rank = '?'
            actual_place = '?'
        
        results.append({
            '馬匹': horse_name,
            '預測排名': row['預測排名'],
            '預測勝率': row['預測勝率'],
            '實際名次': actual_rank,
            '實際位置': actual_place,
        })
    
    # 計算統計
    hit_win = any(str(r['實際名次']) == '1' for r in results)
    hit_place = any(str(r['實際名次']) in ['1', '2', '3'] for r in results)
    
    # 建立報告
    report = []
    report.append("="*60)
    if race_no:
        report.append(f"🏇 賽果對比報告 - {args.date} 第{race_no}場")
    else:
        report.append(f"🏇 賽果對比報告 - {args.date} 全部場次")
    report.append("="*60)
    report.append("")
    report.append("📊 預測 TOP 5 vs 實際賽果")
    report.append("-"*50)
    report.append(f"{'排名':<4} {'馬匹名稱':<12} {'預測勝率':<8} {'實際名次':<10} {'結果':<8}")
    report.append("-"*50)
    
    for r in results:
        report.append(f"{r['預測排名']:<4} {r['馬匹'][:12]:<12} {r['預測勝率']:.2%}    {str(r['實際名次']):<10} {r['實際位置']:<8}")
    
    report.append("-"*50)
    report.append("")
    report.append("📈 統計摘要")
    report.append("-"*30)
    report.append(f"🏆 頭馬命中：{'✅ 是' if hit_win else '❌ 否'}")
    report.append(f"🏅 位置命中：{'✅ 是（跑入前三）' if hit_place else '❌ 否'}")
    
    # 顯示實際頭馬
    if rank_col in result_df.columns:
        actual_winner = result_df[result_df[rank_col] == 1]
        if not actual_winner.empty:
            winner_name = actual_winner.iloc[0].get(name_col, '未知')
            report.append(f"🐎 實際頭馬：{winner_name}")
    
    report.append("="*60)
    
    return "\n".join(report), hit_win, hit_place

# ============================================================
# 4. 主程式
# ============================================================
def main():
    # 加載預測
    pred_df = load_prediction(target_date, target_race)
    if pred_df is None:
        sys.exit(1)
    
    # 加載賽果
    result_df = load_result(target_date, target_race)
    if result_df is None:
        sys.exit(1)
    
    # 執行對比
    report, hit_win, hit_place = compare(pred_df, result_df, target_race)
    print(report)
    
    # 儲存報告
    with open('compare_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("\n💾 報告已儲存至 compare_report.txt")

if __name__ == '__main__':
    main()