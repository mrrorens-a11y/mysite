import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# --- 目的地DB ---
DESTINATIONS_DB = {
    "沖縄美ら海水族館": {"lat": 26.69509427071826, "lon": 127.87787580710211},
    "美ら海水族館": {"lat": 26.69509427071826, "lon": 127.87787580710211},
    "首里城公園": {"lat": 26.21729513013233, "lon": 127.71954766916963},
    "首里城": {"lat": 26.21729513013233, "lon": 127.71954766916963},
    "那覇空港": {"lat": 26.201402381007522, "lon": 127.64684571716576}
}

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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
                "hits": 30
            }
            
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "origin": "https://mysite-l8l0.onrender.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "accept": "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        # 基準点の決定
                        if keyword in DESTINATIONS_DB:
                            base_lat = DESTINATIONS_DB[keyword]["lat"]
                            base_lon = DESTINATIONS_DB[keyword]["lon"]
                        else:
                            first_hotel = data['hotels'][0]['hotel'][0]['hotelBasicInfo']
                            base_lat = float(first_hotel['latitude']) / 3600000
                            base_lon = float(first_hotel['longitude']) / 3600000
                        
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 【ここを修正しました：lon_r ではなく lon_raw に統一】
                            lat_raw = float(info['latitude'])
                            lon_raw = float(info['longitude'])
                            
                            lat = lat_raw / 3600000 if lat_raw > 1000 else lat_raw
                            lon = lon_raw / 3600000 if lon_raw > 1000 else lon_raw

                            dist = calculate_distance(base_lat, base_lon, lat, lon)
                            
                            if dist is not None:
                                info['dist_val'] = dist
                                if dist < 0.05:
                                    info['display_distance'] = "すぐ近く"
                                elif dist < 1.0:
                                    info['display_distance'] = f"{int(dist * 1000)}m"
                                else:
                                    info['display_distance'] = f"{round(dist, 1)}km"
                            else:
                                info['dist_val'] = 9999
                                info['display_distance'] = ""

                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                        
                        # 近い順に並び替え
                        hotels.sort(key=lambda x: x.get('dist_val', 9999))

            except Exception as e:
                print(f"DEBUG: Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
