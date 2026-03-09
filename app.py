import os
import asyncio
import httpx
import math
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 📍 沖縄・有名スポット座標DB（ここを増やすほどサイトが賢くなります） ---
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

# --- 📏 Hotels.com風：距離の表示形式（1km未満はm、1km以上は小数点2桁km） ---
def format_distance(m):
    if m is None: return None
    m = float(m)
    if m < 1000:
        return f"{int(m)}m"
    else:
        # Hotels.comの「0.24km」のような精密な表示
        return f"{round(m/1000, 2)}km"

# --- 2点間の直線距離を計算（ヒュベニの公式） ---
def calculate_distance(lat1, lon1, lat2, lon2):
    if not all([lat1, lon1, lat2, lon2]): return None
    # 緯度経度をラジアンに変換
    rad_lat1, rad_lon1 = math.radians(lat1), math.radians(lon1)
    rad_lat2, rad_lon2 = math.radians(lat2), math.radians(lon2)
    
    # 地球の半径 (m)
    R = 6371000
    dlat = rad_lat2 - rad_lat1
    dlon = rad_lon2 - rad_lon1
    a = math.sin(dlat/2)**2 + math.cos(rad_lat1) * math.cos(rad_lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- じゃらんAPIを非同期で叩く関数 ---
async def get_jalan_data(client, r_name):
    if not RECRUIT_API_KEY: return "---", ""
    j_params = {"key": RECRUIT_API_KEY, "keyword": r_name, "format": "json", "count": 5}
    try:
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                for j_hotel in j_data["results"]["hotel"]:
                    if fuzz.token_sort_ratio(r_name, j_hotel["hotelName"]) > 75:
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

            import requests
            res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                if "hotels" in data:
                    # 自作DBにキーワードがあるかチェック（なければNone）
                    base_coords = DESTINATIONS.get(keyword)

                    async def fetch_all_jalan():
                        async with httpx.AsyncClient() as client:
                            job_list = [get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                            return await asyncio.gather(*job_list)

                    jalan_results = asyncio.run(fetch_all_jalan())

                    for idx, h in enumerate(data["hotels"]):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        j_price, j_url = jalan_results[idx]
                        
                        # 距離計算（DBにキーワードがある場合のみ）
                        display_dist = None
                        if base_coords:
                            h_lat = float(info.get("latitude") or 0)
                            h_lng = float(info.get("longitude") or 0)
                            raw_dist = calculate_distance(base_coords["lat"], base_coords["lng"], h_lat, h_lng)
                            display_dist = format_distance(raw_dist)

                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "address1": info.get("address1", ""),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": display_dist,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        })
    
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
