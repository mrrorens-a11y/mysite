import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数からすべて取得
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

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
    error_msg = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            base_lat, base_lon = get_base_coordinates(keyword)
            
            # 楽天APIへ送るパラメータ（400エラー回避のためAccessKeyも追加）
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
                res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 緯度経度の補正
                            lat_r, lon_r = float(info['latitude']), float(info['longitude'])
                            lat = lat_r / 3600000 if lat_r > 1000 else lat_r
                            lon = lon_r / 3600000 if lon_r > 1000 else lon_r

                            if base_lat:
                                dist = calculate_distance(base_lat, base_lon, lat, lon)
                                info['dist_val'] = dist or 9999
                                if dist < 0.05: info['display_distance'] = "すぐ近く"
                                elif dist < 1.0: info['display_distance'] = f"{int(dist * 1000)}m"
                                else: info['display_distance'] = f"{round(dist, 1)}km"
                            else:
                                info['dist_val'] = 9999
                                info['display_distance'] = ""

                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                        
                        # 近い順に並び替え
                        hotels.sort(key=lambda x: x.get('dist_val', 9999))
                    else:
                        error_msg = "宿が見つかりませんでした。"
                else:
                    error_msg = f"楽天APIエラー（{res.status_code}）: IDやキーの設定を確認してください。"
            except Exception as e:
                error_msg = f"通信エラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, error_msg=error_msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
