import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# APIキー設定（Renderの環境変数から取得）
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 目的地データベース
DESTINATIONS_DB = {
    "沖縄美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "美ら海水族館": {"lat": 26.6943, "lon": 127.8770},
    "首里城公園": {"lat": 26.2172, "lon": 127.7195},
    "那覇空港": {"lat": 26.2014, "lon": 127.6468}
}

def calc_distance(lat1, lon1, lat2, lon2):
    """2地点間の距離を計算(km)"""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def format_distance(dist_km):
    """500mや1.2kmのように分かりやすく変換"""
    if dist_km < 1.0:
        return f"{int(dist_km * 1000)}m"
    else:
        return f"{round(dist_km, 1)}km"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""
    debug_msg = ""
    
    # キーワードがDBにあれば座標検索、なければキーワード検索
    target = DESTINATIONS_DB.get(keyword)
    
    if keyword:
        base_url = "https://webservice.recruit.co.jp/jalan/hotel/v1"
        params = {"key": RECRUIT_API_KEY, "count": 10, "format": "json"}
        
        if target:
            # 座標検索：半径3km以内 (range=3) を距離順 (order=1) で取得
            params.update({"lat": target["lat"], "lng": target["lon"], "range": 3, "order": 1})
        else:
            # キーワード検索
            params.update({"keyword": keyword})

        try:
            res = requests.get(base_url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                j_list = data.get('results', {}).get('hotel', [])
                if isinstance(j_list, dict): j_list = [j_list]
                
                for h in j_list:
                    # 距離計算
                    h_lat, h_lon = float(h.get('lat')), float(h.get('lng'))
                    dist_val = calc_distance(target["lat"], target["lon"], h_lat, h_lon) if target else 0
                    
                    # 楽天APIで同名ホテルの価格を検索
                    rakuten_price = "確認中"
                    rakuten_url = "#"
                    r_params = {
                        "applicationId": RAKUTEN_APP_ID,
                        "affiliateId": RAKUTEN_AFFILIATE_ID,
                        "keyword": h.get('hotel_name'),
                        "hits": 1, "format": "json"
                    }
                    try:
                        r_res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=r_params, timeout=3)
                        if r_res.status_code == 200:
                            r_hotels = r_res.json().get('hotels', [])
                            if r_hotels:
                                r_info = r_hotels[0]['hotel'][0]['hotelBasicInfo']
                                rakuten_price = f"¥{r_info.get('hotelMinCharge', '---')}"
                                rakuten_url = r_info.get('affiliateUrl') or r_info.get('hotelInformationUrl')
                    except: pass

                    hotels.append({
                        "name": h.get('hotel_name'),
                        "image": h.get('hotel_image_sample_large'),
                        "dist_str": format_distance(dist_val) if target else "検索結果",
                        "jalan_price": f"¥{h.get('sample_rate_from', '---')}",
                        "jalan_url": h.get('plan_list_url'),
                        "rakuten_price": rakuten_price,
                        "rakuten_url": rakuten_url
                    })
            else:
                debug_msg = f"じゃらんAPIエラー: {res.status_code}"
        except Exception as e:
            debug_msg = f"システムエラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, debug_msg=debug_msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
