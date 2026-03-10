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

# --- 📍 目的地DB ---
DESTINATIONS = {
    "恩納村": {"lat": 26.5050, "lng": 127.8767},
    "美ら海水族館": {"lat": 26.6943, "lng": 127.8781},
    "那覇空港": {"lat": 26.2064, "lng": 127.6465},
    "国際通り": {"lat": 26.2155, "lng": 127.6853},
    "首里城": {"lat": 26.2170, "lng": 127.7195},
    "アメリカンビレッジ": {"lat": 26.3164, "lng": 127.7576},
    "万座毛": {"lat": 26.5050, "lng": 127.8500},
    "古宇利島": {"lat": 26.7020, "lng": 128.0200},
    "瀬長島ウミカジテラス": {"lat": 26.1748, "lng": 127.6461},
    "那覇駅": {"lat": 26.2125, "lng": 127.6792},
}

# --- 📏 距離計算 ---
def calculate_haversine(lat1, lon1, lat2, lon2):
    try:
        if not all([lat1, lon1, lat2, lon2]): return ""
        R = 6371
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * \
            math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_m = R * c * 1000
        return f"{int(dist_m)}m" if dist_m < 1000 else f"{round(dist_m/1000, 2)}km"
    except: return ""

# --- じゃらん料金取得 (同期版) ---
def get_jalan_price(r_name):
    if not RECRUIT_API_KEY: return "---", ""
    params = {"key": RECRUIT_API_KEY, "keyword": r_name, "format": "json", "count": 1}
    try:
        res = requests.get(JALAN_API_URL, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and "hotel" in data["results"]:
                h = data["results"]["hotel"][0]
                if fuzz.token_sort_ratio(r_name, h["hotelName"]) > 75:
                    return f"¥{h.get('sampleRateFrom', '---')}", h.get("urls", {}).get("pc")
    except: pass
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {"applicationId": RAKUTEN_APP_ID, "format": "json", "keyword": keyword, "hits": 15}
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    target = DESTINATIONS.get(keyword)
                    
                    for h in data.get("hotels", []):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        j_price, j_url = get_jalan_price(info.get("hotelName", ""))
                        
                        dist = ""
                        if target:
                            dist = calculate_haversine(target['lat'], target['lng'], info.get('latitude'), info.get('longitude'))

                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": dist,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        })
            except Exception as e:
                print(f"Error: {e}")
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
