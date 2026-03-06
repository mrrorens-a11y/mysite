import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数から取得（IDに間違いがない前提で進めます）
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY') # アクセスキーを読み込み
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# アクセスキー必須のOpenAPIエンドポイントを使用
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY, # アクセスキーをパラメータに追加
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # OpenAPIが「有効なリクエスト」と認めるためのヘッダー構成
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "accept": "application/json"
            }

            try:
                # リクエスト実行
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            # アフィリエイトURLを取得、なければ通常URLを格納
                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                else:
                    # 400エラー等の場合、何が足りないのか詳細をログに出す
                    print(f"DEBUG API Error: {res.status_code} - {res.text}")
                    
            except Exception as e:
                print(f"DEBUG Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
