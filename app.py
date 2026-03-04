import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# RenderのEnvironment Variablesから取得
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
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                else:
                    print(f"API Error: {res.text}")
            except Exception as e:
                print(f"System Error: {e}")
    
    return render_template('index.html', hotels=hotels, keyword=keyword)

# この下の2行が「一番左端」から始まっていることが成功の絶対条件です
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
