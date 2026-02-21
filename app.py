from flask import Flask, render_template, request
import requests
import math

app = Flask(__name__)


def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json", "limit": 1}
    headers = {"User-Agent": "hotel-search-app"}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        data = res.json()
    except:
        return None

    if not data:
        return None

    return float(data[0]["lat"]), float(data[0]["lon"])


def get_nearby_hotels(lat, lon):
    query = f"""
    [out:json];
    (
      node["tourism"="hotel"](around:5000,{lat},{lon});
      node["tourism"="guest_house"](around:5000,{lat},{lon});
      node["tourism"="hostel"](around:5000,{lat},{lon});
      node["tourism"="resort"](around:5000,{lat},{lon});
    );
    out;
    """

    url = "https://overpass-api.de/api/interpreter"

    try:
        res = requests.post(url, data=query, timeout=20)
        data = res.json()
    except:
        return []

    hotels = []

    for el in data.get("elements", []):
        name = el.get("tags", {}).get("name", "名称不明の宿")
        h_lat = el.get("lat")
        h_lon = el.get("lon")

        if h_lat is None or h_lon is None:
            continue

        dist = round(distance_km(lat, lon, h_lat, h_lon), 2)

        hotels.append({
            "name": name,
            "distance": dist,
            "price": "—",
            "url": f"https://www.google.com/maps/search/?api=1&query={h_lat},{h_lon}"
        })

    hotels.sort(key=lambda x: x["distance"])
    return hotels


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    place = request.form.get("place")

    if not place:
        return "地名を入力してください"

    coords = geocode(place)

    if not coords:
        return "地名が見つかりませんでした（通信エラー or 未登録地名）"

    lat, lon = coords
    hotels = get_nearby_hotels(lat, lon)

    if not hotels:
        return "5km以内に宿が見つかりません（API混雑の可能性あり）"

    return render_template("result.html", place=place, hotels=hotels)


if __name__ == "__main__":
    app.run(debug=True)

