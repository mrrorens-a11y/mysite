import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数（今の4つをそのまま使用）
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY') # じゃらん用

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # 1. 楽天APIで宿を探す（😊ベース）
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            try:
                r_res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if r_res.status_code == 200:
                    data = r_res.json()
                    for h in data.get('hotels', []):
                        r_info = h['hotel'][0]['hotelBasicInfo']
                        h_name = r_info.get('hotelName')
                        
                        # --- ここで「じゃらん」の料金もこっそり探しに行く ---
                        j_price = "設定なし"
                        j_url = "#"
                        
                        if RECRUIT_API_KEY:
                            j_params = {
                                "key": RECRUIT_API_KEY,
                                "keyword": h_name,
                                "count": 1,
                                "format": "json"
                            }
                            try:
                                j_res = requests.get("https://webservice.recruit.co.jp/jalan/hotel/v1/", params=j_params, timeout=3)
                                if j_res.status_code == 200:
                                    j_data = j_res.json()
                                    j_list = j_data.get('results', {}).get('hotel', [])
                                    if j_list:
                                        j_hotel = j_list[0]
                                        j_price = f"¥{j_hotel.get('sample_rate_from', '---')}"
                                        j_url = j_hotel.get('plan_list_url')
                            except: pass # じゃらんが失敗しても楽天は出す
                        
                        hotels.append({
                            "name": h_name,
                            "image": r_info.get('hotelImageUrl'),
                            "r_price": f"¥{r_info.get('hotelMinCharge', '---')}",
                            "r_url": r_info.get('affiliateUrl') or r_info.get('hotelInformationUrl'),
                            "j_price": j_price,
                            "j_url": j_url,
                            "address": f"{r_info.get('address1','')}{r_info.get('address2','')}"
                        })
            except Exception as e:
                print(f"DEBUG Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
