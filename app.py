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

# -----------------------------
# 観光地DB
# -----------------------------

DESTINATIONS = {
    "美ら海水族館": (26.6947, 127.8789),
    "国際通り": (26.2155, 127.6809),
    "アメリカンビレッジ": (26.3167, 127.7560),
    "万座毛": (26.5046, 127.8526),
}

# -----------------------------
# 距離フォーマット
# -----------------------------

def format_distance(m):
    if m is None or m == "":
        return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000,1)}km"
    except:
        return ""

# -----------------------------
# Haversine距離
# -----------------------------

def haversine(lat1, lon1, lat2, lon2):

    R = 6371000

    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))

    dphi = math.radians(float(lat2)-float(lat1))
    dlambda = math.radians(float(lon2)-float(lon1))

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2

    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R*c

# -----------------------------
# 徒歩時間
# -----------------------------

def walking_time(distance):

    minutes = distance / 80

    return f"{round(minutes)}分"

# -----------------------------
# じゃらん取得
# -----------------------------

async def get_jalan_data(client, r_name):

    if not RECRUIT_API_KEY:
        return "---",""

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
                        url = j_hotel.get("urls",{}).get("pc")

                        return (f"¥{price}" if price else "---"), url

    except Exception as e:

        print(f"Async Jalan Error: {e}")

    return "---",""

# -----------------------------
# メイン
# -----------------------------

@app.route("/", methods=["GET","POST"])

def index():

    hotels = []
    keyword = ""

    if request.method == "POST":

        keyword = request.form.get("keyword","").strip()

        if keyword:

            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format":"json",
                "keyword": keyword,
                "hits":15
            }

            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent":"Mozilla/5.0"
            }

            try:

                res = requests.get(RAKUTEN_API_URL,params=params,headers=headers,timeout=10)

                if res.status_code == 200:

                    data = res.json()

                    if "hotels" in data:

                        async def fetch_all_jalan():

                            async with httpx.AsyncClient() as client:

                                tasks = [
                                    get_jalan_data(client,h["hotel"][0]["hotelBasicInfo"].get("hotelName",""))
                                    for h in data["hotels"]
                                ]

                                return await asyncio.gather(*tasks)

                        jalan_results = asyncio.run(fetch_all_jalan())

                        for idx,h in enumerate(data["hotels"]):

                            info = h["hotel"][0]["hotelBasicInfo"]

                            lat = info.get("latitude")
                            lng = info.get("longitude")

                            dist=""
                            walk=""

                            if keyword in DESTINATIONS and lat and lng:

                                dest_lat,dest_lng = DESTINATIONS[keyword]

                                distance_m = haversine(lat,lng,dest_lat,dest_lng)

                                dist = format_distance(distance_m)

                                walk = walking_time(distance_m)

                            j_price,j_url = jalan_results[idx]

                            item = {

                                "hotelName": info.get("hotelName"),

                                "hotelImageUrl": info.get("hotelImageUrl"),

                                "address1": info.get("address1",""),

                                "address2": info.get("address2",""),

                                "hotelMinCharge": info.get("hotelMinCharge"),

                                "display_distance": dist,

                                "walk_time": walk,

                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),

                                "jalan_price": j_price,

                                "jalan_url": j_url
                            }

                            hotels.append(item)

            except Exception as e:

                print(f"Rakuten API Error: {e}")

    return render_template("index.html",hotels=hotels,keyword=keyword)

if __name__ == "__main__":

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)
