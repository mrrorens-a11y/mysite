import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 緯度経度から距離(km)を計算
def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 【魔法の機能】地名から緯度経度を特定する（ジオコーディング）
def get_coordinates(keyword):
    try:
        # 国土地理院のAPIを利用（無料・登録不要）
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={keyword}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data:
                # 検索結果の1番目の場所の座標を返す
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
            # 1. 検索ワードの場所（0m地点）を特定する
            base_lat, base_lon = get_coordinates(keyword)

            # 2. 楽天APIで宿を探す
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
                res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        # もし地名特定が失敗していたら、1軒目を基準にする（バックアップ用）
                        if base_lat is None:
                            first_h = data['hotels'][0]['hotel'][0]['hotelBasicInfo']
                            base_lat = float(first_h['latitude']) / 3600000
                            base_lon = float(first_h['longitude']) / 3600000
                        
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            lat = float(info['latitude']) / 3600000
                            lon = float(info['longitude']) / 3600000

                            dist = calculate_distance(base_lat, base_lon, lat, lon)
                            
                            if dist is not None:
                                # 単位判定（mかkmか）
                                if dist < 0.05: # 50m以内
                                    info['display_distance'] = "すぐ近く"
                                elif dist < 1.0:
                                    meters = int(dist * 1000)
                                    info['display_distance'] = f"{meters}m"
                                else:
                                    info['display_distance'] = f"{round(dist, 1)}km"
                            
                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
            except Exception as e:
                print(f"DEBUG Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
