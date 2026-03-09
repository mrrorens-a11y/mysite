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
    """名寄せ用のクレンジング"""
    if not name: return ""
    name = re.sub(r'[（(［\[〈<＜【].*?[】＞>〉\]］)）]', '', name)
    return name.replace('　', ' ').strip()

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 共通のヘッダー（楽天403対策：User-Agentをしっかり設定）
            headers = {
                "User-Agent": "TomarunApp/1.0 (https://mysite-l8l0.onrender.com/)",
                "Accept": "application/json"
            }

            # 1. 楽天APIから一括取得 (1回)
            r_params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # 2. じゃらんAPIから一括取得 (1回)
            j_list = []
            if RECRUIT_API_KEY:
                j_params = {
                    "key": RECRUIT_API_KEY,
                    "keyword": keyword,
                    "format": "json",
                    "count": 20
                }
                try:
                    j_res = requests.get(JALAN_API_URL, params=j_params, timeout=10)
                    if j_res.status_code == 200:
                        j_data = j_res.json()
                        j_list = j_data.get("results", {}).get("hotel", [])
                except Exception as e:
                    print(f"Jalan API Error: {e}")

            # 3. 楽天の結果をベースに、メモリ上でじゃらんと突合
            try:
                r_res = requests.get(RAKUTEN_API_URL, params=r_params, headers=headers, timeout=10)
                print(f"DEBUG: Rakuten Status: {r_res.status_code}")
                
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

                        # メモリ上のじゃらんリストから一番近いものを探す
                        best_score = 0
                        for j_hotel in j_list:
                            j_name_clean = clean_name(j_hotel.get("hotelName", ""))
                            score = fuzz.token_sort_ratio(r_clean, j_name_clean)
                            
                            if score > 60 and score > best_score:
                                best_score = score
                                price = j_hotel.get("sampleRateFrom")
                                item["jalan_price"] = f"¥{price}" if price else "---"
                                item["jalan_url"] = j_hotel.get("urls", {}).get("pc")
                        
                        hotels.append(item)
                else:
                    print(f"RAKUTEN ERROR: {r_res.status_code} {r_res.text}")

            except Exception as e:
                print(f"System Error: {e}")

    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
