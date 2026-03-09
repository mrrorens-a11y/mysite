import os
import requests
import re
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

def format_distance(m):
    if m is None: return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"
    except:
        return ""

def clean_name(name):
    if not name: return ""
    # カッコ類と中身を排除
    name = re.sub(r'[（(［\[〈<＜【].*?[】＞>〉\]］)）]', '', name)
    return name.replace('　', ' ').strip()

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 楽天403回避用ヘッダー
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }

            # 1. じゃらんから一括取得 (名寄せ用)
            j_list = []
            if RECRUIT_API_KEY:
                j_params = {
                    "key": RECRUIT_API_KEY,
                    "keyword": keyword,
                    "format": "json",
                    "count": 30 # 名寄せのヒット率を上げるため少し多めに
                }
                try:
                    j_res = requests.get(JALAN_API_URL, params=j_params, timeout=10)
                    if j_res.status_code == 200:
                        j_data = j_res.json()
                        j_list = j_data.get("results", {}).get("hotel", [])
                except Exception as e:
                    print(f"DEBUG: Jalan API Error: {e}")

            # 2. 楽天から取得
            r_params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            try:
                r_res = requests.get(RAKUTEN_API_URL, params=r_params, headers=headers, timeout=10)
                if r_res.status_code == 200:
                    r_data = r_res.json()
                    for h in r_data.get("hotels", []):
                        r_info = h["hotel"][0]["hotelBasicInfo"]
                        r_name = r_info.get("hotelName", "")
                        r_clean = clean_name(r_name)
                        
                        item = {
                            "hotelName": r_name,
                            "hotelImageUrl": r_info.get("hotelImageUrl"),
                            "address1": r_info.get("address1", ""),
                            "address2": r_info.get("address2", ""),
                            "hotelMinCharge": r_info.get("hotelMinCharge"),
                            "display_distance": format_distance(r_info.get("searchDistance")),
                            "target_url": r_info.get("affiliateUrl") or r_info.get("hotelInformationUrl"),
                            "jalan_price": "---",
                            "jalan_url": ""
                        }

                        # メモリ内名寄せ
                        best_score = 0
                        for j_hotel in j_list:
                            j_name_clean = clean_name(j_hotel.get("hotelName", ""))
                            score = fuzz.token_sort_ratio(r_clean, j_name_clean)
                            
                            if score > 65 and score > best_score:
                                best_score = score
                                price = j_hotel.get("sampleRateFrom")
                                item["jalan_price"] = f"¥{price}" if price else "---"
                                item["jalan_url"] = j_hotel.get("urls", {}).get("pc")
                        
                        hotels.append(item)
                else:
                    print(f"DEBUG: Rakuten Status: {r_res.status_code}")

            except Exception as e:
                print(f"DEBUG: System Error: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

# Render(Gunicorn)環境でポート10000を確実に使う設定
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
