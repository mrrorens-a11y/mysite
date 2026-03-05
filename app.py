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

@app.route('/')
def health_check():
    # Renderのポートスキャンを即座にパスさせるためのルート
    return "OK", 200

@app.route('/search', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""
    target = DESTINATIONS_DB.get(keyword)
    
    if target:
        url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
        params = {"key": RECRUIT_API_KEY, "lat": target["lat"], "lng": target["lon"], "range": 3, "order": 1, "count": 10, "format": "json"}
        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                j_hotels = res.json().get('results', {}).get('hotel', [])
                for h in j_hotels:
                    h_lat, h_lon = float(h['lat']), float(h['lng'])
                    dist = calc_distance(target["lat"], target["lon"], h_lat, h_lon)
                    hotels.append({
                        "name": h['hotel_name'],
                        "image": h['hotel_image_sample_large'],
                        "display_distance": f"{int(dist*1000)}m" if dist < 1 else f"{round(dist,1)}km",
                        "jalan_price": f"¥{h.get('sample_rate_from', '---')}",
                        "jalan_url": h['plan_list_url']
                    })
        except: pass
    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    # 重要：Renderは環境変数のPORTを最優先で見に行きます
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
