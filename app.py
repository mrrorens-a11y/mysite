import os
import asyncio
import httpx
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

# --- 【爆速化の核心】じゃらんAPIを非同期で叩く関数 ---
async def get_jalan_data(client, r_name):
    if not RECRUIT_API_KEY:
        return "---", ""
    
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
                        return (f"¥{price}" if price else "---"), j_hotel.get("urls", {}).get("pc")
    except Exception as e:
        print(f"Async Jalan Error: {e}")
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 1. 楽天APIリクエスト（ここは同期でOK）
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

            import requests
            res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                if "hotels" in data:
                    # まず楽天のデータを整理
                    temp_hotels = []
                    tasks = []
                    
                    # 非同期処理の準備
                    async def fetch_all_jalan():
                        async with httpx.AsyncClient() as client:
                            # 全ホテルのじゃらん検索を「一斉に」開始
                            job_list = [get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                            return await asyncio.gather(*job_list)

                    # 実行
                    jalan_results = asyncio.run(fetch_all_jalan())

                    # 楽天データとじゃらんの結果を合体
                    for idx, h in enumerate(data["hotels"]):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        j_price, j_url = jalan_results[idx]
                        
                        item = {
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "address1": info.get("address1", ""),
                            "address2": info.get("address2", ""),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": format_distance(info.get("searchDistance")),
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        }
                        hotels.append(item)
    
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
