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
    """
    hotels.csv (id, name, lat, lng, address, tel) と
    hotel_otas.csv (hotel_id, ota, ota_id) を結合して
    rakuten_id → { lat, lng, jalan_id, yahoo_id, booking_id } の辞書を返す
    """
    # 1. hotels.csv を読み込む (id → hotel情報)
    hotels_by_id = {}
    hotels_path = os.path.join(BASE_DIR, 'hotels.csv')
    if os.path.exists(hotels_path):
        with open(hotels_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hotel_id = row.get('id', '').strip()
                if hotel_id:
                    hotels_by_id[hotel_id] = {k: v.strip() for k, v in row.items()}
    else:
        print(f"⚠️ hotels.csv が見つかりません: {hotels_path}")

    # 2. hotel_otas.csv を読み込み、hotel_id → {ota: ota_id} のマップを作る
    ota_map = {}  # hotel_id → { 'rakuten': '...', 'jalan': '...', 'yahoo': '...', 'booking': '...' }
    otas_path = os.path.join(BASE_DIR, 'hotel_otas.csv')
    if os.path.exists(otas_path):
        with open(otas_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                h_id = row.get('hotel_id', '').strip()
                ota  = row.get('ota', '').strip().lower()
                ota_id = row.get('ota_id', '').strip()
                if h_id and ota and ota_id:
                    if h_id not in ota_map:
                        ota_map[h_id] = {}
                    ota_map[h_id][ota] = ota_id
    else:
        print(f"⚠️ hotel_otas.csv が見つかりません: {otas_path}")

    # 3. rakuten_id をキーにした辞書を構築
    hotel_db = {}
    for hotel_id, otas in ota_map.items():
        rakuten_id = otas.get('rakuten')
        if not rakuten_id:
            continue
        hotel_info = hotels_by_id.get(hotel_id, {})
        hotel_db[rakuten_id] = {
            'lat':        hotel_info.get('lat', ''),
            'lng':        hotel_info.get('lng', ''),
            'name':       hotel_info.get('name', ''),
            'address':    hotel_info.get('address', ''),
            'jalan_id':   otas.get('jalan', ''),
            'yahoo_id':   otas.get('yahoo', ''),
            'booking_id': otas.get('booking', ''),
        }

    print(f"✅ hotel_db ロード完了: {len(hotel_db)} 件")
    return hotel_db


def load_destinations():
    """destinations.csv (name, lat, lng) を読み込む"""
    destinations = []
    csv_path = os.path.join(BASE_DIR, 'destinations.csv')
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                destinations.append({k: v.strip() for k, v in row.items()})
    else:
        print(f"⚠️ destinations.csv が見つかりません: {csv_path}")
    return destinations


# --- 距離計算とフォーマット ---

def get_distance(lat1, lng1, lat2, lng2):
    """2点間の距離(km)をハversine式で計算"""
    try:
        if not all([lat1, lng1, lat2, lng2]):
            return None
        R = 6371.0
        r_lat1, r_lng1, r_lat2, r_lng2 = map(math.radians,
            [float(lat1), float(lng1), float(lat2), float(lng2)])
        d_lat = r_lat2 - r_lat1
        d_lng = r_lng2 - r_lng1
        a = math.sin(d_lat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except Exception:
        return None


def format_distance_display(dist_km):
    """1km未満は '500m'、1km以上は '1.2km' と表示"""
    if dist_km is None:
        return ""
    if dist_km < 1.0:
        return f"{int(dist_km * 1000)}m"
    return f"{round(dist_km, 1)}km"


# --- 環境変数 ---
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()
RAKUTEN_API_URL      = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 起動時にCSVをロード
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
                "affiliateId":   RAKUTEN_AFFILIATE_ID,
                "format":        "json",
                "keyword":       keyword,
                "hits":          15,
            }
            headers = {
                "user-agent": "Mozilla/5.0",
                "accept":     "application/json",
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info       = h["hotel"][0]["hotelBasicInfo"]
                            name       = info.get("hotelName", "")
                            rakuten_id = str(info.get("hotelNo", ""))

                            # ホテル名のクレンジング（記号削除）
                            clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', name).strip()
                            search_enc = urllib.parse.quote(clean_name)

                            # CSVから取得した情報（存在しない場合は空dict）
                            csv_match = hotel_db.get(rakuten_id, {})

                            # 距離計算
                            dist_str  = ""
                            dest_name = ""
                            if csv_match.get('lat') and dest_db:
                                dist_km = get_distance(
                                    csv_match['lat'], csv_match['lng'],
                                    dest_db[0]['lat'], dest_db[0]['lng']
                                )
                                dist_str  = format_distance_display(dist_km)
                                dest_name = dest_db[0]['name']

                            # じゃらんURL
                            j_id = csv_match.get('jalan_id')
                            jalan_url = (f"https://www.jalan.net/{j_id}/"
                                         if j_id else
                                         f"https://www.jalan.net/yad/?keyword={search_enc}")

                            # Yahoo/一休URL
                            y_id = csv_match.get('yahoo_id')
                            yahoo_url = (f"https://travel.yahoo.co.jp/{y_id}/?ppc=2"
                                         if y_id else
                                         f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}")

                            # Booking.com URL
                            b_id = csv_match.get('booking_id')
                            booking_url = (f"https://www.booking.com/hotel/jp/{b_id}.ja.html"
                                           if b_id else
                                           f"https://www.booking.com/searchresults.ja.html?ss={search_enc}")

                            hotels.append({
                                "hotelName":        name,
                                "hotelImageUrl":    info.get("hotelImageUrl"),
                                "address1":         info.get("address1", ""),
                                "address2":         info.get("address2", ""),
                                "hotelMinCharge":   info.get("hotelMinCharge"),
                                "display_distance": dist_str,
                                "dest_name":        dest_name,
                                "target_url":       info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_url":        jalan_url,
                                "yahoo_url":        yahoo_url,
                                "booking_url":      booking_url,
                            })

            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
