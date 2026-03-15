import os
import sqlite3
import requests
import urllib.parse
import re
from flask import Flask, render_template, request

app = Flask(__name__)

# --- データベースからIDを取得する関数 ---
def get_hotel_from_db(rakuten_id):
    try:
        conn = sqlite3.connect('tomarun.db')
        cursor = conn.cursor()
        # 楽天IDを元に、じゃらんIDとYahooIDを検索
        cursor.execute('SELECT jalan_id, yahoo_id FROM hotels WHERE rakuten_id = ?', (str(rakuten_id),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"jalan": row[0], "yahoo": row[1]}
    except Exception as e:
        print(f"DB Error: {e}")
    return None

# 環境変数（以前のまま）
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

def format_distance(m):
    if m is None: return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"
    except: return ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }
            headers = {"referer": SITE_URL + "/", "origin": SITE_URL, "user-agent": "Mozilla/5.0"}

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

                            # --- ここでDB（tomarun.db）を確認！ ---
                            match = get_hotel_from_db(rakuten_id)
                            
                            if match and match['jalan']:
                                jalan_url = f"https://www.jalan.net/yad{match['jalan']}/"
                            else:
                                jalan_url = f"https://www.jalan.net/searches/results/index.php?keyword={search_enc}"

                            if match and match['yahoo']:
                                yahoo_url = f"https://travel.yahoo.co.jp/{match['yahoo']}/?ppc=2"
                            else:
                                yahoo_url = f"https://travel.yahoo.co.jp/search-hotel/?keyword={search_enc}"

                            hotels.append({
                                "hotelName": name,
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(info.get("searchDistance")),
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
