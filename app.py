import os
import math
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")

RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/SimpleHotelSearch/20170426"


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


# --- 📏 Haversine距離計算 ---
def haversine(lat1, lon1, lat2, lon2):

    R = 6371000

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def format_distance(m):

    if m < 1000:
        return f"{int(m)}m"

    return f"{round(m/1000,1)}km"


@app.route("/", methods=["GET","POST"])
def index():

    hotels = []
    keyword = ""

    if request.method == "POST":

        keyword = request.form.get("keyword","").strip()

        if keyword in DESTINATIONS:

            lat = DESTINATIONS[keyword]["lat"]
            lng = DESTINATIONS[keyword]["lng"]

            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "latitude": lat,
                "longitude": lng,
                "searchRadius": 3,
                "hits": 20,
                "format": "json"
            }

            res = requests.get(RAKUTEN_API_URL, params=params)

            if res.status_code == 200:

                data = res.json()

                if "hotels" in data:

                    for h in data["hotels"]:

                        info = h["hotel"][0]["hotelBasicInfo"]

                        h_lat = float(info.get("latitude"))
                        h_lng = float(info.get("longitude"))

                        distance = haversine(lat, lng, h_lat, h_lng)

                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "address": info.get("address1","") + info.get("address2",""),
                            "price": info.get("hotelMinCharge"),
                            "distance": format_distance(distance),
                            "url": info.get("affiliateUrl") or info.get("hotelInformationUrl")
                        })

                    hotels = sorted(hotels, key=lambda x: float(x["distance"].replace("km","000").replace("m","")))

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0", port=port)
