from flask import Flask, request, render_template_string
import joblib
import numpy as np
import re
import unicodedata

app = Flask(__name__)

# 載入你個 AI 模型
try:
    MODEL = joblib.load('hk_racing_model.pkl')
    print("✅ AI 模型已成功載入！")
except:
    print("❌ 搵唔到模型！請先執行 python train_place_final.py")

# 手機版網頁 HTML (繁體中文)
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SHTSN 賽馬預測 (手機版)</title>
    <style>
        body { background-color: #1e2d24; color: #f5c542; font-family: Arial, sans-serif; padding: 20px; text-align: center; }
        input { width: 90%; padding: 12px; margin: 15px 0; border-radius: 5px; border: none; font-size: 16px; }
        button { padding: 12px 30px; background: #f5c542; color: #1e2d24; border: none; border-radius: 5px; font-weight: bold; font-size: 18px; cursor: pointer; }
        .result { margin-top: 20px; background: #263b30; padding: 20px; border-radius: 10px; color: #ffffff; text-align: left; line-height: 1.8; font-size: 16px; }
        .good { color: #f5c542; font-weight: bold; }
        .bad { color: #ff6b6b; }
        .info { font-size: 12px; color: #8aa091; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h2>🕷️ SHTSN 即時預測</h2>
    <p class="info">請輸入 17 個數字 (用空格分隔)</p>
    <form method="post">
        <input type="text" name="data" placeholder="例如: 4.0 0.0 1650.0 0 4.0 0.125..." required>
        <button type="submit">🔮 立即預測</button>
    </form>
    <div class="result">{{ result | safe }}</div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def predict():
    result = ""
    if request.method == 'POST':
        inp = request.form.get('data', '')
        try:
            # 強制清洗輸入數據
            normalized = unicodedata.normalize('NFKD', inp)
            cleaned = re.sub(r'[^0-9.\-]', ' ', normalized)
            data = [float(x) for x in cleaned.split() if x != '']

            if len(data) != 17:
                result = f"⚠️ 模型需要 <b>17</b> 個數字，你只輸入咗 <b>{len(data)}</b> 個。"
            else:
                prob = MODEL.predict_proba(np.array([data]))[0][1]
                odds = data[9]  # 賠率 (第10個數字)
                
                if odds == 0:
                    market_prob = 0
                    value_score = 0
                else:
                    market_prob = 1 / odds
                    value_score = prob - market_prob

                # 繁體中文輸出
                res = f"📊 <b>AI 估計勝率</b>: {prob*100:.1f}%<br>"
                res += f"📊 <b>市場預期勝率</b>: {market_prob*100:.1f}%<br>"
                
                CONFIDENCE_THRESHOLD = 0.15
                if prob >= CONFIDENCE_THRESHOLD:
                    if value_score > 0.1:
                        res += f"<br><span class='good'>💰 超級值博！</span><br>AI 比市場睇高 <b>{value_score*100:.1f}%</b>"
                    else:
                        res += f"<br><span class='good'>🏆 AI 勝算極高！</span><br>信心: {prob*100:.1f}%"
                else:
                    if value_score > 0.1:
                        res += f"<br><span class='good'>⚠️ 信心稍低</span><br>但值博率極高，可小注嘗試！"
                    else:
                        res += f"<br><span class='bad'>❌ 信心唔夠，唔值博。</span>"
                result = res
        except Exception as e:
            result = f"❌ 輸入格式錯誤！請確保係有效數字。<br><span style='font-size:12px; color:#aaa;'>{str(e)}</span>"
    return render_template_string(HTML_PAGE, result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)