import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 検索ワードの座標を取得する関数
def get_base_coordinates(keyword):
    try:
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={keyword}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data:
                # 経度, 緯度の順で入っているので入れ替えて返す
                lon, lat = data[0]['geometry']['coordinates']
                return lat, lon
    except:
        return None, None
    return None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            # 1. 検索地点（0m地点）の座標を特定
            base_lat, base_lon = get_base_coordinates(keyword)

            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 30 # ソート精度を上げるため少し多めに取得
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
                        # 地点特定に失敗していたら1軒目を基準にするバックアップ
                        if base_lat is None:
                            f_info = data['hotels'][0]['hotel'][0]['hotelBasicInfo']
                            f_lat_raw = float(f_info['latitude'])
                            base_lat = f_lat_raw / 3600000 if f_lat_raw > 1000 else f_lat_raw
                            f_lon_raw = float(f_info['longitude'])
                            base_lon = f_lon_raw / 3600000 if f_lon_raw > 1000 else f_lon_raw

                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 楽天の緯度経度補正（ミリ秒なら360万で割る）
                            lat_raw = float(info['latitude'])
                            lat = lat_raw / 3600000 if lat_raw > 1000 else lat_raw
                            lon_raw = float(info['longitude'])
                            lon = lon_raw / 3600000 if lon_raw > 1000 else lon_raw

                            dist = calculate_distance(base_lat, base_lon, lat, lon)
                            
                            if dist is not None:
                                info['dist_val'] = dist # 並び替え用の数値
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
                        
                        # ★ 距離が近い順に並び替え
                        hotels.sort(key=lambda x: x.get('dist_val', 9999))

            except Exception as e:
                print(f"DEBUG: Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
