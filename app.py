import os
import asyncio
import httpx
import requests
import math
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

# API
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 📍 目的地DB ---
DESTINATIONS = {
    "恩納村": {"lat": 26.5050, "lng": 127.8767, "search_word": "恩納村"},
    "美ら海水族館": {"lat": 26.6943, "lng": 127.8781, "search_word": "本部町"},
    "那覇空港": {"lat": 26.2064, "lng": 127.6465, "search_word": "那覇"},
    "国際通り": {"lat": 26.2155, "lng": 127.6853, "search_word": "那覇"},
    "首里城": {"lat": 26.2170, "lng": 127.7195, "search_word": "那覇"},
    "アメリカンビレッジ": {"lat": 26.3164, "lng": 127.7576, "search_word": "北谷"},
    "万座毛": {"lat": 26.5050, "lng": 127.8500, "search_word": "恩納村"},
    "古宇利島": {"lat": 26.7020, "lng": 128.0200, "search_word": "今帰仁村"},
    "瀬長島ウミカジテラス": {"lat": 26.1748, "lng": 127.6461, "search_word": "豊見城"},
    "那覇駅": {"lat": 26.2125, "lng": 127.6792, "search_word": "那覇"}
}

# --- 距離計算 ---
def haversine(lat1, lon1, lat2, lon2):

    R = 6371

    lat1, lon1, lat2, lon2 = map(
        math.radians,
        [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2

    c = 2 * math.asin(math.sqrt(a))

    return R * c


def format_distance(m):

    if not m:
        return ""

    if m < 1000:
        return f"{int(m)}m"

    return f"{round(m/1000,1)}km"


# --- じゃらん料金取得 ---
async def get_jalan_data(client, r_name):

    if not RECRUIT_API_KEY:
        return "---", ""

    params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 5
    }

    try:

        res = await client.get(JALAN_API_URL, params=params, timeout=5)

        if res.status_code == 200:

            data = res.json()

            if "results" in data and "hotel" in data["results"]:

                for j_hotel in data["results"]["hotel"]:

                    score = fuzz.token_sort_ratio(
                        r_name,
                        j_hotel["hotelName"]
                    )

                    if score > 75:

                        price = j_hotel.get("sampleRateFrom")
                        url = j_hotel.get("urls", {}).get("pc")

                        return f"¥{price}" if price else "---", url

    except Exception as e:

        print("Jalan Error", e)

    return "---", ""


@app.route("/", methods=["GET", "POST"])
def index():

    hotels = []
    keyword = ""

    if request.method == "POST":

        keyword = request.form.get("keyword", "").strip()

        if keyword:

            # --- DESTINATION判定 ---
            if keyword in DESTINATIONS:

                dest = DESTINATIONS[keyword]

                dest_lat = dest["lat"]
                dest_lng = dest["lng"]

                rakuten_keyword = dest["search_word"]

            else:

                dest_lat = None
                dest_lng = None
                rakuten_keyword = keyword

            # --- 楽天検索 ---
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "keyword": rakuten_keyword,
                "format": "json",
                "hits": 15
            }

            headers = {
                "user-agent": "Mozilla/5.0"
            }

            res = requests.get(
                RAKUTEN_API_URL,
                params=params,
                headers=headers,
                timeout=10
            )

            if res.status_code == 200:

                data = res.json()

                if "hotels" in data:

                    async def fetch_all_jalan():

                        async with httpx.AsyncClient() as client:

                            tasks = [
                                get_jalan_data(
                                    client,
                                    h["hotel"][0]["hotelBasicInfo"]["hotelName"]
                                )
                                for h in data["hotels"]
                            ]

                            return await asyncio.gather(*tasks)

                    jalan_results = asyncio.run(fetch_all_jalan())

                    for idx, h in enumerate(data["hotels"]):

                        info = h["hotel"][0]["hotelBasicInfo"]

                        hotel_lat = info.get("latitude")
                        hotel_lng = info.get("longitude")

                        distance = None

                        if dest_lat and hotel_lat:

                            distance_km = haversine(
                                dest_lat,
                                dest_lng,
                                float(hotel_lat),
                                float(hotel_lng)
                            )

                            distance = distance_km * 1000

                        j_price, j_url = jalan_results[idx]

                        hotels.append({

                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "address1": info.get("address1", ""),
                            "address2": info.get("address2", ""),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": format_distance(distance),
                            "distance_raw": distance if distance else 999999,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        })

                    # --- 距離順 ---
                    hotels.sort(key=lambda x: x["distance_raw"])

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
