import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数から取得
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# より安定した標準のAPIエンドポイントに変更
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # 完璧なブラウザのふりをするヘッダー
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "origin": "https://mysite-l8l0.onrender.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "accept": "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            # アフィリエイトURLの取得（ここで収益化）
                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                else:
                    print(f"DEBUG API Error: {res.status_code} - {res.text}")
            except Exception as e:
                print(f"DEBUG Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    # Renderのポート検出エラーを回避するための設定
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
