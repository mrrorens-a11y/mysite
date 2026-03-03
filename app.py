import os
import math
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")

if not RAKUTEN_APP_ID:
    raise ValueError("RAKUTEN_APP_ID is not set in environment variables")


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

    if not keyword:
        return jsonify({"error": "keyword required"}), 400

    # 🔥 まずキーワード検索
    keyword_url = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"
    keyword_params = {
        "format": "json",
        "keyword": keyword,
        "applicationId": RAKUTEN_APP_ID
    }

    keyword_res = requests.get(keyword_url, params=keyword_params)
    keyword_data = keyword_res.json()

    if "hotels" not in keyword_data:
        return jsonify({"hotels": []})

    center = keyword_data["hotels"][0]["hotel"][0]["hotelBasicInfo"]

    center_lat = center.get("latitude")
    center_lon = center.get("longitude")

    if not center_lat or not center_lon:
        return jsonify({"hotels": []})

    # 🔥 周辺検索
    simple_url = "https://app.rakuten.co.jp/services/api/Travel/SimpleHotelSearch/20170426"
    simple_params = {
        "format": "json",
        "latitude": center_lat,
        "longitude": center_lon,
        "searchRadius": 3,
        "applicationId": RAKUTEN_APP_ID
    }

    simple_res = requests.get(simple_url, params=simple_params)
    simple_data = simple_res.json()

    if "hotels" not in simple_data:
        return jsonify({"hotels": []})

    results = []

    for h in simple_data["hotels"]:
        info = h["hotel"][0]["hotelBasicInfo"]

        lat = info.get("latitude")
        lon = info.get("longitude")

        if not lat or not lon:
            continue

        distance = get_distance(
            float(center_lat),
            float(center_lon),
            float(lat),
            float(lon)
        )

        results.append({
            "name": info.get("hotelName"),
            "price": info.get("hotelMinCharge"),
            "url": info.get("hotelInformationUrl"),
            "distance": round(distance, 2)
        })

    results.sort(key=lambda x: x["distance"])

    return jsonify({"hotels": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
