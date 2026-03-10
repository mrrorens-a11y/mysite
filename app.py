import os
import asyncio
import httpx # 非同期通信用のライブラリ
import requests
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

def format_distance(m):
    if m is None: return ""
    m = float(m)
    return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"

# --- 【爆速化の肝】じゃらんAPIを非同期で叩く関数 ---
async def fetch_jalan_data(client, r_name):
    if not RECRUIT_API_KEY:
        return "---", ""
    j_params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 5
    }
    try:
        # タイムアウトを短めに設定して全体の停滞を防ぐ
        res = await client.get(JALAN_API_URL, params=j_params, timeout=4.0)
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
    return "---", ""

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
                "hits": 15
            }
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent": "Mozilla/5.0",
                "accept": "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        # --- 【爆速化の実行】一斉に検索を開始 ---
                        async def get_all_prices():
                            async with httpx.AsyncClient() as client:
                                tasks = [fetch_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                                return await asyncio.gather(*tasks)
                        
                        # 非同期処理の結果をまとめて受け取る
                        jalan_results = asyncio.run(get_all_prices())

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            j_price, j_url = jalan_results[idx] # まとめて取得した結果を割り当てる

                            hotels.append({
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(info.get("searchDistance")),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price,
                                "jalan_url": j_url
                            })
                else:
                    print(f"RAKUTEN ERROR: {res.status_code}")
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
