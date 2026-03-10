import os
import asyncio
import httpx
import requests
import math
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数 (楽天API用) ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# --- 📍 目的地DB (あなたが指定した10選) ---
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

# --- 🏨 自作宿DB (各エリアに数件ずつ配置) ---
MY_HOTEL_DB = [
    {"name": "ホテル美ら海フロント", "lat": 26.6945, "lng": 127.8785, "price": 12000, "url": "https://travel.rakuten.co.jp/"},
    {"name": "那覇エアポートイン", "lat": 26.2070, "lng": 127.6470, "price": 7500, "url": "https://travel.rakuten.co.jp/"},
    {"name": "国際通りセントラルホテル", "lat": 26.2160, "lng": 127.6860, "price": 9800, "url": "https://travel.rakuten.co.jp/"},
    {"name": "アメリカンビレッジ・リゾート", "lat": 26.3170, "lng": 127.7580, "price": 15000, "url": "https://travel.rakuten.co.jp/"},
    {"name": "恩納サンセットビーチ宿", "lat": 26.5060, "lng": 127.8770, "price": 22000, "url": "https://travel.rakuten.co.jp/"}
]

# --- 📏 距離計算 ---
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
    return f"{int(m)}m" if m < 1000 else f"{round(km, 2)}km"

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            target = DESTINATIONS.get(keyword)
            
            # --- 1. 自作DBから宿を抽出 ---
            if target:
                for h in MY_HOTEL_DB:
                    dist_km = haversine(target["lat"], target["lng"], h["lat"], h["lng"])
                    # 目的地から30km以内の宿を表示（全県表示を防ぐため）
                    if dist_km and dist_km < 30:
                        hotels.append({
                            "hotelName": h["name"],
                            "hotelImageUrl": "https://picsum.photos/seed/" + h["name"] + "/600/400",
                            "hotelMinCharge": h["price"],
                            "display_distance": format_distance(dist_km),
                            "target_url": h["url"],
                            "jalan_price": "---",
                            "raw_dist": dist_km
                        })

            # --- 2. 楽天API (動けばラッキー、動かなくても自作DBが出る) ---
            params = {
                "applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID, "format": "json",
                "keyword": target["search_word"] if target else keyword, "hits": 10
            }
            headers = {"referer": "https://mysite-l8l0.onrender.com/", "user-agent": "Mozilla/5.0"}
            
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    for h_item in data.get("hotels", []):
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        dist_km = None
                        if target:
                            dist_km = haversine(target["lat"], target["lng"], info.get("latitude"), info.get("longitude"))
                        
                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": format_distance(dist_km),
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_price": "---",
                            "raw_dist": dist_km if dist_km is not None else 999
                        })
            except: pass

            # --- 3. 全体を距離順に並び替え ---
            if target:
                hotels.sort(key=lambda x: x["raw_dist"])

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
