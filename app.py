import os
import asyncio
import httpx
import requests
import math # 距離計算用に追加
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数設定 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

# APIエンドポイント
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 📍 あなたが魂を込めて育てる目的地DB ---
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

# --- 📏 Haversine Formula (2点間の距離を正確に計算) ---
def calculate_haversine(lat1, lon1, lat2, lon2):
    try:
        if not all([lat1, lon1, lat2, lon2]): return None
        R = 6371  # 地球の半径 (km)
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * \
            math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_m = R * c * 1000
        # Hotels.com風表示 (1km未満はm、1km以上はkm)
        return f"{int(dist_m)}m" if dist_m < 1000 else f"{round(dist_m/1000, 2)}km"
    except:
        return ""

async def get_jalan_data(client, r_name):
    if not RECRUIT_API_KEY: return "---", ""
    j_params = {"key": RECRUIT_API_KEY, "keyword": r_name, "format": "json", "count": 5}
    try:
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                for j_hotel in j_data["results"]["hotel"]:
                    score = fuzz.token_sort_ratio(r_name, j_hotel["hotelName"])
                    if score > 75:
                        price = j_hotel.get("sampleRateFrom")
                        return (f"¥{price}" if price else "---"), j_hotel.get("urls", {}).get("pc")
    except: pass
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID, "format": "json",
                "keyword": keyword, "hits": 15
            }
            headers = {"referer": "https://mysite-l8l0.onrender.com/", "user-agent": "Mozilla/5.0"}

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        # 目的地DBから基準座標を取得
                        target = DESTINATIONS.get(keyword)

                        async def fetch_all_jalan():
                            async with httpx.AsyncClient() as client:
                                tasks = [get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                                return await asyncio.gather(*tasks)

                        jalan_results = asyncio.run(fetch_all_jalan())

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            j_price, j_url = jalan_results[idx]
                            
                            # --- 🚀 ここでHaversine距離を計算 ---
                            display_dist = ""
                            if target:
                                display_dist = calculate_haversine(
                                    target['lat'], target['lng'], 
                                    info.get('latitude'), info.get('longitude')
                                )
                            
                            item = {
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                # 自作計算が成功すればそれを使い、なければ空にする
                                "display_distance": display_dist,
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price,
                                "jalan_url": j_url
                            }
                            hotels.append(item)
            except Exception as e:
                print(f"Rakuten API Error: {e}")
    
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
