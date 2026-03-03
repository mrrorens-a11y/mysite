import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# --- 設定情報 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # URL設定に合わせて末尾スラッシュなしに統一
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers)
                print(f"--- Search: {keyword} / Status: {res.status_code} ---")
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                else:
                    print(f"API Error: {res.text}")
            except Exception as e:
                print(f"Error: {str(e)}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

# --- ここが重要！一番左端から書き始めてください ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Renderで確実に検知させるため host と port を明示
    app.run(host="0.0.0.0", port=port)
