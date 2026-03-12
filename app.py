import os
import asyncio
import httpx
import requests
import urllib.parse
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- じゃらん名寄せ検索（非同期版） ---
async def fetch_jalan_data(client, r_name):
    # 初期値（APIがダメでも検索結果ページに飛ばすURL）
    encoded_name = urllib.parse.quote(r_name)
    fallback_url = f"https://www.jalan.net/fwSearch.do?fw={encoded_name}"
    
    if not RECRUIT_API_KEY:
        return "---", fallback_url

    j_params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 5
    }
    try:
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                for j_hotel in j_data["results"]["hotel"]:
                    score = fuzz.token_sort_ratio(r_name, j_hotel["hotelName"])
                    if score > 75:
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
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }

            # 🚨 復活させた403エラー対策ヘッダー
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
                        async def get_all_prices():
                            async with httpx.AsyncClient() as client:
                                tasks = [fetch_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                                return await asyncio.gather(*tasks)
                        
                        jalan_results = asyncio.run(get_all_prices())

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            hotel_name = info.get("hotelName", "")
                            encoded_name = urllib.parse.quote(hotel_name)
                            j_price, j_url = jalan_results[idx]

                            hotels.append({
                                "hotelName": hotel_name,
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price,
                                "jalan_url": j_url,
                                "yahoo_url": f"https://travel.yahoo.co.jp/search/?stext={encoded_name}",
                                "booking_url": f"https://www.booking.com/searchresults.ja.html?ss={encoded_name}",
                                "display_distance": None # 距離は無効化
                            })
                else:
                    print(f"RAKUTEN ERROR: {res.status_code}")
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
