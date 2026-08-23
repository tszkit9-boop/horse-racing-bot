#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
trend_report.py - 預測準確度趨勢報告
用法:
  python trend_report.py              # 預設近30日
  python trend_report.py --days 60    # 近60日
  python trend_report.py --date 2026-08-01 --days 30
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 無頭模式

# ============================================================
# 參數
# ============================================================
parser = argparse.ArgumentParser(description='預測準確度趨勢報告')
parser.add_argument('--days', type=int, default=30, help='分析最近N日，預設30')
parser.add_argument('--date', type=str, help='指定結束日期，預設今日')
args = parser.parse_args()

# ============================================================
# 1. 設定日期範圍
# ============================================================
if args.date:
    end_date = pd.to_datetime(args.date)
else:
    end_date = datetime.now()

start_date = end_date - timedelta(days=args.days)
print(f"📊 分析期間：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

# ============================================================
# 2. 讀取預測歷史記錄
# ============================================================
def load_predictions(date_range_start, date_range_end):
    """讀取 prediction_history 入面指定日期範圍嘅預測記錄"""
    history_folder = 'prediction_history'
    if not os.path.exists(history_folder):
        print(f"❌ 找不到 {history_folder}")
        return None
    
    files = glob.glob(os.path.join(history_folder, 'prediction_*.csv'))
    if not files:
        print("❌ 沒有預測記錄")
        return None
    
    all_pred = []
    for f in files:
        # 從檔名提取日期 (prediction_YYYY-MM-DD_場次X_時間.csv)
        match = re.search(r'prediction_(\d{4}-\d{2}-\d{2})', f)
        if match:
            pred_date = pd.to_datetime(match.group(1))
            if start_date <= pred_date <= end_date:
                try:
                    df = pd.read_csv(f, encoding='utf-8-sig')
                    df['預測日期'] = pred_date
                    all_pred.append(df)
                except:
                    continue
    
    if not all_pred:
        print("❌ 沒有找到符合日期範圍嘅預測記錄")
        return None
    
    combined = pd.concat(all_pred, ignore_index=True)
    print(f"📋 找到 {len(combined)} 筆預測記錄，來自 {len(all_pred)} 個檔案")
    return combined

# ============================================================
# 3. 讀取實際賽果
# ============================================================
def load_results(date_range_start, date_range_end):
    """讀取 full_data_*.csv 入面指定日期範圍嘅賽果"""
    files = glob.glob('full_data_*.csv')
    if not files:
        print("❌ 沒有賽果數據")
        return None
    
    all_results = []
    date_pattern = re.compile(r'full_data_(\d{4}-\d{2}-\d{2})\.csv')
    
    for f in files:
        match = date_pattern.search(f)
        if match:
            race_date = pd.to_datetime(match.group(1))
            if start_date <= race_date <= end_date:
                try:
                    df = pd.read_csv(f, encoding='utf-8-sig')
                    df['賽事日期'] = race_date
                    all_results.append(df)
                except:
                    continue
    
    if not all_results:
        print("❌ 沒有找到符合日期範圍嘅賽果數據")
        return None
    
    combined = pd.concat(all_results, ignore_index=True)
    print(f"📋 找到 {len(combined)} 筆賽果記錄")
    return combined

# ============================================================
# 4. 對比分析
# ============================================================
def analyze(pred_df, result_df, start_date, end_date):
    """對比預測 vs 賽果，計算每日命中率"""
    
    # 找名次欄位
    rank_col = '名次' if '名次' in result_df.columns else 'finish_position'
    if rank_col not in result_df.columns:
        print("❌ 賽果數據缺少名次欄位")
        return None
    
    # 找馬名欄位
    name_col = '馬名' if '馬名' in result_df.columns else 'horse_id'
    if name_col not in result_df.columns:
        name_col = '馬匹名稱'
    
    # 逐日統計
    daily_stats = []
    date_range = pd.date_range(start_date, end_date)
    
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        
        # 該日預測
        day_pred = pred_df[pred_df['預測日期'].dt.date == date.date()]
        # 該日賽果
        day_result = result_df[result_df['賽事日期'].dt.date == date.date()]
        
        if day_pred.empty or day_result.empty:
            continue
        
        # 逐場比對
        race_nos = sorted(day_pred['場次'].unique())
        total_races = len(race_nos)
        hit_win = 0
        hit_place = 0
        
        for race_no in race_nos:
            race_pred = day_pred[day_pred['場次'] == race_no]
            race_result = day_result[day_result['場次'] == race_no]
            
            if race_pred.empty or race_result.empty:
                continue
            
            # 取預測頭馬
            pred_winner = race_pred.iloc[0]['馬匹名稱']
            
            # 搵實際頭馬
            actual_winner = race_result[race_result[rank_col] == 1]
            if not actual_winner.empty:
                actual_name = actual_winner.iloc[0].get(name_col, '')
                if actual_name == pred_winner:
                    hit_win += 1
                    
                # 位置命中 (跑入前三)
                place_horses = race_result[race_result[rank_col] <= 3][name_col].tolist()
                if pred_winner in place_horses:
                    hit_place += 1
        
        win_rate = hit_win / total_races * 100 if total_races > 0 else 0
        place_rate = hit_place / total_races * 100 if total_races > 0 else 0
        
        daily_stats.append({
            '日期': date_str,
            '場次': total_races,
            '頭馬命中': hit_win,
            '位置命中': hit_place,
            '頭馬命中率': win_rate,
            '位置命中率': place_rate
        })
    
    return pd.DataFrame(daily_stats)

# ============================================================
# 5. 生成報告（文字 + 圖表）
# ============================================================
def generate_report(daily_df):
    """生成文字報告"""
    if daily_df.empty:
        return "❌ 沒有足夠數據生成報告"
    
    total_days = len(daily_df)
    total_races = daily_df['場次'].sum()
    total_win_hits = daily_df['頭馬命中'].sum()
    total_place_hits = daily_df['位置命中'].sum()
    
    avg_win_rate = daily_df['頭馬命中率'].mean()
    avg_place_rate = daily_df['位置命中率'].mean()
    
    # 找出最佳/最差日子
    best_day = daily_df.loc[daily_df['頭馬命中率'].idxmax()]
    worst_day = daily_df.loc[daily_df['頭馬命中率'].idxmin()]
    
    # 每週平均
    daily_df['週'] = pd.to_datetime(daily_df['日期']).dt.isocalendar().week
    weekly = daily_df.groupby('週')['頭馬命中率'].mean().round(1)
    
    # 趨勢判斷（最近7日 vs 整體平均）
    recent = daily_df.tail(7)
    recent_avg = recent['頭馬命中率'].mean()
    
    trend = '⬆️ 上升' if recent_avg > avg_win_rate else '⬇️ 下降'
    trend_msg = '模型表現穩定' if abs(recent_avg - avg_win_rate) < 3 else f'模型表現有 {trend} 趨勢'
    
    # 構建報告
    report = []
    report.append("="*60)
    report.append(f"📊 預測準確度趨勢報告")
    report.append(f"📅 {daily_df['日期'].min()} 至 {daily_df['日期'].max()}")
    report.append("="*60)
    report.append("")
    report.append("📈 每日命中率走勢：")
    
    # 顯示最近14日
    for _, row in daily_df.tail(14).iterrows():
        bar = '█' * int(row['頭馬命中率'] / 2)
        report.append(f"  {row['日期']} {bar} {row['頭馬命中率']:.1f}%")
    
    report.append("")
    report.append("📊 每週平均：")
    for week, rate in weekly.items():
        report.append(f"  第{week}週：{rate:.1f}%")
    
    report.append("")
    report.append("📋 總結：")
    report.append(f"  - 總日數：{total_days} 日")
    report.append(f"  - 總場次：{total_races} 場")
    report.append(f"  - 頭馬命中：{total_win_hits} 場")
    report.append(f"  - 頭馬命中率：{avg_win_rate:.1f}%")
    report.append(f"  - 位置命中率：{avg_place_rate:.1f}%")
    report.append("")
    report.append(f"🏆 最佳日子：{best_day['日期']}（{best_day['頭馬命中率']:.1f}%）")
    report.append(f"📉 最差日子：{worst_day['日期']}（{worst_day['頭馬命中率']:.1f}%）")
    report.append("")
    report.append(f"📌 趨勢分析：{trend_msg}")
    report.append("="*60)
    
    return "\n".join(report)

def generate_chart(daily_df):
    """生成走勢圖"""
    if daily_df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    dates = pd.to_datetime(daily_df['日期'])
    win_rates = daily_df['頭馬命中率']
    place_rates = daily_df['位置命中率']
    
    ax.plot(dates, win_rates, marker='o', linewidth=2, label='頭馬命中率', color='#2ecc71')
    ax.plot(dates, place_rates, marker='s', linewidth=2, label='位置命中率', color='#3498db')
    
    # 平均線
    avg_win = win_rates.mean()
    ax.axhline(y=avg_win, color='red', linestyle='--', linewidth=1, label=f'平均 {avg_win:.1f}%')
    
    # 7日移動平均
    if len(win_rates) >= 7:
        ma7 = win_rates.rolling(7, min_periods=1).mean()
        ax.plot(dates, ma7, color='orange', linestyle=':', linewidth=2, label='7日移動平均')
    
    ax.set_xlabel('日期')
    ax.set_ylabel('命中率 (%)')
    ax.set_title('賽馬預測準確度走勢')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(100, max(win_rates.max(), place_rates.max()) + 10))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 儲存
    chart_path = 'trend_chart.png'
    plt.savefig(chart_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    return chart_path

# ============================================================
# 6. 主程式
# ============================================================
def main():
    # 載入數據
    pred_df = load_predictions(start_date, end_date)
    if pred_df is None:
        sys.exit(1)
    
    result_df = load_results(start_date, end_date)
    if result_df is None:
        sys.exit(1)
    
    # 分析
    daily_df = analyze(pred_df, result_df, start_date, end_date)
    if daily_df is None or daily_df.empty:
        print("❌ 分析失敗，沒有足夠數據")
        sys.exit(1)
    
    # 生成報告
    report = generate_report(daily_df)
    print(report)
    
    # 生成圖表
    chart_path = generate_chart(daily_df)
    if chart_path:
        print(f"📊 圖表已儲存至 {chart_path}")
    
    # 儲存報告
    with open('trend_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("💾 報告已儲存至 trend_report.txt")

if __name__ == '__main__':
    main()