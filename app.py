import os
import csv
import math
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 都道府県別の宿データを動的に読み込む ---
def load_pref_hotel_db(pref_code):
    combined_db = {}
    if not pref_code:
        return combined_db

    file_name = f"{pref_code}.csv"
    hotels_path = os.path.join(BASE_DIR, file_name)
    
    if not os.path.exists(hotels_path):
        hotels_path = os.path.join(BASE_DIR, "hotels", file_name)

    if os.path.exists(hotels_path):
        with open(hotels_path, mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                r_id = (row.get('rakuten_id') or "").strip()
                if r_id:
                    combined_db[r_id] = {k: (v or "").strip() for k, v in row.items()}
    return combined_db

def load_destinations():
    destinations = []
    csv_path = os.path.join(BASE_DIR, 'destinations.csv')
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                destinations.append({k: (v or "").strip() for k, v in row.items()})
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
BOOKING_AID          = os.environ.get("BOOKING_AID", "").strip()
AGODA_AID            = os.environ.get("AGODA_AID", "").strip()

dest_db  = load_destinations()

@app.route("/", methods=["GET", "POST"])
def index():
    hotels  = []
    keyword = ""
    hotel_db = {} 

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            target_dest = None
            for d in dest_db:
                d_name = d.get('name', '')
                keys = [k.strip() for k in d.get('search_keys', '').split(',') if k.strip()]
                
                if keyword == d_name or any(k in keyword for k in keys):
                    target_dest = d
                    print(f"DEBUG: Match found -> {d_name} ({d.get('pref_code')})")
                    break

            # 【修正】dest_lat/dest_lng をループの外・前に定義（スコープ問題の解消）
            dest_lat = target_dest.get('lat') if target_dest else None
            dest_lng = target_dest.get('lng') if target_dest else None  # 【修正】'ng' タイポを削除

            if target_dest:
                pref_code = target_dest.get('pref_code')
                hotel_db = load_pref_hotel_db(pref_code)

                if dest_lat and dest_lng:
                    # 周辺検索API
                    api_url = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20170426"
                    params = {"applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY, "affiliateId": RAKUTEN_AFFILIATE_ID, "format": "json", "latitude": dest_lat, "longitude": dest_lng, "searchRadius": 3.0, "datumType": 1, "hits": 21}
                else:
                    # 座標がない場合のキーワード検索（安全策）
                    api_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
                    params = {"applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY, "affiliateId": RAKUTEN_AFFILIATE_ID, "format": "json", "keyword": keyword, "hits": 21}
            else:
                # 目的地DBにないワードで検索された場合
                api_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
                params = {"applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY, "affiliateId": RAKUTEN_AFFILIATE_ID, "format": "json", "keyword": keyword, "hits": 21}

            headers = {"referer": SITE_URL + "/", "origin": SITE_URL, "user-agent": "Mozilla/5.0", "accept": "application/json"}

            try:
                res = requests.get(api_url, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info = h["hotel"][0]["hotelBasicInfo"]
                            rakuten_id = str(info.get("hotelNo"))
                            csv_match = hotel_db.get(rakuten_id, {})

                            # --- 距離計算 ---
                            dist_str = ""
                            dist_val = float('inf')
                            h_lat = csv_match.get('lat') or info.get('latitude')
                            h_lng = csv_match.get('lng') or info.get('longitude')
                            
                            if dest_lat and h_lat:
                                d_km = get_distance(h_lat, h_lng, dest_lat, dest_lng)
                                if d_km is not None:
                                    dist_str = format_distance_display(d_km)
                                    dist_val = d_km

                            # リンク生成用クエリ作成
                            raw_name = info.get("hotelName", "")
                            clean_name = re.sub(r'[\(\（【［].*?[\)\）】］]', '', raw_name).strip()
                            search_address = csv_match.get('address') or info.get('address1', '')
                            search_tel = csv_match.get('tel', '')
                            search_text = f"{clean_name} {search_tel} {search_address}".strip()
                            hotel_search_query = urllib.parse.quote(search_text)

                            # リンクの組み立て
                            b_url = f"https://www.booking.com/searchresults.ja.html?ss={hotel_search_query}"
                            if BOOKING_AID: b_url += f"&aid={BOOKING_AID}"

                            # --- 【変更箇所】Agoda：宿名のみ＋緯度経度で検索 ---
                            agoda_query = urllib.parse.quote(clean_name)
                            a_url = (
                                "https://www.agoda.com/ja-jp/search"
                                f"?textToSearch={agoda_query}"
                                f"&latitude={h_lat}"
                                f"&longitude={h_lng}"
                                "&rooms=1"
                                "&adults=2"
                            )
                            if AGODA_AID: a_url += f"&cid={AGODA_AID}"

                            hotels.append({
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": dist_str,
                                "dist_val": dist_val,
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_url": f"https://www.jalan.net/{csv_match.get('jalan_id')}/" if csv_match.get('jalan_id') else f"https://www.jalan.net/yad/?keyword={hotel_search_query}",
                                "yahoo_url": f"https://travel.yahoo.co.jp/{csv_match.get('yahoo_id')}/?ppc=2" if csv_match.get('yahoo_id') else f"https://travel.yahoo.co.jp/search-hotel/?keyword={hotel_search_query}",
                                "booking_url": b_url,
                                "agoda_url": a_url,
                            })

                        # 距離順にソート
                        if target_dest and dest_lat:
                            hotels.sort(key=lambda x: x['dist_val'])

            except Exception as e:
                print("SYSTEM ERROR:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword, destinations=dest_db)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
