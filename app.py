import os
import csv
import math
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CSVデータの読み込みと結合 ---
def load_hotel_db():
    """
    1. hotels.csv (基本情報)
    2. hotel_otas.csv (各社ID対応)
    を読み込み、楽天IDをキーにした一つの辞書に統合する
    """
    raw_hotels = {}  # id -> {name, lat, lng}
    combined_db = {} # rakuten_id -> {全情報}

    # ① hotels.csv の読み込み
    hotels_path = os.path.join(BASE_DIR, 'hotels.csv')
    if os.path.exists(hotels_path):
        with open(hotels_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                h_id = row.get('id', '').strip()
                if h_id:
                    raw_hotels[h_id] = {k: v.strip() for k, v in row.items()}
    
    # ② hotel_otas.csv の読み込みと結合
    otas_path = os.path.join(BASE_DIR, 'hotel_otas.csv')
    if os.path.exists(otas_path):
        with open(otas_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                h_id = row.get('hotel_id', '').strip()
                r_id = row.get('rakuten_id', '').strip()
                
                # hotels.csvに存在するホテルなら結合
                if h_id in raw_hotels and r_id:
                    hotel_info = raw_hotels[h_id].copy()
                    hotel_info.update({k: v.strip() for k, v in row.items()})
                    combined_db[r_id] = hotel_info
    
    print(f"✅ hotel_db ロード完了: {len(combined_db)} 件 (楽天ID紐付け済み)")
    return combined_db

def load_destinations():
    destinations = []
    csv_path = os.path.join(BASE_DIR, 'destinations.csv')
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                destinations.append({k: v.strip() for k, v in row.items()})
    return destinations

# --- 距離計算 ---
def get_distance(lat1, lng1, lat2, lng2):
    try:
        if not all([lat1, lng1, lat2, lng2]): return None
        R = 6371.0
        r_lat1, r_lng1, r_lat2, r_lng2 = map(math.radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
        d_lat = r_lat2 - r_lat1
        d_lng = r_lng2 - r_lng1
        a = math.sin(d_lat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except:
        return None

def format_distance_display(dist_km):
    """新仕様: 1km未満はm表示"""
    if dist_km is None: return ""
    return f"{int(dist_km * 1000)}m" if dist_km < 1.0 else f"{round(dist_km, 1)}km"

# 環境変数
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
RAKUTEN_API_URL      = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 起動時に一度だけロード
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
                "hits":          15
            }
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for h in data.get("hotels", []):
                        info       = h["hotel"][0]["hotelBasicInfo"]
                        rakuten_id = str(info.get("hotelNo"))
                        
                        # クレンジング後の名前（検索フォールバック用）
                        clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', info.get("hotelName", "")).strip()
                        search_enc = urllib.parse.quote(clean_name)

                        # CSVデータベース（結合済み）から情報を検索
                        csv_match = hotel_db.get(rakuten_id, {})

                        # 距離計算（CSVの座標を使用）
                        dist_str = ""
                        dest_name = ""
                        if csv_match.get('lat') and dest_db:
                            dist_km = get_distance(csv_match['lat'], csv_match['lng'],
                                                   dest_db[0]['lat'], dest_db[0]['lng'])
                            dist_str = format_distance_display(dist_km)
                            dest_name = dest_db[0]['name']

                        # 各社URL生成（IDがあれば直接、なければ検索）
                        j_id = csv_match.get('jalan_id')
                        jalan_url = f"https://www.jalan.net/{j_id}/" if j_id else f"https://www.jalan.net/yad/?keyword={search_enc}"

                        y_id = csv_match.get('yahoo_id')
                        yahoo_url = f"https://travel.yahoo.co.jp/{y_id}/?ppc=2" if y_id else f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}"

                        b_id = csv_match.get('booking_id')
                        booking_url = f"https://www.booking.com/hotel/jp/{b_id}.ja.html" if b_id else f"https://www.booking.com/searchresults.ja.html?ss={search_enc}"

                        hotels.append({
                            "hotelName":        info.get("hotelName"),
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
