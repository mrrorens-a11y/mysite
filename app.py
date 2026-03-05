import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 緯度経度から距離（km）を計算する関数（ヒュベニの公式風）
def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
    # 地球の半径 (km)
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
                "hits": 20
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
                        # 最初の宿の場所を「検索地点の基準」にする（簡易的な距離表示用）
                        base_lat = None
                        base_lon = None
                        
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 1軒目の宿の座標を基準点とする（「このエリアの中心」からの距離とするため）
                            if base_lat is None:
                                base_lat = float(info['latitude'])
                                base_lon = float(info['longitude'])

                            # 距離計算
                            dist = calculate_distance(base_lat, base_lon, float(info['latitude']), float(info['longitude']))
                            
                            # 距離の表示形式を整える
                            if dist is not None:
                                if dist < 1.0:
                                    info['display_distance'] = f"{int(dist * 1000)}m" # 1km未満はm表示
                                else:
                                    info['display_distance'] = f"{round(dist, 1)}km" # 1km以上はkm表示
                            else:
                                info['display_distance'] = ""

                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
            except Exception as e:
                print(f"DEBUG: Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
