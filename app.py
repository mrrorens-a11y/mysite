import os
import asyncio
import httpx
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# じゃらん価格取得（非同期）
async def get_jalan_price(client, hotel_name):
    if not RECRUIT_API_KEY: return "---", ""
    try:
        params = {"key": RECRUIT_API_KEY, "keyword": hotel_name, "format": "json", "count": 1}
        res = await client.get(JALAN_API_URL, params=params, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and "hotel" in data["results"]:
                h = data["results"]["hotel"][0]
                if fuzz.token_sort_ratio(hotel_name, h["hotelName"]) > 75:
                    p = h.get("sampleRateFrom")
                    return (f"¥{p}" if p else "---"), h.get("urls", {}).get("pc")
    except: pass
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 楽天APIへのリクエスト
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }
            # 403エラー対策のヘッダー
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    raw_list = data.get("hotels", [])
                    
                    # じゃらん価格を一斉に取得
                    async def fetch_prices():
                        async with httpx.AsyncClient() as client:
                            tasks = [get_jalan_price(client, h["hotel"][0]["hotelBasicInfo"]["hotelName"]) for h in raw_list]
                            return await asyncio.gather(*tasks)
                    
                    jalan_results = asyncio.run(fetch_prices()) if raw_list else []

                    for idx, h_item in enumerate(raw_list):
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        j_p, j_u = jalan_results[idx]
                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_p,
                            "jalan_url": j_u
                        })
                else:
                    print(f"Rakuten Error: {res.status_code}")
            except Exception as e:
                print(f"Error: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
