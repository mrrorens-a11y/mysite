import os
import math
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")

if not RAKUTEN_APP_ID:
    raise ValueError("RAKUTEN_APP_ID is not set")

# 🔥 観光地データベース（あとから追加可能）
DESTINATIONS = {
    "沖縄美ら海水族館": {"lat": 26.69451309310509, "lng": 127.87801499848918},
    "ウッパマビーチ": {"lat": 26.692852017176595, "lng": 127.99204980657072},
}

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)

    a = (
        math.sin(dLat/2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dLon/2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():
    keyword = request.args.get("keyword")

    if keyword not in DESTINATIONS:
        return jsonify({"error": "目的地が見つかりません"})

    center_lat = DESTINATIONS[keyword]["lat"]
    center_lon = DESTINATIONS[keyword]["lng"]

    url = "https://app.rakuten.co.jp/services/api/Travel/SimpleHotelSearch/20170426"

    params = {
        "format": "json",
        "latitude": center_lat,
        "longitude": center_lon,
        "searchRadius": 5,
        "hits": 30,
        "applicationId": RAKUTEN_APP_ID,
        "affiliateId": RAKUTEN_AFFILIATE_ID
    }

    res = requests.get(url, params=params)
    data = res.json()

    if "hotels" not in data:
        return jsonify({"hotels": []})

    results = []

    for h in data["hotels"]:
        info = h["hotel"][0]["hotelBasicInfo"]

        lat = float(info["latitude"])
        lon = float(info["longitude"])

        distance = get_distance(center_lat, center_lon, lat, lon)

        results.append({
            "name": info["hotelName"],
            "price": info.get("hotelMinCharge"),
            "url": info["hotelInformationUrl"],
            "distance": round(distance, 2)
        })

    results.sort(key=lambda x: x["distance"])

    return jsonify({"hotels": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
