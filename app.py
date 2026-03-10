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

# --- 📏 距離計算 ---
def get_display_distance(lat1, lon1, lat2, lon2):
    try:
        if not all([lat1, lon1, lat2, lon2]): return None
        R = 6371 
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * \
            math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        m = R * c * 1000
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 2)}km"
    except: return None

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
                if fuzz.token_sort_ratio(hotel_name, h["hotelName"]) > 70:
                    return f"¥{h.get('sampleRateFrom')}", h.get("urls", {}).get("pc")
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
            api_keyword = target_info["search_word"] if target_info else keyword

            params = {"applicationId": RAKUTEN_APP_ID, "format": "json", "keyword": api_keyword, "hits": 20}
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for h_item in data.get("hotels", []):
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        h_name = info.get("hotelName", "")
                        
                        dist = None
                        if target_info:
                            dist = get_display_distance(target_info['lat'], target_info['lng'], info.get('latitude'), info.get('longitude'))
                        
                        j_price, j_url = get_jalan_info(h_name)
                        
                        # 表示用の距離（m/km）を数値に変換してソート用に保持
                        raw_dist_val = 999999
                        if dist:
                            clean_dist = dist.replace('km','').replace('m','')
                            raw_dist_val = float(clean_dist)
                            if 'km' in dist:
                                raw_dist_val *= 1000

                        hotels.append({
                            "hotelName": h_name,
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": dist,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url,
                            "raw_dist": raw_dist_val
                        })
                    
                    if target_info:
                        hotels.sort(key=lambda x: x['raw_dist'])
            except Exception as e:
                print(f"Error: {e}")
                
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
