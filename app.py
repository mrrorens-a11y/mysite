import os
import csv
import math
import sqlite3
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

# ✅ 設定: ディレクトリ基準
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CSVデータの読み込み関数 ---
def load_hotel_db():
    """hotels.csvからホテル情報を読み込む。新仕様の各社IDにも対応"""
    hotels_db = {}
    csv_path = os.path.join(BASE_DIR, 'hotels.csv')
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 楽天IDをキーとして正規化して保存
                r_id = row.get('rakuten_id', '').strip()
                if r_id:
                    hotels_db[r_id] = {k: v.strip() for k, v in row.items()}
    else:
        print(f"⚠️ hotels.csv が見つかりません: {csv_path}")
    return hotels_db

def load_destinations():
    """目的地情報を読み込む"""
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
    """2点間の距離(km)を計算"""
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
    """新仕様: 1km未満は『500m』、1km以上は『1.2km』と表示"""
    if dist_km is None: return ""
    if dist_km < 1.0:
        return f"{int(dist_km * 1000)}m"
    else:
        return f"{round(dist_km, 1)}km"

# --- SQLite lookup (旧仕様互換・新CSVにIDがあればそちら優先) ---
def get_hotel_from_db(rakuten_id):
    db_path = os.path.join(BASE_DIR, 'tomarun.db')
    if not os.path.exists(db_path): return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT jalan_id, yahoo_id FROM hotels WHERE rakuten_id = ?', (str(rakuten_id),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"jalan": row["jalan_id"], "yahoo": row["yahoo_id"]}
    except:
        pass
    return None

# 環境変数
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
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
                "hits":          15
            }
            headers = {
                "user-agent": "Mozilla/5.0",
                "accept":     "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info       = h["hotel"][0]["hotelBasicInfo"]
                            name       = info.get("hotelName", "")
                            rakuten_id = str(info.get("hotelNo"))

                            # ホテル名のクレンジング（記号削除）
                            clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', name).strip()
                            search_enc = urllib.parse.quote(f"{clean_name}")

                            # 1. 新しいCSVから情報を取得
                            csv_match = hotel_db.get(rakuten_id, {})
                            
                            # 2. SQLite（旧仕様）からの補完
                            db_match = get_hotel_from_db(rakuten_id) or {}

                            # 距離計算（新仕様: CSVの座標を優先）
                            dist_str = ""
                            dest_name = ""
                            if csv_match.get('lat') and dest_db:
                                dist_km = get_distance(csv_match['lat'], csv_match['lng'],
                                                       dest_db[0]['lat'], dest_db[0]['lng'])
                                dist_str = format_distance_display(dist_km)
                                dest_name = dest_db[0]['name']

                            # URL生成ロジック（CSVのIDを最優先、次にSQLite、なければキーワード検索）
                            # じゃらん
                            j_id = csv_match.get('jalan_id') or db_match.get('jalan')
                            if j_id:
                                jalan_url = f"https://www.jalan.net/{j_id}/"
                            else:
                                jalan_url = f"https://www.jalan.net/yad/?keyword={search_enc}"

                            # Yahoo/一休
                            y_id = csv_match.get('yahoo_id') or db_match.get('yahoo')
                            if y_id:
                                yahoo_url = f"https://travel.yahoo.co.jp/{y_id}/?ppc=2"
                            else:
                                yahoo_url = f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}"

                            # Booking.com
                            b_id = csv_match.get('booking_id') # 新CSVにbooking_idがある場合
                            if b_id:
                                booking_url = f"https://www.booking.com/hotel/jp/{b_id}.ja.html"
                            else:
                                booking_url = f"https://www.booking.com/searchresults.ja.html?ss={search_enc}"

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
