import os
import math
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数チェックログ ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

print(f"DEBUG: RAKUTEN_APP_ID exists: {bool(RAKUTEN_APP_ID)}")
print(f"DEBUG: RECRUIT_API_KEY exists: {bool(RECRUIT_API_KEY)}")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# --- 📍 目的地DB ---
DESTINATIONS = {
    "美ら海水族館": {"lat": 26.694542346577375, "lng": 127.8779368039277, "search_word": "本部町"}
}

def get_display_distance(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        m = R * c * 1000
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 2)}km"
    except Exception as e:
        print(f"DEBUG: Distance calculation error: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        print(f"DEBUG: Search start - Keyword: {keyword}")
        
        if keyword:
            target_info = DESTINATIONS.get(keyword)
            api_keyword = target_info["search_word"] if target_info else keyword
            print(f"DEBUG: Using API keyword: {api_keyword}")

            params = {"applicationId": RAKUTEN_APP_ID, "format": "json", "keyword": api_keyword, "hits": 20}
            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                print(f"DEBUG: Rakuten API Status: {res.status_code}")
                
                if res.status_code == 200:
                    data = res.json()
                    raw_hotels = data.get("hotels", [])
                    print(f"DEBUG: Found {len(raw_hotels)} hotels from Rakuten")
                    
                    for h_item in raw_hotels:
                        info = h_item["hotel"][0]["hotelBasicInfo"]
                        h_name = info.get("hotelName")
                        
                        d_text = None
                        raw_dist = 999999
                        if target_info:
                            d_text = get_display_distance(
                                target_info['lat'], target_info['lng'], 
                                info.get('latitude'), info.get('longitude')
                            )
                            if d_text:
                                val = float(d_text.replace('km','').replace('m',''))
                                raw_dist = val * 1000 if 'km' in d_text else val

                        hotels.append({
                            "hotelName": h_name,
                            "hotelImageUrl": info.get("hotelImageUrl"),
                            "hotelMinCharge": info.get("hotelMinCharge"),
                            "display_distance": d_text,
                            "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                            "raw_dist": raw_dist
                        })
                    
                    if target_info:
                        hotels.sort(key=lambda x: x['raw_dist'])
                        print("DEBUG: Hotels sorted by distance")
                else:
                    print(f"DEBUG: API Error Body: {res.text}")
            except Exception as e:
                print(f"DEBUG: Request Error: {e}")
                
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
