import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 目的地DB
DESTINATIONS_DB = {
    "美ら海": {"lat": 26.695094, "lon": 127.877875},
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
                "hits": 20 # 20に戻して安定させます
            }
            headers = {"referer": "https://mysite-l8l0.onrender.com/"}

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        # 基準点の決定：DBのキーワードが含まれているか判定
                        base_lat, base_lon = None, None
                        for name, coords in DESTINATIONS_DB.items():
                            if name in keyword:
                                base_lat, base_lon = coords["lat"], coords["lon"]
                                break
                        
                        # DBになければ1軒目を基準にする（成功コードのロジック）
                        if not base_lat:
                            f_info = data['hotels'][0]['hotel'][0]['hotelBasicInfo']
                            f_lat = float(f_info['latitude'])
                            base_lat = f_lat / 3600000 if f_lat > 1000 else f_lat
                            f_lon = float(f_info['longitude'])
                            base_lon = f_lon / 3600000 if f_lon > 1000 else f_lon

                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            # 宿の座標を「度」に変換
                            h_lat_raw = float(info['latitude'])
                            h_lon_raw = float(info['longitude'])
                            h_lat = h_lat_raw / 3600000 if h_lat_raw > 1000 else h_lat_raw
                            h_lon = h_lon_raw / 3600000 if h_lon_raw > 1000 else h_lon_raw

                            dist = calculate_distance(base_lat, base_lon, h_lat, h_lon)
                            
                            info['dist_val'] = dist if dist is not None else 9999
                            if dist is not None:
                                if dist < 0.1: info['display_distance'] = "すぐ近く"
                                elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                                else: info['display_distance'] = f"{round(dist, 1)}km"
                            else:
                                info['display_distance'] = ""

                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                        
                        # 近い順に並び替え
                        hotels.sort(key=lambda x: x.get('dist_val', 9999))
            except: pass

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
