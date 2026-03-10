import os
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# 環境変数（RenderのDashboardで設定したもの）
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

# 楽天の新しいAPIエンドポイント
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"


def format_distance(m):
    """距離を500mや1.2kmのように表示"""
    if m is None:
        return ""
    m = float(m)
    return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"


@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if keyword:
            # 1. 楽天APIリクエスト
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }

            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "origin": "https://mysite-l8l0.onrender.com",
                "user-agent": "Mozilla/5.0",
                "accept": "application/json"
            }

            try:
                res = requests.get(
                    RAKUTEN_API_URL,
                    params=params,
                    headers=headers,
                    timeout=10
                )

                print(f"DEBUG: Rakuten Status: {res.status_code}")

                if res.status_code == 200:
                    data = res.json()

                    if "hotels" in data:
                        for h in data["hotels"]:

                            info = h["hotel"][0]["hotelBasicInfo"]
                            r_name = info.get("hotelName", "")

                            item = {
                                "hotelName": r_name,
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(
                                    info.get("searchDistance")
                                ),
                                "target_url": info.get("affiliateUrl")
                                or info.get("hotelInformationUrl"),
                                "jalan_price": "---",
                                "jalan_url": ""
                            }

                            # 2. じゃらん名寄せ検索
                            if RECRUIT_API_KEY:

                                j_params = {
                                    "key": RECRUIT_API_KEY,
                                    "keyword": r_name,
                                    "format": "json",
                                    "count": 5
                                }

                                try:
                                    j_res = requests.get(
                                        JALAN_API_URL,
                                        params=j_params,
                                        timeout=5
                                    )

                                    if j_res.status_code == 200:
                                        j_data = j_res.json()

                                        if (
                                            "results" in j_data
                                            and "hotel" in j_data["results"]
                                        ):
                                            for j_hotel in j_data["results"]["hotel"]:

                                                score = fuzz.token_sort_ratio(
                                                    r_name,
                                                    j_hotel["hotelName"]
                                                )

                                                if score > 75:
                                                    price = j_hotel.get("sampleRateFrom")

                                                    item["jalan_price"] = (
                                                        f"¥{price}"
                                                        if price
                                                        else "---"
                                                    )

                                                    item["jalan_url"] = (
                                                        j_hotel.get("urls", {})
                                                        .get("pc")
                                                    )

                                                    break

                                except Exception as e:
                                    print(f"Jalan sub-search error: {e}")

                            hotels.append(item)

                else:
                    print(
                        f"RAKUTEN API ERROR: {res.status_code}, Body: {res.text}"
                    )

            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template(
        "index.html",
        hotels=hotels,
        keyword=keyword
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)))
