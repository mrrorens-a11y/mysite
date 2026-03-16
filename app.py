import os
import csv
import math
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

# --- 1. CSVデータの読み込み関数 ---
def load_hotel_db():
    hotels_db = {}
    if os.path.exists('hotels.csv'):
        with open('hotels.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 楽天IDをキーにしてデータを格納
                hotels_db[row['rakuten_id']] = row
    return hotels_db

def load_destinations():
    destinations = []
    if os.path.exists('destinations.csv'):
        with open('destinations.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                destinations.append(row)
    return destinations

# --- 2. 距離計算ロジック ---
def get_distance(lat1, lng1, lat2, lng2):
    if not all([lat1, lng1, lat2, lng2]): return None
    R = 6371.0 # 地球の半径km
    r_lat1, r_lng1, r_lat2, r_lng2 = map(math.radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
    d_lat = r_lat2 - r_lat1
    d_lng = r_lng2 - r_lng1
    a = math.sin(d_lat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def format_distance(dist_km):
    if dist_km is None: return ""
    if dist_km < 1:
        return f"{int(dist_km * 1000)}m"
    else:
        return f"{round(dist_km, 1)}km"

# 環境変数
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    
    # データを最新のCSVからロード
    hotel_db = load_hotel_db()
    dest_db = load_destinations()

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey":     RAKUTEN_ACCESS_KEY,
                "affiliateId":   RAKUTEN_AFFILIATE_ID,
                "format":        "json",
                "keyword":       keyword,
                "hits":          15
            }
            headers = {"referer": SITE_URL + "/", "user-agent": "Mozilla/5.0"}

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for h in data.get("hotels", []):
                        info = h["hotel"][0]["hotelBasicInfo"]
                        rakuten_id = str(info.get("hotelNo"))
                        
                        # --- CSVからマッチング ---
                        match = hotel_db.get(rakuten_id)
                        
                        # 距離計算（目的地DBの1番目との距離を計算）
                        dist_str = ""
                        dest_name = ""
                        if match and match['lat'] and dest_db:
                            dist_km = get_distance(match['lat'], match['lng'], dest_db[0]['lat'], dest_db[0]['lng'])
                            dist_str = format_distance(dist_km)
                            dest_name = dest_db[0]['name']

                        # URL生成
                        clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', info.get("hotelName", "")).strip()
                        search_enc = urllib.parse.quote(f"{clean_name} {info.get('address1', '')}")

                        jalan_url = f"https://www.jalan.net/{match['jalan_id']}/" if match and match.get('jalan_id') else f"https://www.jalan.net/yad/?keyword={search_enc}"
                        yahoo_url = f"https://travel.yahoo.co.jp/{match['yahoo_id']}/?ppc=2" if match and match.get('yahoo_id') else f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}"

                        hotels.append({
                            "hotelName": info.get("hotelName"),
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "address1": info.get("address1", ""),
                            "address2": info.get("address2", ""),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": dist_str,
                            "dest_name": dest_name, # 目的地名を追加
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_url": jalan_url,
                            "yahoo_url": yahoo_url,
                            "booking_url": f"https://www.booking.com/searchresults.ja.html?ss={search_enc}",
                        })
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
