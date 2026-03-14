import os
import requests
import urllib.parse
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
RECRUIT_API_KEY      = os.environ.get("RECRUIT_API_KEY", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL   = "https://webservice.recruit.co.jp/jalan/hotel/v1/"


def format_distance(m):
    if m is None: return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"
    except: return ""


# じゃらん宿ページ取得
def get_jalan_url(hotel_name):

    if not RECRUIT_API_KEY:
        return None

    params = {
        "key": RECRUIT_API_KEY,
        "keyword": hotel_name,
        "format": "json",
        "count": 3
    }

    try:
        r = requests.get(JALAN_API_URL, params=params, timeout=5)

        if r.status_code == 200:

            data = r.json()

            if "results" in data and "hotel" in data["results"]:

                # 一番最初のホテル
                hotel = data["results"]["hotel"][0]

                return hotel["hotel"][0]["hotelBasicInfo"]["hotelUrl"]

    except Exception as e:
        print("JALAN ERROR:", e)

    return None


@app.route("/", methods=["GET", "POST"])
def index():
    hotels  = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey":     RAKUTEN_ACCESS_KEY,
                "affiliateId":   RAKUTEN_AFFILIATE_ID,
                "format":        "json",
                "keyword":       keyword,
                "hits":          15
            }

            headers = {
                "referer":    SITE_URL + "/",
                "origin":     SITE_URL,
                "user-agent": "Mozilla/5.0",
                "accept":     "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                print(f"DEBUG: Rakuten Status: {res.status_code}")

                if res.status_code == 200:

                    data = res.json()

                    if "hotels" in data:

                        for h in data["hotels"]:

                            info = h["hotel"][0]["hotelBasicInfo"]

                            name = info.get("hotelName", "")
                            enc  = urllib.parse.quote(name)

                            # じゃらんAPI検索
                            jalan_url = get_jalan_url(name)

                            # fallback
                            if not jalan_url:
                                jalan_url = f"https://www.jalan.net/search/?keyword={enc}"

                            hotels.append({
                                "hotelName":        name,
                                "hotelImageUrl":    info.get("hotelImageUrl"),
                                "address1":         info.get("address1", ""),
                                "address2":         info.get("address2", ""),
                                "hotelMinCharge":   info.get("hotelMinCharge"),
                                "display_distance": format_distance(info.get("searchDistance")),

                                # 楽天
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),

                                # じゃらん
                                "jalan_url": jalan_url,

                                # Yahoo
                                "yahoo_url": f"https://travel.yahoo.co.jp/search/?stext={enc}",

                                # Booking
                                "booking_url": f"https://www.booking.com/searchresults.ja.html?ss={enc}&lang=ja",
                            })

                else:
                    print(f"RAKUTEN ERROR: {res.status_code}, Body: {res.text}")

            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
