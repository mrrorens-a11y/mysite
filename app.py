import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Render環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

def get_jalan_price(hotel_name):
    """宿名でじゃらんを検索し、最安値とURLを返す"""
    params = {
        "key": RECRUIT_API_KEY,
        "keyword": hotel_name,
        "format": "json",
        "count": 1
    }
    try:
        res = requests.get(JALAN_API_URL, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            hotels = data.get('results', {}).get('hotel', [])
            if hotels:
                h = hotels[0]
                # じゃらんの価格（サンプル。APIにより取得項目は調整が必要な場合があります）
                return {
                    "price": h.get("sampleRateFrom", "---"),
                    "url": h.get("urls", {}).get("pc")
                }
    except:
        pass
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 10 # 比較処理を速くするため一旦10件
            }
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent": "Mozilla/5.0"
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for h in data.get("hotels", []):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        
                        # じゃらんの情報を取得
                        jalan_info = get_jalan_price(info["hotelName"])
                        
                        hotel_data = {
                            "name": info["hotelName"],
                            "img": info["hotelImageUrl"],
                            "address": f"{info['address1']}{info['address2']}",
                            "rakuten_price": info.get("hotelMinCharge", "---"),
                            "rakuten_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": jalan_info["price"] if jalan_info else "---",
                            "jalan_url": jalan_info["url"] if jalan_info else None
                        }
                        hotels.append(hotel_data)
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
