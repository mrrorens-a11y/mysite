import os
import csv
import math
import sqlite3
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

# ✅ 修正①: app.pyと同じディレクトリを基準にする
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CSVデータの読み込み関数 ---
def load_hotel_db():
    hotels_db = {}
    csv_path = os.path.join(BASE_DIR, 'hotels.csv')
    print(f"CSVパス確認: {csv_path}")
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # ✅ 修正②: 余白を除去してキーを正規化
                hotels_db[row['rakuten_id'].strip()] = {k: v.strip() for k, v in row.items()}
    else:
        print(f"⚠️ hotels.csv が見つかりません: {csv_path}")
    return hotels_db

def load_destinations():
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

# --- 距離計算 ---
def get_distance(lat1, lng1, lat2, lng2):
    if not all([lat1, lng1, lat2, lng2]): return None
    R = 6371.0
    r_lat1, r_lng1, r_lat2, r_lng2 = map(math.radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
    d_lat = r_lat2 - r_lat1
    d_lng = r_lng2 - r_lng1
    a = math.sin(d_lat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def format_distance_km(dist_km):
    if dist_km is None: return ""
    if dist_km < 1:
        return f"{int(dist_km * 1000)}m"
    else:
        return f"{round(dist_km, 1)}km"

# --- SQLiteからIDを取得する関数 ---
def get_hotel_from_db(rakuten_id):
    try:
        db_path = os.path.join(BASE_DIR, 'tomarun.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT jalan_id, yahoo_id FROM hotels WHERE rakuten_id = ?', (str(rakuten_id),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"jalan": row["jalan_id"], "yahoo": row["yahoo_id"]}
    except Exception as e:
        print(f"DB Error: {e}")
    return None

# 環境変数
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()
RAKUTEN_API_URL      = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

def format_distance(m):
    if m is None: return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"
    except:
        return ""

# ✅ 修正③: 起動時に1回だけCSVをロード（リクエストのたびに読まない）
hotel_db = load_hotel_db()
dest_db  = load_destinations()
print(f"hotel_db件数: {len(hotel_db)}")
print(f"dest_db件数: {len(dest_db)}")
if hotel_db:
    print(f"CSVサンプルID: {list(hotel_db.keys())[:3]}")

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
                "hits":          15
            }
            headers = {
                "referer":    SITE_URL + "/",
                "origin":     SITE_URL,
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

                            clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', name).strip()
                            search_enc = urllib.parse.quote(f"{clean_name} {info.get('address1', '')}")

                            # SQLite検索
                            match = get_hotel_from_db(rakuten_id)

                            # CSV検索・距離計算
                            csv_match = hotel_db.get(rakuten_id)
                            dist_str  = ""
                            dest_name = ""
                            if csv_match and csv_match.get('lat') and dest_db:
                                dist_km   = get_distance(csv_match['lat'], csv_match['lng'],
                                                         dest_db[0]['lat'], dest_db[0]['lng'])
                                dist_str  = format_distance_km(dist_km)
                                dest_name = dest_db[0]['name']

                            # デバッグログ
                            print(f"--- DEBUG START ---")
                            print(f"楽天ID: {rakuten_id} | 宿名: {name}")
                            print(f"DBからの取得結果: {match}")
                            print(f"CSVからの取得結果: {csv_match}")
                            print(f"距離: {dist_str} / 目的地: {dest_name}")
                            if match:
                                print(f"じゃらんURL予定: https://www.jalan.net/{match['jalan']}/")
                            print(f"--- DEBUG END ---")

                            # URL生成
                            if match and match['jalan']:
                                jalan_url = f"https://www.jalan.net/{match['jalan']}/"
                            else:
                                jalan_url = f"https://www.jalan.net/yad/?keyword={search_enc}"

                            if match and match['yahoo']:
                                yahoo_url = f"https://travel.yahoo.co.jp/{match['yahoo']}/?ppc=2"
                            else:
                                yahoo_url = f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}"

                            hotels.append({
                                "hotelName":        name,
                                "hotelImageUrl":    info.get("hotelImageUrl"),
                                "address1":         info.get("address1", ""),
                                "address2":         info.get("address2", ""),
                                "hotelMinCharge":   info.get("hotelMinCharge"),
                                "display_distance": dist_str or format_distance(info.get("searchDistance")),
                                "dest_name":        dest_name,
                                "target_url":       info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_url":        jalan_url,
                                "yahoo_url":        yahoo_url,
                                "booking_url":      f"https://www.booking.com/searchresults.ja.html?ss={search_enc}",
                            })
            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
