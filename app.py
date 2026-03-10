import os
import asyncio
import httpx
import requests
import math
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

# APIエンドポイント（周辺検索に変更）
RAKUTEN_AROUND_URL = "https://app.rakuten.co.jp/services/api/Travel/AroundHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 基準地点（美ら海水族館） ---
DEST_LAT = 26.694542346577375
DEST_LNG = 127.8779368039277

def calculate_distance(lat1, lng1):
    if not lat1 or not lng1: return None
    try:
        R = 6371000
        phi1, phi2 = math.radians(float(lat1)), math.radians(DEST_LAT)
        dphi = math.radians(DEST_LAT - float(lat1))
        dlamb = math.radians(DEST_LNG - float(lng1))
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlamb/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    except: return None

def format_distance(m):
    if m is None: return ""
    return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"

async def get_jalan_data(client, r_name):
    if not RECRUIT_API_KEY: return "---", ""
    params = {"key": RECRUIT_API_KEY, "keyword": r_name, "format": "json", "count": 1}
    try:
        res = await client.get(JALAN_API_URL, params=params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                j_hotel = j_data["results"]["hotel"][0]
                if fuzz.token_sort_ratio(r_name, j_hotel["hotelName"]) > 70:
                    price = j_hotel.get("sampleRateFrom")
                    return (f"¥{price}" if price else "---"), j_hotel.get("urls", {}).get("pc")
    except: pass
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        # 今回は「美ら海水族館」周辺を出すためキーワードに関わらず周辺検索を実行
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "affiliateId": RAKUTEN_AFFILIATE_ID,
            "format": "json",
            "latitude": DEST_LAT,
            "longitude": DEST_LNG,
            "searchRadius": 3, # 3km圏内
            "hits": 15
        }
        
        try:
            res = requests.get(RAKUTEN_AROUND_URL, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "hotels" in data:
                    async def fetch_all_jalan():
                        async with httpx.AsyncClient() as client:
                            tasks = [get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                            return await asyncio.gather(*tasks)

                    jalan_results = asyncio.run(fetch_all_jalan())

                    for idx, h in enumerate(data["hotels"]):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        j_price, j_url = jalan_results[idx]
                        dist_m = calculate_distance(info.get("latitude"), info.get("longitude"))
                        
                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": format_distance(dist_m),
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        })
            else:
                print(f"Rakuten Error: {res.status_code}")
        except Exception as e:
            print(f"System Error: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
