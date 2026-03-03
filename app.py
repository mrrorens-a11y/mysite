import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# --- 設定情報 (Renderの環境変数から取得) ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 2026年新APIドメイン
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            # APIに送るパラメータ
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # 【重要】楽天の新APIで必須となるリファラ(Referer)の設定
            headers = {
                "Referer": "https://mysite-l8l0.onrender.com/"
            }

            try:
                # APIリクエスト実行（headersを追加しています）
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers)
                
                print(f"--- Search Keyword: {keyword} ---")
                print(f"API Status Code: {res.status_code}")

                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                    else:
                        print("No hotels found.")
                else:
                    # エラー内容をログに詳細出力
                    print(f"API Error Response: {res.text}")

            except Exception as e:
                print(f"Python Error: {str(e)}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

# Render用の起動設定
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
