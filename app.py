import os
import requests
import urllib.parse
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()

print("=" * 60)
print(f"[INIT] RAKUTEN_APP_ID    : {'SET ('+str(len(RAKUTEN_APP_ID))+' chars)' if RAKUTEN_APP_ID else '*** MISSING ***'}")
print(f"[INIT] RAKUTEN_ACCESS_KEY: {'SET' if RAKUTEN_ACCESS_KEY else '*** MISSING ***'}")
print(f"[INIT] SITE_URL          : {SITE_URL}")
print("=" * 60)

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"


@app.route("/", methods=["GET", "POST"])
def index():
    hotels    = []
    keyword   = ""
    error_msg = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY:
            error_msg = "RAKUTEN_APP_ID または RAKUTEN_ACCESS_KEY が未設定です。"
            return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)

        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey":     RAKUTEN_ACCESS_KEY,
                "format":        "json",
                "keyword":       keyword,
                "hits":          10,
            }
            if RAKUTEN_AFFILIATE_ID:
                params["affiliateId"] = RAKUTEN_AFFILIATE_ID

            headers = {
                "Authorization": f"Bearer {RAKUTEN_ACCESS_KEY}",
                "Referer":       SITE_URL,
                "Origin":        SITE_URL,
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                print(f"[API] Status: {res.status_code}")

                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info = h["hotel"][0]["hotelBasicInfo"]
                            name = info.get("hotelName", "")
                            enc  = urllib.parse.quote(name)
                            hotels.append({
                                "hotelName":      name,
                                "hotelImageUrl":  info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "target_url":     info.get("affiliateUrl") or info.get("hotelInformationUrl", ""),
                                "jalan_url":      f"https://www.jalan.net/yad/?srt=1&kw={enc}",
                                "yahoo_url":      f"https://travel.yahoo.co.jp/search/?kw={enc}&type=hotel",
                                "booking_url":    f"https://www.booking.com/searchresults.ja.html?ss={enc}&lang=ja",
                            })
                    else:
                        error_msg = "該当する宿が見つかりませんでした。"
                else:
                    error_msg = f"楽天APIエラー ({res.status_code}): {res.text[:200]}"
                    print(f"[API] Response: {res.text[:300]}")

            except Exception as e:
                print(f"[ERROR] {e}")
                error_msg = "通信エラーが発生しました。"

    return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
