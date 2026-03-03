import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# --- 設定情報 (Renderの環境変数から読み込みます) ---
# もし直接書き込む場合は 'あなたのID' を消して書き換えてください
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', 'あなたのアプリID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY', 'あなたのアクセスキー')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID', 'あなたのアフィリエイトID')

# 2026年からの新エンドポイント (openapi.rakuten.co.jp)
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
                "hits": 20  # Amazon風にたくさん並べるため20件取得
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params)
                if res.status_code == 200:
                    data = res.json()
                    # 楽天API特有の深い階層からデータを取り出す
                    if 'hotels' in data:
                        for h in data['hotels']:
                            # 基本情報を取り出してリストに追加
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                else:
                    print(f"API Error: {res.status_code}")
            except Exception as e:
                print(f"Error during API request: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

# --- Renderで動かすための重要な設定 ---
if __name__ == "__main__":
    # Renderは環境変数 PORT を指定してくるので、それに合わせます
    port = int(os.environ.get("PORT", 10000))
    # host="0.0.0.0" にすることで外部からのアクセスを許可します
    app.run(host="0.0.0.0", port=port)
