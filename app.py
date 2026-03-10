import os
import asyncio
import httpx
import math
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

# --- 📍 あなたが地道に集める価値のある目的地DB ---
DESTINATIONS = {
    "恩納村": {"lat": 26.5050, "lng": 127.8767},
    "美ら海水族館": {"lat": 26.6943, "lng": 127.8781},
    "那覇空港": {"lat": 26.2064, "lng": 127.6465},
    "国際通り": {"lat": 26.2155, "lng": 127.6853},
    "首里城": {"lat": 26.2170, "lng": 127.7195},
    "アメリカンビレッジ": {"lat": 26.3164, "lng": 127.7576},
    "万座毛": {"lat": 26.5050, "lng": 127.8500},
    "古宇利島": {"lat": 26.7020, "lng": 128.0200},
    "瀬長島ウミカジテラス": {"lat": 26.1748, "lng": 127.6461},
    "那覇駅": {"lat": 26.2125, "lng": 127.6792},
}

# --- 📏 精密距離計算 (Hotels.comスタイル) ---
def get_distance_str(lat1, lon1, lat2, lon2):
    try:
        # すべて数値に変換（ここが失敗の分岐点）
        p1_lat, p1_lon = float(lat1), float(lon1)
        p2_lat, p2_lon = float(lat2), float(lon2)
        
        R = 6371000 # 地球の半径(m)
        d_lat = math.radians(p2_lat - p1_lat)
        d_lon = math.radians(p2_lon - p1_lon)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(p1_lat)) * math.cos(math.radians(p2_lat)) * math.sin(d_lon/2)**2
        dist_m = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
        
        if dist_m < 1000:
            return f"{int(dist_m)}m"
        else:
            return f"{round(dist_m/1000, 2)}km"
    except:
        return None

async def get_jalan_data(client, r_name):
    if not RECRUIT_API_KEY: return "---", ""
    try:
        j_params = {"key": RECRUIT_API_KEY, "keyword": r_name, "format": "json", "count": 1}
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                h = j_data["results"]["hotel"][0]
                if fuzz.token_sort_ratio(r_name, h["hotelName"]) > 75:
                    return (f"¥{h.get('sampleRateFrom')}" if h.get('sampleRateFrom') else "---"), h.get("urls", {}).get("pc")
    except: pass
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID, "format": "json",
                "keyword": keyword, "hits": 15
            }
            res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "hotels" in data:
                    # キーワードがDBにあれば座標をセット
                    base = DESTINATIONS.get(keyword)
                    
                    async def fetch_jalan():
                        async with httpx.AsyncClient() as client:
                            tasks = [get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                            return await asyncio.gather(*tasks)
                    
                    j_results = asyncio.run(fetch_jalan())

                    for idx, h in enumerate(data["hotels"]):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        j_price, j_url = j_results[idx]
                        
                        # 距離計算の実行
                        d_str = None
                        if base:
                            d_str = get_distance_str(base['lat'], base['lng'], info.get('latitude'), info.get('longitude'))

                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": d_str,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url
                        })
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
