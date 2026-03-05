import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# メイン: 周辺検索API / サブ: キーワード検索API
RAKUTEN_AROUND_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20170426"
RAKUTEN_KEYWORD_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

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
            base_lat, base_lon = get_base_coordinates(keyword)
            headers = {"referer": "https://mysite-l8l0.onrender.com/"}
            
            # --- 戦略1: まずは周辺検索で攻める ---
            if base_lat:
                params = {
                    "applicationId": RAKUTEN_APP_ID,
                    "affiliateId": RAKUTEN_AFFILIATE_ID,
                    "format": "json",
                    "latitude": base_lat,
                    "longitude": base_lon,
                    "searchRadius": 30, # 範囲を30kmに拡大して確実性を高める
                    "datumType": 1
                }
                try:
                    res = requests.get(RAKUTEN_AROUND_URL, params=params, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        if 'hotels' in data:
                            for h in data['hotels']:
                                info = h['hotel'][0]['hotelBasicInfo']
                                dist = calculate_distance(base_lat, base_lon, float(info['latitude']), float(info['longitude']))
                                info['dist_val'] = dist or 9999
                                if dist is not None:
                                    if dist < 0.05: info['display_distance'] = "すぐ近く"
                                    elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                                    else: info['display_distance'] = f"{round(dist, 1)}km"
                                info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                                hotels.append(info)
                except: pass

            # --- 戦略2: 周辺検索で1件も出なかったらキーワード検索に切り替える（保険） ---
            if not hotels:
                params_kw = {
                    "applicationId": RAKUTEN_APP_ID,
                    "affiliateId": RAKUTEN_AFFILIATE_ID,
                    "format": "json",
                    "keyword": keyword,
                    "hits": 20
                }
                try:
                    res_kw = requests.get(RAKUTEN_KEYWORD_URL, params=params_kw, headers=headers)
                    if res_kw.status_code == 200:
                        data_kw = res_kw.json()
                        if 'hotels' in data_kw:
                            for h in data_kw['hotels']:
                                info = h['hotel'][0]['hotelBasicInfo']
                                # 座標補正
                                lat_r = float(info['latitude'])
                                lat = lat_r / 3600000 if lat_r > 1000 else lat_r
                                lon_r = float(info['longitude'])
                                lon = lon_r / 3600000 if lon_r > 1000 else lon_r
                                
                                if base_lat:
                                    dist = calculate_distance(base_lat, base_lon, lat, lon)
                                    info['dist_val'] = dist or 9999
                                    if dist is not None:
                                        if dist < 0.05: info['display_distance'] = "すぐ近く"
                                        elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                                        else: info['display_distance'] = f"{round(dist, 1)}km"
                                else:
                                    info['dist_val'] = 9999
                                info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                                hotels.append(info)
                except: pass

            # 最後に距離順で並び替え
            if hotels:
                hotels.sort(key=lambda x: x.get('dist_val', 9999))

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
