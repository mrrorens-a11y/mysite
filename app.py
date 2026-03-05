import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 目的地DB（あなたが指定した緯度経度）
DESTINATIONS_DB = {
    "沖縄美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "首里城公園": {"lat": 26.2172, "lon": 127.7195},
    "那覇空港": {"lat": 26.2014, "lon": 127.6468}
}

# --- 🔥 OTAも使っているHaversine公式 ---
def calc_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # 地球の半径 (km)
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        
        # 1. DBから目的地の座標を取得
        target = DESTINATIONS_DB.get(keyword)
        
        if target:
            # 2. 楽天API (VacationHotelSearch) - 座標指定で半径3kmを検索
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "latitude": target["lat"],
                "longitude": target["lon"],
                "searchRadius": 3, # 半径3km
                "hits": 20
            }
            # 緯度経度検索用のURL
            url = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20170426"
        else:
            # DBにない場合は通常のキーワード検索（保険）
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if 'hotels' in data:
                    for h in data['hotels']:
                        info = h['hotel'][0]['hotelBasicInfo']
                        
                        # 3. 楽天の座標を「ミリ秒」から「度」へ変換
                        # 楽天APIは一貫してミリ秒で返るため 3600000 で割る
                        h_lat = float(info['latitude']) / 3600000
                        h_lon = float(info['longitude']) / 3600000

                        # 4. 距離計算（DBに地点がある場合のみ、公式を使用）
                        if target:
                            dist = calc_distance(target["lat"], target["lon"], h_lat, h_lon)
                            info['dist_val'] = dist
                            if dist < 0.1: info['display_distance'] = "すぐ近く"
                            elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                            else: info['display_distance'] = f"{round(dist, 1)}km"
                        else:
                            info['dist_val'] = 9999
                            info['display_distance'] = ""

                        info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                        hotels.append(info)
                    
                    # 5. 距離順で並び替え
                    hotels.sort(key=lambda x: x.get('dist_val', 9999))
        except:
            pass

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
