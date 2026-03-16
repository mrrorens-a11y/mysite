import os
import csv
import math
import sqlite3
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

# --- ① CSVデータの読み込み関数（追加） ---
def load_hotel_db():
    hotels_db = {}
    if os.path.exists('hotels.csv'):
        with open('hotels.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
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

# --- ② 距離計算ロジック（追加） ---
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

# --- 既存：SQLiteからIDを取得する関数（変更なし） ---
def get_hotel_from_db(rakuten_id):
    try:
        conn = sqlite3.connect('tomarun.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        search_id = str(rakuten_id)
        cursor.execute('SELECT jalan_id, yahoo_id FROM hotels WHERE rakuten_id = ?', (search_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"jalan": row["jalan_id"], "yahoo": row["yahoo_id"]}
    except Exception as e:
        print(f"DB Error: {e}")
    return None

# 環境変数（変更なし）
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

def format_distance(m):
    if m is None: return ""
    try:
        m = float(m)
        if m < 1000:
            return f"{int(m)}m"
        else:
            return f"{round(m/1000, 1)}km"
    except:
        return ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels  = []
    keyword = ""

    # --- ③ CSVをロードしてログ表示（追加） ---
    hotel_db = load_hotel_db()
    dest_db  = load_destinations()
    print(f"hotel_db件数: {len(hotel_db)}")
    print(f"dest_db件数: {len(dest_db)}")

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
                            info = h["hotel"][0]["hotelBasicInfo"]
                            name = info.get("hotelName", "")
                            rakuten_id = str(info.get("hotelNo"))

                            clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', name).strip()
                            search_enc = urllib.parse.quote(f"{clean_name} {info.get('address1', '')}")

                            # --- 既存：SQLite検索（変更なし） ---
                            match = get_hotel_from_db(rakuten_id)

                            # --- ④ CSV検索・距離計算（追加） ---
                            csv_match  = hotel_db.get(rakuten_id)
                            dist_str   = ""
                            dest_name  = ""
                            if csv_match and csv_match.get('lat') and dest_db:
                                dist_km  = get_distance(csv_match['lat'], csv_match['lng'],
                                                        dest_db[0]['lat'], dest_db[0]['lng'])
                                dist_str  = format_distance_km(dist_km)
                                dest_name = dest_db[0]['name']

                            # --- 既存：デバッグログ（変更なし＋CSV結果を追加） ---
                            print(f"--- DEBUG START ---")
                            print(f"楽天ID: {rakuten_id} | 宿名: {name}")
                            print(f"DBからの取得結果: {match}")
                            print(f"CSVからの取得結果: {csv_match}")  # ← 追加
                            print(f"距離: {dist_str} / 目的地: {dest_name}")   # ← 追加
                            if match:
                                print(f"生成される予定のじゃらんURL: https://www.jalan.net/{match['jalan']}/")
                            print(f"--- DEBUG END ---")

                            # --- 既存：URL生成（変更なし） ---
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
                                "display_distance": dist_str or format_distance(info.get("searchDistance")),  # CSV距離優先
                                "dest_name":        dest_name,  # ← 追加
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
