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

                        # 基準点の特定ロジック

                        # 1番目の宿の座標を「目的地の代表点」として採用（後ほどAPI連携でさらに強化可能）

                        # まず、リスト全体を見て一番「中心」に近いものを推測します

                        first_hotel = data['hotels'][0]['hotel'][0]['hotelBasicInfo']

                        base_lat = float(first_hotel['latitude']) / 3600000

                        base_lon = float(first_hotel['longitude']) / 3600000

                        

                        for h in data['hotels']:

                            info = h['hotel'][0]['hotelBasicInfo']

                            lat = float(info['latitude']) / 3600000

                            lon = float(info['longitude']) / 3600000



                            dist = calculate_distance(base_lat, base_lon, lat, lon)

                            

                            if dist is not None:

                                # 単位と表示の修正

                                if dist < 0.1: # 100m以内

                                    info['display_distance'] = "すぐ近く"

                                elif dist < 1.0: # 1km未満はメートル表示

                                    # 0.5km → 500m

                                    meters = int(dist * 1000)

                                    info['display_distance'] = f"{meters}m"

                                else: # 1km以上はキロ表示

                                    # 1.234km → 1.2km

                                    info['display_distance'] = f"{round(dist, 1)}km"

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
