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

# --- 📍 目的地座標DB (指定の座標を反映) ---
DESTINATIONS = {
    "恩納村": {"lat": 26.5050, "lng": 127.8767},
    "美ら海水族館": {"lat": 26.694542346577375, "lng": 127.8779368039277},
    "那覇空港": {"lat": 26.2064, "lng": 127.6465},
    "国際通り": {"lat": 26.2155, "lng": 127.6853},
    "アメリカンビレッジ": {"lat": 26.3164, "lng": 127.7576},
}

# --- 📏 Haversine距離計算 ---
def get_display_distance(lat1, lon1, lat2, lon2):
    try:
        if not all([lat1, lon1, lat2, lon2]): return None
        R = 6371 
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * \
            math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_m = R * c * 1000
        
        # 1000m未満は「m」、それ以上は「km」表記
        if dist_m < 1000:
            return f"{int(dist_m)}m"
        else:
            return f"{round(dist_m/1000, 2)}km"
    except:
        return None

# --- じゃらん料金取得 (同期) ---
def get_jalan_info(hotel_name):
    if not RECRUIT_API_KEY: return "---", None
    params = {"key": RECRUIT_API_KEY, "keyword": hotel_name, "format": "json", "count": 1}
    try:
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
            params = {"applicationId": RAKUTEN_APP_ID, "format": "json", "keyword": keyword, "hits": 20}
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    target = DESTINATIONS.get(keyword)
                    
                    for h_item in data.get("hotels", []):
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        h_name = info.get("hotelName", "")
                        
                        # 距離計算
                        d_text = None
                        if target:
                            d_text = get_display_distance(
                                target['lat'], target['lng'], 
                                info.get('latitude'), info.get('longitude')
                            )
                        
                        j_price, j_url = get_jalan_info(h_name)
                        
                        hotels.append({
                            "hotelName": h_name,
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": d_text,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        })
                    
                    # 距離が近い順に並び替え（距離データがある場合のみ）
                    if target:
                        hotels.sort(key=lambda x: x['display_distance'] if x['display_distance'] else "999km")
            except Exception as e:
                print(f"Error: {e}")
                
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
