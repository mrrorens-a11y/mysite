import os
import asyncio
import httpx
import requests
import math
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

# -------------------------
# テストDBホテル（2件）
# -------------------------
DB_HOTELS = [
    {
        "hotelName": "テストホテル美ら海",
        "lat": 26.6943,
        "lng": 127.8780,
        "price": 9000,
        "url": "https://travel.rakuten.co.jp/"
    },
    {
        "hotelName": "テストホテル本部",
        "lat": 26.6930,
        "lng": 127.8800,
        "price": 8000,
        "url": "https://travel.rakuten.co.jp/"
    }
]

DESTINATIONS = {
    "美ら海水族館": {"lat": 26.6943, "lng": 127.8781}
}

# -------------------------
# Haversine距離計算
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def format_distance(m):
    """
    距離を1000m未満は'm'、それ以上は'km'で分かりやすく表示
    """
    if m is None or m == "": return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"
    except ValueError:
        return ""


async def get_jalan_data(client, r_name):
    """
    じゃらんAPIを非同期で叩き、楽天のホテル名と照合して料金を返す
    """
    if not RECRUIT_API_KEY:
        return "---", ""
    
    j_params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 5
    }
    
    try:
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                for j_hotel in j_data["results"]["hotel"]:
                    score = fuzz.token_sort_ratio(r_name, j_hotel["hotelName"])
                    if score > 75:
                        price = j_hotel.get("sampleRateFrom")
                        url = j_hotel.get("urls", {}).get("pc")
                        return (f"¥{price}" if price else "---"), url
    except Exception as e:
        print(f"Async Jalan Error for {r_name}: {e}")
    
    return "---", ""


@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if keyword:
            # -----------------------
            # 楽天API検索
            # -----------------------
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }

            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent": "Mozilla/5.0"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)

                if res.status_code == 200:
                    data = res.json()

                    if "hotels" in data:

                        async def fetch_all_jalan():
                            async with httpx.AsyncClient() as client:
                                tasks = [
                                    get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) 
                                    for h in data["hotels"]
                                ]
                                return await asyncio.gather(*tasks)

                        jalan_results = asyncio.run(fetch_all_jalan())

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            j_price, j_url = jalan_results[idx]

                            item = {
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(info.get("searchDistance")),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price,
                                "jalan_url": j_url
                            }

                            hotels.append(item)

            except Exception as e:
                print(f"Rakuten API Error: {e}")

        # -----------------------
        # DBホテル表示
        # -----------------------
        if keyword in DESTINATIONS:

            dest_lat = DESTINATIONS[keyword]["lat"]
            dest_lng = DESTINATIONS[keyword]["lng"]

            for h in DB_HOTELS:

                distance_km = haversine(dest_lat, dest_lng, h["lat"], h["lng"])
                distance_m = distance_km * 1000

                item = {
                    "hotelName": h["hotelName"],
                    "hotelImageUrl": "https://picsum.photos/600/400",
                    "address1": "",
                    "address2": "",
                    "hotelMinCharge": h["price"],
                    "display_distance": format_distance(distance_m),
                    "target_url": h["url"],
                    "jalan_price": "---",
                    "jalan_url": ""
                }

                hotels.append(item)

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
