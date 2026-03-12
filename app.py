import os
import asyncio
import httpx
import requests
import urllib.parse  # URLエンコード用に追加
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

# --- じゃらん価格取得 ---
async def fetch_jalan_data(client, r_name):
    if not RECRUIT_API_KEY:
        # APIキーがない場合は検索URLだけ生成
        encoded_name = urllib.parse.quote(r_name)
        return "---", f"https://www.jalan.net/fwSearch.do?fw={encoded_name}"
    
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
                        return (f"¥{price}" if price else "---"), (url or "")
    except:
        pass
    
    # マッチしなかった場合は、じゃらんのキーワード検索結果ページへ飛ばす
    encoded_name = urllib.parse.quote(r_name)
    return "---", f"https://www.jalan.net/fwSearch.do?fw={encoded_name}"

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

            headers = {
                "user-agent": "Mozilla/5.0",
                "accept": "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        # 非同期でじゃらんの価格を取得
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
                                # Yahoo!トラベル（キーワード検索URL）
                                "yahoo_url": f"https://travel.yahoo.co.jp/search/?stext={encoded_name}",
                                # Booking.com（キーワード検索URL）
                                "booking_url": f"https://www.booking.com/searchresults.ja.html?ss={encoded_name}",
                                "display_distance": None # 距離は一旦無効化
                            })
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
