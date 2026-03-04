import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

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
                "hits": 20
            }
            # セッションとヘッダーの固定（403対策）
            session = requests.Session()
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            try:
                res = session.get(RAKUTEN_API_URL, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 【重要】リンク先をセットするロジック
                            # 1. アフィリエイトURLがあればそれを使う
                            # 2. なければ通常のURLを使う
                            # 3. どちらもなければ楽天トラベルTOP（保険）
                            raw_url = info.get('hotelInformationUrl', 'https://travel.rakuten.co.jp/')
                            aff_url = info.get('affiliateUrl')
                            
                            info['target_url'] = aff_url if aff_url else raw_url
                            
                            hotels.append(info)
                    else:
                        print("DEBUG: 宿が見つかりませんでした。")
                else:
                    print(f"DEBUG: API Error: {res.status_code} - {res.text}")
            except Exception as e:
                print(f"DEBUG: System Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
