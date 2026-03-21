import os
import csv
import math
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CSVデータの読み込み ---
def load_hotel_db():
    raw_hotels = {}
    combined_db = {}
    hotels_path = os.path.join(BASE_DIR, 'hotels.csv')
    if os.path.exists(hotels_path):
        with open(hotels_path, mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                h_id = row.get('id', '').strip()
                if h_id:
                    raw_hotels[h_id] = {k: v.strip() for k, v in row.items()}

    ota_map = {}
    otas_path = os.path.join(BASE_DIR, 'hotel_otas.csv')
    if os.path.exists(otas_path):
        with open(otas_path, mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                h_id   = row.get('hotel_id', '').strip()
                ota    = row.get('ota', '').strip().lower()
                ota_id = row.get('ota_id', '').strip()
                if h_id and ota and ota_id:
                    if h_id not in ota_map:
                        ota_map[h_id] = {}
                    ota_map[h_id][f"{ota}_id"] = ota_id

    for h_id, ids in ota_map.items():
        r_id = ids.get('rakuten_id')
        if r_id and h_id in raw_hotels:
            hotel_info = raw_hotels[h_id].copy()
            hotel_info.update(ids)
            combined_db[r_id] = hotel_info
    return combined_db

def load_destinations():
    destinations = []
    csv_path = os.path.join(BASE_DIR, 'destinations.csv')
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                destinations.append({k: v.strip() for k, v in row.items()})
    return destinations

def get_distance(lat1, lng1, lat2, lng2):
    try:
        if not all([lat1, lng1, lat2, lng2]): return None
        R = 6371.0
        r_lat1, r_lng1, r_lat2, r_lng2 = map(math.radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
        d_lat = r_lat2 - r_lat1
        d_lng = r_lng2 - r_lng1
        a = math.sin(d_lat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except: return None

def format_distance_display(dist_km):
    if dist_km is None: return ""
    return f"{int(dist_km * 1000)}m" if dist_km < 1.0 else f"{round(dist_km, 1)}km"

# 環境変数
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()

hotel_db = load_hotel_db()
dest_db  = load_destinations()

@app.route("/", methods=["GET", "POST"])
def index():
    hotels  = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if keyword:
            # --- 1 & 3: 目的地判別ロジック ---
            target_dest = None
            for d in dest_db:
                keys = d.get('search_keys', '').split(',')
                if any(k.strip() in keyword for k in keys) or keyword in d['name']:
                    target_dest = d
                    break

            # --- 目的地（座標）があるかどうかでAPIを切り替える ---
            if target_dest and target_dest.get('lat') and target_dest.get('lng'):
                # 座標検索 (SimpleHotelSearch)
                api_url = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20170426"
                params = {
                    "applicationId": RAKUTEN_APP_ID,
                    "accessKey":     RAKUTEN_ACCESS_KEY,
                    "affiliateId":   RAKUTEN_AFFILIATE_ID,
                    "format":        "json",
                    "latitude":      target_dest['lat'],
                    "longitude":     target_dest['lng'],
                    "searchRadius":  3.0, # 半径3km以内の宿を検索
                    "datumType":     1,   # 世界測地系
                    "hits":          21
                }
            else:
                # キーワード検索 (KeywordHotelSearch)
                api_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
                params = {
                    "applicationId": RAKUTEN_APP_ID,
                    "accessKey":     RAKUTEN_ACCESS_KEY,
                    "affiliateId":   RAKUTEN_AFFILIATE_ID,
                    "format":        "json",
                    "keyword":       keyword,
                    "hits":          21
                }

            headers = {
                "referer": SITE_URL + "/",
                "origin": SITE_URL,
                "user-agent": "Mozilla/5.0",
                "accept": "application/json"
            }

            try:
                res = requests.get(api_url, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info = h["hotel"][0]["hotelBasicInfo"]
                            rakuten_id = str(info.get("hotelNo"))
                            csv_match = hotel_db.get(rakuten_id, {})

                            # 距離計算（目的地が特定できた場合のみ）
                            dist_str = ""
                            dist_val = float('inf') # ソート用初期値
                            if target_dest and csv_match.get('lat'):
                                d_km = get_distance(csv_match['lat'], csv_match['lng'], target_dest['lat'], target_dest['lng'])
                                if d_km is not None:
                                    dist_str = format_distance_display(d_km)
                                    dist_val = d_km

                            # URL生成用
                            clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', info.get("hotelName", "")).strip()
                            search_enc = urllib.parse.quote(f"{clean_name} {info.get('address1', '')}")

                            hotels.append({
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": dist_str,
                                "dist_val": dist_val, # ソート用
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_url": f"https://www.jalan.net/{csv_match.get('jalan_id')}/" if csv_match.get('jalan_id') else f"https://www.jalan.net/yad/?keyword={search_enc}",
                                "yahoo_url": f"https://travel.yahoo.co.jp/{csv_match.get('yahoo_id')}/?ppc=2" if csv_match.get('yahoo_id') else f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}",
                                "booking_url": f"https://www.booking.com/hotel/jp/{csv_match.get('booking_id')}.ja.html" if csv_match.get('booking_id') else f"https://www.booking.com/searchresults.ja.html?ss={search_enc}",
                            })

                        # --- 目的地がある場合は距離順にソート ---
                        if target_dest:
                            hotels.sort(key=lambda x: x['dist_val'])

            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword, destinations=dest_db)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
