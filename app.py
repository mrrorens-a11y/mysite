import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Render環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")

# 楽天トラベルAPI
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if not RAKUTEN_APP_ID:
            print("DEBUG: RAKUTEN_APP_ID が設定されていません")

        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }

            # affiliateIdがある時だけ追加
            if RAKUTEN_AFFILIATE_ID:
                params["affiliateId"] = RAKUTEN_AFFILIATE_ID

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }

            try:
                res = requests.get(
                    RAKUTEN_API_URL,
                    params=params,
                    headers=headers,
                    timeout=10
                )

                print("DEBUG URL:", res.url)
                print("DEBUG STATUS:", res.status_code)

                if res.status_code == 200:
                    data = res.json()

                    if "hotels" in data:
                        for h in data["hotels"]:
                            info = h["hotel"][0]["hotelBasicInfo"]

                            # アフィリエイトURL
                            info["target_url"] = (
                                info.get("affiliateUrl")
                                or info.get("hotelInformationUrl")
                            )

                            hotels.append(info)

                else:
                    print("DEBUG API ERROR:", res.text)

            except Exception as e:
                print("DEBUG SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
