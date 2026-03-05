import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2: return None
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_coordinates(keyword):
    try:
        # 国土地理院APIで検索ワードの座標を取得
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={keyword}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and res.json():
            # 経度、緯度の順で返ってくるので入れ替え
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
            # 1. 検索ワードから基準となる座標を特定
            base_lat, base_lon = get_coordinates(keyword)
            
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 30
            }
            # 403回避のためのヘッダー設定
            headers = {"referer": "https://mysite-l8l0.onrender.com/"}

            try:
                res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 緯度経度の「ミリ秒/度」を判別して正しく補正
                            raw_lat, raw_lon = float(info['latitude']), float(info['longitude'])
                            lat = raw_lat / 3600000 if raw_lat > 1000 else raw_lat
                            lon = raw_lon / 3600000 if raw_lon > 1000 else raw_lon

                            # 距離計算
                            if base_lat:
                                info['dist_val'] = calculate_distance(base_lat, base_lon, lat, lon)
                                # 単位の出し分け
                                if info['dist_val'] < 0.05: info['display_distance'] = "すぐ近く"
                                elif info['dist_val'] < 1.0: info['display_distance'] = f"{int(info['dist_val'] * 1000)}m"
                                else: info['display_distance'] = f"{round(info['dist_val'], 1)}km"
                            else:
                                info['dist_val'] = 9999
                                info['display_distance'] = ""

                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                        
                        # 2. 距離が近い順（dist_valが小さい順）に並び替え
                        hotels.sort(key=lambda x: x.get('dist_val', 9999))
            except Exception as e:
                print(f"Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
