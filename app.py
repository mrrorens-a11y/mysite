import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# Render環境変数
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 目的地DB
DESTINATIONS_DB = {
    "沖縄美ら海水族館": {"lat": 26.695094, "lon": 127.877875},
    "美ら海水族館": {"lat": 26.695094, "lon": 127.877875},
    "首里城公園": {"lat": 26.217295, "lon": 127.719547},
    "首里城": {"lat": 26.217295, "lon": 127.719547},
    "那覇空港": {"lat": 26.201402, "lon": 127.646845}
}

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2: return None
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '')
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 30
            }
            headers = {"referer": "https://mysite-l8l0.onrender.com/"}

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        # 基準点の決定（DBにあれば採用、なければ空にする）
                        target = DESTINATIONS_DB.get(keyword)
                        b_lat = target["lat"] if target else None
                        b_lon = target["lon"] if target else None

                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 宿の座標（ミリ秒を度に変換）
                            h_lat = float(info['latitude']) / 3600000
                            h_lon = float(info['longitude']) / 3600000

                            # 距離計算（DBに地点がある場合のみ実行）
                            if b_lat and b_lon:
                                dist = calculate_distance(b_lat, b_lon, h_lat, h_lon)
                                info['dist_val'] = dist
                                if dist < 0.1: info['display_distance'] = "すぐ近く"
                                elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                                else: info['display_distance'] = f"{round(dist, 1)}km"
                            else:
                                info['dist_val'] = 9999
                                info['display_distance'] = ""

                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            # ★ここが重要：どんな場合も必ずリストに追加する
                            hotels.append(info)
                        
                        # 距離順に並び替え
                        if b_lat:
                            hotels.sort(key=lambda x: x.get('dist_val', 9999))
            except:
                pass

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
