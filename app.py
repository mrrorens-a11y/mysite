import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数を取得
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""
    debug_msg = ""
    
    if keyword:
        # 楽天トラベルキーワード検索API
        r_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
        r_params = {
            "applicationId": RAKUTEN_APP_ID,
            "affiliateId": RAKUTEN_AFFILIATE_ID,
            "keyword": keyword,
            "hits": 10,
            "format": "json"
        }
        
        try:
            res = requests.get(r_url, params=r_params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                r_hotels = data.get('hotels', [])
                
                if not r_hotels:
                    debug_msg = f"「{keyword}」で見つかりませんでした。"
                else:
                    for item in r_hotels:
                        h = item['hotel'][0]['hotelBasicInfo']
                        hotels.append({
                            "name": h.get('hotelName'),
                            "image": h.get('hotelImageUrl'),
                            "price": f"¥{h.get('hotelMinCharge', '---')}",
                            "url": h.get('affiliateUrl') or h.get('hotelInformationUrl'),
                            "address": h.get('address1') + h.get('address2')
                        })
            else:
                debug_msg = f"楽天APIエラー: {res.status_code}"
        except Exception as e:
            debug_msg = f"接続エラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, debug_msg=debug_msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
