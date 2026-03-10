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

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 📍 目的地DB (あなたが提供してくれた主要スポット) ---
DESTINATIONS = {
    "恩納村": {"lat": 26.5050, "lng": 127.8767, "search_word": "恩納村"},
    "美ら海水族館": {"lat": 26.6943, "lng": 127.8781, "search_word": "本部町"},
    "那覇空港": {"lat": 26.2064, "lng": 127.6465, "search_word": "那覇"},
    "国際通り": {"lat": 26.2155, "lng": 127.6853, "search_word": "那覇"},
    "首里城": {"lat": 26.2170, "lng": 127.7195, "search_word": "那覇"},
    "アメリカンビレッジ": {"lat": 26.3164, "lng": 127.7576, "search_word": "北谷"},
    "万座毛": {"lat": 26.5050, "lng": 127.8500, "search_word": "恩納村"},
    "古宇利島": {"lat": 26.7020, "lng": 128.0200, "search_word": "今帰仁村"},
    "瀬長島ウミカジテラス": {"lat": 26.1748, "lng": 127.6461, "search_word": "豊見城"},
    "那覇駅": {"lat": 26.2125, "lng": 127.6792, "search_word": "那覇"}
}

# --- 🏨 テストDBホテル (必ず表示される宿) ---
DB_HOTELS = [
    {"hotelName": "テストホテル美ら海", "lat": 26.6943, "lng": 127.8780, "price": 9000, "url": "https://travel.rakuten.co.jp/"},
    {"hotelName": "テストホテル本部", "lat": 26.6930, "lng": 127.8800, "price": 8000, "url": "https://travel.rakuten.co.jp/"}
]

# --- 📏 距離計算 (Haversine) ---
def haversine(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a))
    except: return None

def format_distance(km):
    if km is None: return ""
    m = km * 1000
    return f"{int(m)}m" if m < 1000 else f"{round(km, 1)}km"

# --- じゃらんデータ取得 (非同期) ---
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
                    price = h.get("sampleRateFrom")
                    return (f"¥{price}" if price else "---"), h.get("urls", {}).get("pc")
    except: pass
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            target = DESTINATIONS.get(keyword)
            # 目的地DBにあればその検索ワードを使い、なければ入力された言葉をそのまま使う
            search_query = target["search_word"] if target else keyword

            # 1. 楽天API検索
            params = {
                "applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID, "format": "json",
                "keyword": search_query, "hits": 15
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        # じゃらん価格を並列で取得
                        async def fetch_jalan():
                            async with httpx.AsyncClient() as client:
                                tasks = [get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                                return await asyncio.gather(*tasks)
                        
                        jalan_results = asyncio.run(fetch_jalan())

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            j_price, j_url = jalan_results[idx]
                            
                            dist_km = None
                            if target:
                                dist_km = haversine(target["lat"], target["lng"], info.get("latitude"), info.get("longitude"))

                            hotels.append({
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(dist_km),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price, "jalan_url": j_url,
                                "raw_dist": dist_km if dist_km is not None else 999
                            })
            except Exception as e: print(f"Rakuten Error: {e}")

            # 2. テストDBホテル追加 (キーワードが一致する場合のみ)
            if target:
                for h in DB_HOTELS:
                    d_km = haversine(target["lat"], target["lng"], h["lat"], h["lng"])
                    hotels.append({
                        "hotelName": h["hotelName"], "hotelImageUrl": "https://picsum.photos/600/400",
                        "hotelMinCharge": h["price"], "display_distance": format_distance(d_km),
                        "target_url": h["url"], "jalan_price": "---", "jalan_url": "",
                        "raw_dist": d_km
                    })
                # 距離が近い順に並び替え
                hotels.sort(key=lambda x: x["raw_dist"])

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
