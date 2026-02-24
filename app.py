from flask import Flask, render_template, request
import math

app = Flask(__name__)

# =============================
# 観光地
# =============================
destinations = {
    "美ら海水族館": {
        "name": "沖縄美ら海水族館",
        "lat": 26.69450809438831,
        "lng": 127.87802394473563
    }
}

# =============================
# 宿データ
# =============================
hotels = [
    {
        "name": "ロイヤルビューホテル美ら海",
        "lat": 26.695070212866984,
        "lng": 127.87955480115063,
        "url": "https://royalview-churaumi.com/",
        "image": "https://royalview-churaumi.com/wp-content/themes/churaumi/images/top/main.jpg"
    },
    {
        "name": "オリオンホテル モトブ リゾート＆スパ",
        "lat": 26.698680823691493,
        "lng": 127.87954414729788,
        "url": "https://www.okinawaresort-orion.com/",
        "image": "https://www.okinawaresort-orion.com/assets/img/top/main.jpg"
    },
    {
        "name": "ホテルマハイナ ウェルネスリゾートオキナワ",
        "lat": 26.683218735182386,
        "lng": 127.88197011075614,
        "url": "http://www.mahaina.co.jp/",
        "image": "https://www.mahaina.co.jp/images/top/main.jpg"
    },
    {
        "name": "美ら海ビレッジ（2号店 管理棟）",
        "lat": 26.687465673757558,
        "lng": 127.88601810300285,
        "url": "https://churaumi-village.com/",
        "image": "https://churaumi-village.com/img/top/main.jpg"
    },
    {
        "name": "カリーコンド美ら海",
        "lat": 26.682051810566435,
        "lng": 127.8872590010066,
        "url": "https://karry-condo.com/",
        "image": "https://karry-condo.com/images/top/main.jpg"
    }
]

# =============================
# 距離計算
# =============================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat/2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(d_lon/2)**2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 2)

# =============================
# ルート
# =============================
@app.route("/", methods=["GET", "POST"])
def index():

    results = []
    destination_name = ""

    if request.method == "POST":

        destination_name = request.form.get("destination", "").strip()

        if "美ら海" in destination_name:
            destination = destinations["美ら海水族館"]

            for hotel in hotels:
                hotel["distance"] = calculate_distance(
                    destination["lat"],
                    destination["lng"],
                    hotel["lat"],
                    hotel["lng"]
                )

            results = sorted(hotels, key=lambda x: x["distance"])

            return render_template(
                "result.html",
                results=results,
                destination_name=destination_name
            )

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)