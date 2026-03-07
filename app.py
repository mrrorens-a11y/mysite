import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

print("===== APP STARTING =====")

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")

print("APP_ID:", RAKUTEN_APP_ID)
print("AFFILIATE_ID:", RAKUTEN_AFFILIATE_ID)

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"


@app.route("/", methods=["GET", "POST"])
def index():

    print("===== INDEX PAGE ACCESSED =====")

    hotels = []
    keyword = ""

    if request.method == "POST":

        keyword = request.form.get("keyword", "").strip()

        print("SEARCH KEYWORD:", keyword)

        if keyword:

            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }

            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "origin": "https://mysite-l8l0.onrender.com",
                "user-agent": "Mozilla/5.0",
                "accept": "application/json"
            }

            try:

                print("===== CALLING RAKUTEN API =====")

                res = requests.get(
                    RAKUTEN_API_URL,
                    params=params,
                    headers=headers,
                    timeout=10
                )

                print("API STATUS:", res.status_code)

                data = res.json()

                print("API RESPONSE KEYS:", data.keys())

                if "hotels" in data:

                    for h in data["hotels"]:

                        info = h["hotel"][0]["hotelBasicInfo"]

                        print("HOTEL:", info.get("hotelName"))
                        print("affiliateUrl:", info.get("affiliateUrl"))
                        print("normalUrl:", info.get("hotelInformationUrl"))

                        info["target_url"] = (
                            info.get("affiliateUrl")
                            or info.get("hotelInformationUrl")
                        )

                        hotels.append(info)

            except Exception as e:

                print("ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    print("STARTING SERVER PORT:", port)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
