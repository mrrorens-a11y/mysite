import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# ID類
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # --- 🚀 楽天は「独立」して動かす ---
            try:
                r_res = requests.get(
                    "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426",
                    params={"applicationId": RAKUTEN_APP_ID, "format": "json", "keyword": keyword, "hits": 10},
                    timeout=5 # 5秒で切り上げる
                )
                if r_res.status_code == 200:
                    r_data = r_res.json()
                    for h in r_data.get('hotels', []):
                        info = h['hotel'][0]['hotelBasicInfo']
                        hotels.append({
                            "name": info['hotelName'], "price": info.get('hotelMinCharge', '---'),
                            "url": info['hotelInformationUrl'], "image": info['hotelImageUrl'], "site": "Rakuten"
                        })
            except Exception as e:
                print(f"楽天エラー(無視します): {e}")

            # --- 🚀 じゃらんも「独立」して動かす ---
            # ここでエラーが起きても、上の楽天データ（hotels）は守られます
            if RECRUIT_API_KEY:
                try:
                    j_res = requests.get(
                        "https://webservice.recruit.co.jp/jalan/hotel/v1/",
                        params={"key": RECRUIT_API_KEY, "keyword": keyword, "count": 10, "format": "json"},
                        timeout=5
                    )
                    if j_res.status_code == 200:
                        j_data = j_res.json()
                        for jh in j_data.get('results', {}).get('hotel', []):
                            hotels.append({
                                "name": jh['hotel_name'], "price": jh.get('sample_rate_from', '---'),
                                "url": jh['plan_list_url'], "image": jh['hotel_image_sample_large'], "site": "Jalan"
                            })
                except Exception as e:
                    print(f"じゃらんエラー(無視します): {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
