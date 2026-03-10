import os
import asyncio
import httpx
import requests
import math
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数設定 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

# APIエンドポイント
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 目的地（美ら海水族館）の座標 ---
DEST_LAT = 26.694542346577375
DEST_LNG = 127.8779368039277

def calculate_distance(lat1, lng1, lat2, lng2):
    """緯度経度から2点間の直線距離(m)を計算"""
    if not lat1 or not lng1: return None
    R = 6371000  # 地球の半径 (m)
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlamb = math.radians(float(lng2) - float(lng1))
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlamb/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def format_distance(m):
    """距離表示を500mや1.2kmに整形"""
    if m is None: return ""
    return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"

async def get_jalan_data(client, r_name):
    """じゃらんAPIを非同期で検索"""
    if not RECRUIT_API_KEY: return "---", ""
    j_params = {"key": RECRUIT_API_KEY, "keyword": r_name, "format": "json", "count": 1}
    try:
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                j_hotel = j_data["results"]["hotel"][0]
                score = fuzz.token_sort_ratio(r_name, j_hotel["hotelName"])
                if score > 70:
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
        if keyword:
            # 楽天APIリクエスト
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY, # ここを確実に送る
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }
            # エラー防止のため headers も設定
            headers = {"user-agent": "Mozilla/5.0"}
            
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
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
                            
                            # 距離計算
                            dist_m = calculate_distance(info.get("latitude"), info.get("longitude"), DEST_LAT, DEST_LNG)
                            
                            hotels.append({
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(dist_m),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price,
                                "jalan_url": j_url
                            })
            except Exception as e:
                print(f"Error: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
