import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

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
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append({
                                "name": info.get('hotelName'),
                                "image": info.get('hotelImageUrl'),
                                "price": info.get('hotelMinCharge'),
                                "address": f"{info.get('address1','')}{info.get('address2','')}",
                                "url": info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            })
            except Exception as e:
                print(f"Error: {e}")
    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    # この3行がポートエラーを消すための「おまじない」です
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
