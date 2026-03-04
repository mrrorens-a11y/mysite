import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数から取得
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 2026年新ドメインのAPIエンドポイント
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    
    # 状況確認用のログ
    print(f"DEBUG: Request Method = {request.method}")

    if request.method == 'POST':
        keyword = request.form.get('keyword')
        print(f"DEBUG: User search keyword = {keyword}")

        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # 【最重要】楽天管理画面と1文字も違わないリファラを送信
            # User-Agentも最新のブラウザのふりをさせます
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
            }

            try:
                # APIリクエスト
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers)
                print(f"DEBUG: API Response Status = {res.status_code}")

                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            # 楽天API特有のデータ階層を正しく抽出
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                        print(f"DEBUG: Success! Found {len(hotels)} hotels")
                else:
                    # 403などが出た場合に原因を表示
                    print(f"DEBUG: API Error Detail = {res.text}")

            except Exception as e:
                print(f"DEBUG: System Error = {str(e)}")
    
    return render_template('index.html', hotels=hotels, keyword=keyword)

# Renderでの起動用
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
