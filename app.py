import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 目的地DB
DESTINATIONS_DB = {
    "沖縄美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "首里城公園": {"lat": 26.2172, "lon": 127.7195},
    "那覇空港": {"lat": 26.2014, "lon": 127.6468}
}

def calc_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    # GETのときは空、POST（検索）のときだけキーワード取得
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""
    target = DESTINATIONS_DB.get(keyword)
    
    if target:
        url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
        # じゃらんAPI：距離順(order=1)で10件取得
        params = {
            "key": RECRUIT_API_KEY, 
            "lat": target["lat"], 
            "lng": target["lon"], 
            "range": 3, 
            "order": 1, 
            "count": 10, 
            "format": "json"
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                j_hotels = res.json().get('results', {}).get('hotel', [])
                for h in j_hotels:
                    h_lat, h_lon = float(h['lat']), float(h['lng'])
                    dist = calc_distance(target["lat"], target["lon"], h_lat, h_lon)
                    
                    # 楽天の価格も1件ずつ取得（上位5件に絞るのが安全ですが、まずは10件トライ）
                    rakuten_price = "確認中"
                    rakuten_url = ""
                    r_params = {
                        "applicationId": RAKUTEN_APP_ID,
                        "affiliateId": RAKUTEN_AFFILIATE_ID,
                        "keyword": h['hotel_name'],
                        "hits": 1,
                        "format": "json"
                    }
                    try:
                        r_res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=r_params, timeout=3)
                        if r_res.status_code == 200:
                            r_data = r_res.json()
                            if 'hotels' in r_data:
                                r_info = r_data['hotels'][0]['hotel'][0]['hotelBasicInfo']
                                rakuten_price = f"¥{r_info.get('hotelMinCharge', '---')}"
                                rakuten_url = r_info.get('affiliateUrl') or r_info.get('hotelInformationUrl')
                    except: pass

                    hotels.append({
                        "name": h['hotel_name'],
                        "image": h['hotel_image_sample_large'],
                        "display_distance": f"{int(dist*1000)}m" if dist < 1 else f"{round(dist,1)}km",
                        "jalan_price": f"¥{h.get('sample_rate_from', '---')}",
                        "rakuten_price": rakuten_price,
                        "jalan_url": h['plan_list_url'],
                        "rakuten_url": rakuten_url
                    })
        except Exception as e:
            print(f"ERROR: {e}")
            
    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
