import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 周辺検索APIのURL（こちらの方が位置精度が高い）
RAKUTEN_AROUND_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20170426"

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2: return None
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_base_coordinates(keyword):
    try:
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={keyword}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and res.json():
            lon, lat = res.json()[0]['geometry']['coordinates']
            return lat, lon
    except: return None, None
    return None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            # 1. まず検索地点の座標（緯度経度）を特定
            base_lat, base_lon = get_base_coordinates(keyword)

            if base_lat:
                # 2. その座標の「半径3km以内」にある宿を検索
                params = {
                    "applicationId": RAKUTEN_APP_ID,
                    "affiliateId": RAKUTEN_AFFILIATE_ID,
                    "format": "json",
                    "latitude": base_lat,
                    "longitude": base_lon,
                    "searchRadius": 3, # 半径3km以内
                    "datumType": 1     # 世界測地系で固定（これで距離が狂わない）
                }
                headers = {"referer": "https://mysite-l8l0.onrender.com/"}

                try:
                    res = requests.get(RAKUTEN_AROUND_URL, params=params, headers=headers, timeout=10)
                    if res.status_code == 200:
                        data = res.json()
                        if 'hotels' in data:
                            for h in data['hotels']:
                                info = h['hotel'][0]['hotelBasicInfo']
                                # 距離計算
                                dist = calculate_distance(base_lat, base_lon, float(info['latitude']), float(info['longitude']))
                                
                                if dist is not None:
                                    info['dist_val'] = dist
                                    if dist < 0.05: info['display_distance'] = "すぐ近く"
                                    elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                                    else: info['display_distance'] = f"{round(dist, 1)}km"
                                
                                info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                                hotels.append(info)
                            
                            # 近い順にソート
                            hotels.sort(key=lambda x: x.get('dist_val', 9999))
                except Exception as e: print(f"Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
