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
    
    # ログ出力1: アクセスが来たことを知らせる
    print(f"DEBUG: Request Method = {request.method}")

    if request.method == 'POST':
        keyword = request.form.get('keyword')
        print(f"DEBUG: User searched for = {keyword}") # ログ出力2: キーワードの確認

        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers)
                print(f"DEBUG: API Status = {res.status_code}") # ログ出力3: APIの結果

                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                        print(f"DEBUG: Found {len(hotels)} hotels") # ログ出力4: 見つかった数
                else:
                    print(f"DEBUG: API Error Detail = {res.text}")
            except Exception as e:
                print(f"DEBUG: System Error = {str(e)}")
    
    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
