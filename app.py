import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# staticフォルダ（画像用）がなければ自動作成
if not os.path.exists('static'):
    os.makedirs('static')

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            headers = {
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
                            
                            # ======= 【ログ出力：ここを復活させました】 =======
                            print(f"HOTEL: {info.get('hotelName')}")
                            print(f"URL: {info.get('affiliateUrl') or info.get('hotelInformationUrl')}")
                            # ===============================================

                            # 画面表示用のURLをセット（収益化のための大事な部分）
                            info["target_url"] = info.get("affiliateUrl") or info.get("hotelInformationUrl")
                            hotels.append(info)
                else:
                    print(f"API ERROR: {res.status_code}")
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
