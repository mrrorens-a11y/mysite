import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

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
            session = requests.Session()
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            try:
                res = session.get(RAKUTEN_API_URL, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            # ここで hotelBasicInfo を取得
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 【重要】もしアフィリエイトIDが設定されていれば、affiliateUrl が優先される
                            # なければ hotelInformationUrl を使う
                            final_url = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            info['target_url'] = final_url # テンプレートで使うための名前を固定
                            
                            hotels.append(info)
            except Exception as e:
                print(f"Error: {e}")
    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
