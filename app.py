import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# APIキー設定（Render環境変数から）
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 目的地DB
DESTINATIONS_DB = {
    "沖縄美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "首里城公園": {"lat": 26.2172, "lon": 127.7195},
    "那覇空港": {"lat": 26.2014, "lon": 127.6468}
}

# --- 🔥 正確なHaversine距離計算 ---
def calc_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # 地球の半径 (km)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        target = DESTINATIONS_DB.get(keyword)
        
        if target:
            # 1. じゃらんAPIで「座標から半径3km」を検索（じゃらんは「度」でOK！）
            jalan_url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
            j_params = {
                "key": RECRUIT_API_KEY,
                "lat": target["lat"],
                "lng": target["lon"],
                "range": 3,      # 半径3km
                "order": 1,      # 距離が近い順
                "count": 15,     # 15件程度が安定
                "format": "json"
            }
            
            try:
                res = requests.get(jalan_url, params=j_params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get('results', {}).get('hotel', [])
                    
                    for h in results:
                        # じゃらんの基本情報
                        h_lat = float(h['lat'])
                        h_lon = float(h['lng'])
                        dist = calc_distance(target["lat"], target["lon"], h_lat, h_lon)
                        
                        # 2. 楽天APIに「その宿名」で価格を聞きに行く（簡易検索）
                        rakuten_price = "確認中"
                        rakuten_url = ""
                        r_params = {
                            "applicationId": RAKUTEN_APP_ID,
                            "affiliateId": RAKUTEN_AFFILIATE_ID,
                            "keyword": h['hotel_name'],
                            "hits": 1,
                            "format": "json"
                        }
                        r_res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=r_params)
                        if r_res.status_code == 200:
                            r_data = r_res.json()
                            if 'hotels' in r_data:
                                r_info = r_data['hotels'][0]['hotel'][0]['hotelBasicInfo']
                                rakuten_price = f"¥{r_info.get('hotelMinCharge', '---')}"
                                rakuten_url = r_info.get('affiliateUrl') or r_info.get('hotelInformationUrl')

                        # データをまとめる
                        hotels.append({
                            "name": h['hotel_name'],
                            "image": h['hotel_image_sample_large'],
                            "dist_val": dist,
                            "display_distance": f"{int(dist*1000)}m" if dist < 1 else f"{round(dist,1)}km",
                            "jalan_price": f"¥{h.get('sample_rate_from', '---')}",
                            "rakuten_price": rakuten_price,
                            "jalan_url": h['plan_list_url'], # 後でアフィリンクに置換可能
                            "rakuten_url": rakuten_url
                        })
            except Exception as e:
                print(f"DEBUG: Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
