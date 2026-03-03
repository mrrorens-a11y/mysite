import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数から取得（nanoで直接書き込んでも動きますが、公開時は環境変数を推奨）
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', 'あなたのアプリID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY', 'あなたのアクセスキー')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID', 'あなたのアフィリエイトID')

# 新ドメインのエンドポイント
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15  # 表示件数
            }
            res = requests.get(RAKUTEN_API_URL, params=params)
            if res.status_code == 200:
                data = res.json()
                if 'hotels' in data:
                    # APIの階層構造から必要な情報を抽出
                    for h in data['hotels']:
                        info = h['hotel'][0]['hotelBasicInfo']
                        hotels.append(info)
            else:
                print(f"Error: {res.status_code}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == '__main__':
    app.run(debug=True)
