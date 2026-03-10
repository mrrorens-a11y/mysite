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
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# --- 📍 目的地DB ---
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

# 距離計算
def haversine(lat1, lon1, lat2, lon2):
    try:
        if not all([lat1, lon1, lat2, lon2]): return None
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a))
    except: return None

def format_distance(km):
    if km is None: return ""
    m = km * 1000
    return f"{int(m)}m" if m < 1000 else f"{round(km, 2)}km"

async def get_jalan_price(client, hotel_name):
    if not RECRUIT_API_KEY: return "---", ""
    try:
        params = {"key": RECRUIT_API_KEY, "keyword": hotel_name, "format": "json", "count": 1}
        res = await client.get(JALAN_API_URL, params=params, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and "hotel" in data["results"]:
                h = data["results"]["hotel"][0]
                if fuzz.token_sort_ratio(hotel_name, h["hotelName"]) > 70:
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
            # 目的地があればそのエリア、なければ入力ワードで検索
            search_query = target["search_word"] if target else keyword

            # 楽天APIリクエスト (パラメータを極限までシンプルにしました)
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "format": "json",
                "keyword": search_query,
                "hits": 20,
                "elements": "hotelName,hotelImageUrl,hotelMinCharge,latitude,longitude,affiliateUrl,hotelInformationUrl"
            }
            
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    raw_hotels = data.get("hotels", [])
                    
                    # 楽天の宿が見つかった場合、じゃらんの価格も並行で取得
                    async def fetch_all_prices():
                        async with httpx.AsyncClient() as client:
                            tasks = [get_jalan_price(client, h["hotel"][0]["hotelBasicInfo"]["hotelName"]) for h in raw_hotels]
                            return await asyncio.gather(*tasks)
                    
                    jalan_data = asyncio.run(fetch_all_prices()) if raw_hotels else []

                    for idx, h_item in enumerate(raw_hotels):
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        j_price, j_url = jalan_data[idx]
                        
                        dist_km = None
                        if target:
                            dist_km = haversine(target["lat"], target["lng"], info.get("latitude"), info.get("longitude"))

                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": format_distance(dist_km),
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": j_price,
                            "jalan_url": j_url,
                            "raw_dist": dist_km if dist_km is not None else 9999
                        })
                    
                    # 目的地がある場合は近い順に並び替え
                    if target:
                        hotels.sort(key=lambda x: x["raw_dist"])
                else:
                    print(f"楽天APIエラー: {res.status_code} - {res.text}")

            except Exception as e:
                print(f"システムエラー: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
