import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # --- 1. 楽天APIで検索 ---
            r_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
            r_params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 10
            }
            try:
                r_res = requests.get(r_url, params=r_params, timeout=10)
                if r_res.status_code == 200:
                    data = r_res.json()
                    for h in data.get('hotels', []):
                        info = h['hotel'][0]['hotelBasicInfo']
                        hotels.append({
                            "name": info.get('hotelName'),
                            "image": info.get('hotelImageUrl'),
                            "price": f"¥{info.get('hotelMinCharge', '---')}",
                            "url": info.get('affiliateUrl') or info.get('hotelInformationUrl'),
                            "site": "Rakuten"
                        })
            except: pass

            # --- 2. じゃらんAPIで検索 ---
            j_url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
            j_params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 10,
                "format": "json"
            }
            try:
                j_res = requests.get(j_url, params=j_params, timeout=10)
                if j_res.status_code == 200:
                    data = j_res.json()
                    j_hotels = data.get('results', {}).get('hotel', [])
                    for jh in j_hotels:
                        hotels.append({
                            "name": jh.get('hotel_name'),
                            "image": jh.get('hotel_image_sample_large'),
                            "price": f"¥{jh.get('sample_rate_from', '---')}",
                            "url": jh.get('plan_list_url'),
                            "site": "Jalan"
                        })
            except: pass

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
