import os
import csv
import math
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_hotel_db():
    raw_hotels = {}
    combined_db = {}

    hotels_path = os.path.join(BASE_DIR, 'hotels.csv')
    if os.path.exists(hotels_path):
        with open(hotels_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                h_id = row.get('id', '').strip()
                if h_id:
                    raw_hotels[h_id] = {k: v.strip() for k, v in row.items()}

    ota_map = {}
    otas_path = os.path.join(BASE_DIR, 'hotel_otas.csv')
    if os.path.exists(otas_path):
        with open(otas_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
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

    print(f"✅ hotel_db ロード完了: {len(combined_db)} 件")
    return combined_db


def load_destinations():
    destinations = []
    csv_path = os.path.join(BASE_DIR, 'destinations.csv')
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
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


RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()
RAKUTEN_API_URL      = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

hotel_db = load_hotel_db()
dest_db  = load_destinations()


@app.route("/", methods=["GET", "POST"])
def index():
    hotels  = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey":     RAKUTEN_ACCESS_KEY,
                "affiliateId":   RAKUTEN_AFFILIATE_ID,
                "format":        "json",
                "keyword":       keyword,
                "hits":          15,
            }

            # ===== デバッグログ =====
            print(f"🔍 検索キーワード: {keyword}")
            print(f"🔑 APP_ID: '{RAKUTEN_APP_ID[:6]}...' (空={not RAKUTEN_APP_ID})")
            print(f"🔑 ACCESS_KEY: 空={not RAKUTEN_ACCESS_KEY}")
            print(f"🔑 AFFILIATE_ID: 空={not RAKUTEN_AFFILIATE_ID}")
            # =======================

            headers = {
                "user-agent": "Mozilla/5.0",
                "referer":    SITE_URL,
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                print(f"📡 APIステータス: {res.status_code}")

                if res.status_code == 200:
                    data = res.json()
                    print(f"📦 APIレスポンスキー: {list(data.keys())}")

                    # エラーレスポンスの確認
                    if "error" in data:
                        print(f"❌ APIエラー: {data.get('error')} / {data.get('error_description')}")

                    hotel_list = data.get("hotels", [])
                    print(f"🏨 取得ホテル数: {len(hotel_list)}")

                    for h in hotel_list:
                        info       = h["hotel"][0]["hotelBasicInfo"]
                        rakuten_id = str(info.get("hotelNo", ""))
                        clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', info.get("hotelName", "")).strip()
                        search_enc = urllib.parse.quote(clean_name)

                        csv_match = hotel_db.get(rakuten_id, {})
                        dist_str  = ""
                        dest_name = ""
                        if csv_match.get('lat') and dest_db:
                            dist_km   = get_distance(csv_match['lat'], csv_match['lng'], dest_db[0]['lat'], dest_db[0]['lng'])
                            dist_str  = format_distance_display(dist_km)
                            dest_name = dest_db[0]['name']

                        j_id = csv_match.get('jalan_id')
                        y_id = csv_match.get('yahoo_id')
                        b_id = csv_match.get('booking_id')

                        hotels.append({
                            "hotelName":        info.get("hotelName"),
                            "hotelImageUrl":    info.get("hotelImageUrl"),
                            "address1":         info.get("address1", ""),
                            "address2":         info.get("address2", ""),
                            "hotelMinCharge":   info.get("hotelMinCharge"),
                            "display_distance": dist_str,
                            "dest_name":        dest_name,
                            "target_url":       info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "jalan_url":        f"https://www.jalan.net/{j_id}/" if j_id else f"https://www.jalan.net/yad/?keyword={search_enc}",
                            "yahoo_url":        f"https://travel.yahoo.co.jp/{y_id}/?ppc=2" if y_id else f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}",
                            "booking_url":      f"https://www.booking.com/hotel/jp/{b_id}.ja.html" if b_id else f"https://www.booking.com/searchresults.ja.html?ss={search_enc}",
                        })
                else:
                    print(f"❌ HTTPエラー: {res.status_code} / {res.text[:200]}")

            except Exception as e:
                print(f"💥 SYSTEM ERROR: {type(e).__name__}: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
