import os
import asyncio
import httpx
import requests
import urllib.parse
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数（アクセスキーはコード内では使わないので削除してOK）
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"

async def fetch_jalan_data(client, r_name):
    encoded_name = urllib.parse.quote(r_name)
    fallback_url = f"https://www.jalan.net/fwSearch.do?fw={encoded_name}"
    if not RECRUIT_API_KEY:
        return "---", fallback_url

    j_params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 1
    }
    try:
        res = await client.get("https://webservice.recruit.co.jp/jalan/hotel/v1/", params=j_params, timeout=3.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                j_hotel = j_data["results"]["hotel"][0]
                price = j_hotel.get("sampleRateFrom")
                url = j_hotel.get("urls", {}).get("pc")
                return (f"¥{price}" if price else "---"), (url or fallback_url)
    except:
        pass
    return "---", fallback_url

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 🚨 パラメータを極限までシンプルにしました
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 10
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        async def get_all_prices():
                            async with httpx.AsyncClient() as client:
                                tasks = [fetch_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                                return await asyncio.gather(*tasks)
                        
                        try:
                            jalan_results = asyncio.run(get_all_prices())
                        except:
                            jalan_results = [("---", f"https://www.jalan.net/fwSearch.do?fw={urllib.parse.quote(h['hotel'][0]['hotelBasicInfo'].get('hotelName',''))}") for h in data["hotels"]]

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            name = info.get("hotelName", "")
                            enc_name = urllib.parse.quote(name)
                            
                            hotels.append({
                                "hotelName": name,
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": jalan_results[idx][0],
                                "jalan_url": jalan_results[idx][1],
                                "yahoo_url": f"https://travel.yahoo.co.jp/search/?stext={enc_name}",
                                "booking_url": f"https://www.booking.com/searchresults.ja.html?ss={enc_name}"
                            })
                else:
                    # エラーの時はログに出す（デバッグ用）
                    print(f"API Error: {res.status_code}")
            except Exception as e:
                print(f"System Error: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
