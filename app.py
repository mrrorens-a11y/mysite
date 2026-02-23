from flask import Flask, render_template
import math

app = Flask(__name__)

# =============================
# 観光地（固定）
# =============================
destination = {
    "name": "沖縄美ら海水族館",
    "lat": 26.69450809438831,
    "lng": 127.87802394473563
}

# =============================
# 宿データ（固定）
# =============================
hotels = [
    {
        "name": "ロイヤルビューホテル美ら海",
        "lat": 26.695070212866984,
        "lng": 127.87955480115063,
        "url": "https://royalview-churaumi.com/"
    },
    {
        "name": "オリオンホテル モトブ リゾート＆スパ",
        "lat": 26.698680823691493,
        "lng": 127.87954414729788,
        "url": "https://www.okinawaresort-orion.com/"
    },
    {
        "name": "ホテルマハイナ ウェルネスリゾートオキナワ",
        "lat": 26.683218735182386,
        "lng": 127.88197011075614,
        "url": "http://www.mahaina.co.jp/"
    },
    {
        "name": "美ら海ビレッジ（2号店 管理棟）",
        "lat": 26.687465673757558,
        "lng": 127.88601810300285,
        "url": "https://churaumi-village.com/"
    },
    {
        "name": "カリーコンド美ら海",
        "lat": 26.682051810566435,
        "lng": 127.8872590010066,
        "url": "https://karry-condo.com/"
    }
]

# =============================
# 距離計算（km）
# =============================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(d_lon/2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

@app.route("/")
def home():

    for hotel in hotels:
        distance = calculate_distance(
            destination["lat"],
            destination["lng"],
            hotel["lat"],
            hotel["lng"]
        )
        hotel["distance"] = distance

    sorted_hotels = sorted(hotels, key=lambda x: x["distance"])

    return render_template(
        "result.html",
        destination=destination,
        hotels=sorted_hotels
    )

if __name__ == "__main__":
    app.run(debug=True)