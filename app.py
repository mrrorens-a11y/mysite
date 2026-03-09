import os
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz  # 名寄せ用

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY") # じゃらん用

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

def format_distance(m):
    """距離をわかりやすく変換"""
    if m is None: return ""
    m = float(m)
    return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if keyword:
            # --- 楽天APIへのリクエスト ---
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
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
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)

                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info = h["hotel"][0]["hotelBasicInfo"]
                            r_name = info.get("hotelName", "")
                            
                            # 距離の整形
                            dist_raw = info.get("searchDistance")
                            info["display_distance"] = format_distance(dist_raw) if dist_raw else ""

                            # URLのセット
                            info["target_url"] = info.get("affiliateUrl") or info.get("hotelInformationUrl")

                            # --- 【名寄せ】じゃらんAPIへの問い合わせ ---
                            info["jalan_price"] = "---"
                            info["jalan_url"] = ""

                            if RECRUIT_API_KEY:
                                j_params = {
                                    "key": RECRUIT_API_KEY,
                                    "keyword": r_name, # 楽天の宿名で検索
                                    "format": "json",
                                    "count": 3
                                }
                                try:
                                    j_res = requests.get(JALAN_API_URL, params=j_params, timeout=5)
                                    if j_res.status_code == 200:
                                        j_data = j_res.json()
                                        if "results" in j_data and "hotel" in j_data["results"]:
                                            for j_hotel in j_data["results"]["hotel"]:
                                                # 名前の類似度をチェック
                                                score = fuzz.token_sort_ratio(r_name, j_hotel["hotelName"])
                                                if score > 80: # 80%以上一致なら同一とみなす
                                                    price = j_hotel.get("sampleRateFrom")
                                                    info["jalan_price"] = f"¥{price}" if price else "---"
                                                    info["jalan_url"] = j_hotel.get("urls", {}).get("pc")
                                                    break
                                except Exception as e:
                                    print(f"JALAN ERROR for {r_name}: {e}")

                            hotels.append(info)
                else:
                    print(f"RAKUTEN API ERROR: {res.status_code}")

            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
