import os
import math
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 📍 目的地DB (美ら海水族館の正確な座標) ---
DESTINATIONS = {
    "美ら海水族館": {
        "lat": 26.694542346577375, 
        "lng": 127.8779368039277, 
        "search_word": "本部町"
    }
}

# --- 📏 Haversine距離計算 (これが心臓部です) ---
def get_display_distance(lat1, lon1, lat2, lon2):
    try:
        # APIから文字で来ても計算できるようにfloat(小数)へ変換
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        
        R = 6371  # 地球の半径 (km)
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi / 2)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        dist_m = R * c * 1000  # メートルに変換
        
        # あなたの理想: 1km未満は500m、以上は2.34kmのような表示
        if dist_m < 1000:
            return f"{int(dist_m)}m"
        else:
            return f"{round(dist_m / 1000, 2)}km"
    except (TypeError, ValueError, Exception):
        return None

# --- じゃらん料金取得 ---
def get_jalan_info(hotel_name):
    if not RECRUIT_API_KEY: return "---", None
    try:
        params = {"key": RECRUIT_API_KEY, "keyword": hotel_name, "format": "json", "count": 1}
        res = requests.get(JALAN_API_URL, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and "hotel" in data["results"]:
                h = data["results"]["hotel"][0]
                if fuzz.token_sort_ratio(hotel_name, h["hotelName"]) > 75:
                    price = h.get("sampleRateFrom")
                    return (f"¥{price}" if price else "---"), h.get("urls", {}).get("pc")
    except: pass
    return "---", None

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            target_info = DESTINATIONS.get(keyword)
            # 特定のスポットなら検索ワードを最適化（美ら海水族館なら本部町で検索）
            api_keyword = target_info["search_word"] if target_info else keyword

            params = {"applicationId": RAKUTEN_APP_ID, "format": "json", "keyword": api_keyword, "hits": 20}
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for h_item in data.get("hotels", []):
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        
                        # 距離計算の実行
                        d_text = None
                        raw_dist_for_sort = 999999
                        if target_info:
                            d_text = get_display_distance(
                                target_info['lat'], target_info['lng'], 
                                info.get('latitude'), info.get('longitude')
                            )
                            # ソート用に数値化
                            if d_text:
                                val = float(d_text.replace('km','').replace('m',''))
                                raw_dist_for_sort = val * 1000 if 'km' in d_text else val

                        j_price, j_url = get_jalan_info(info.get("hotelName", ""))
                        
                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": d_text,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url,
                            "raw_dist": raw_dist_for_sort
                        })
                    
                    # 目的地がある場合は「近い順」に並び替え
                    if target_info:
                        hotels.sort(key=lambda x: x['raw_dist'])
            except Exception as e:
                print(f"Error: {e}")
                
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
