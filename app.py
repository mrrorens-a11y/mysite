import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

@app.route("/", methods=["GET","POST"])
def index():

    rakuten_hotels = []
    jalan_hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword")

        # 楽天API
        rakuten_params = {
            "applicationId": RAKUTEN_APP_ID,
            "affiliateId": RAKUTEN_AFFILIATE_ID,
            "keyword": keyword,
            "hits": 10,
            "format": "json"
        }

        try:
            r = requests.get(RAKUTEN_URL, params=rakuten_params, timeout=10)
            data = r.json()

            if "hotels" in data:
                for h in data["hotels"]:
                    info = h["hotel"][0]["hotelBasicInfo"]
                    info["target_url"] = info.get("affiliateUrl") or info.get("hotelInformationUrl")
                    rakuten_hotels.append(info)

        except Exception as e:
            print(e)


        # じゃらんAPI
        jalan_params = {
            "key": RECRUIT_API_KEY,
            "keyword": keyword,
            "count": 10,
            "format": "json"
        }

        try:
            j = requests.get(JALAN_URL, params=jalan_params, timeout=10)
            data = j.json()

            hotels = data.get("results",{}).get("hotel",[])

            if isinstance(hotels, dict):
                hotels = [hotels]

            for h in hotels:
                jalan_hotels.append({
                    "name": h["hotel_name"],
                    "image": h["hotel_image_sample_large"],
                    "price": h.get("sample_rate_from","---"),
                    "url": h["plan_list_url"]
                })

        except Exception as e:
            print(e)

    return render_template(
        "index.html",
        keyword=keyword,
        rakuten_hotels=rakuten_hotels,
        jalan_hotels=jalan_hotels
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
