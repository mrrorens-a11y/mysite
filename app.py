import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# --- 設定情報 (RenderのEnvironment Variablesから読み込みます) ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 2026年新ドメイン：KeywordHotelSearch API
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
            try:
                # 楽天APIへリクエスト送信
                res = requests.get(RAKUTEN_API_URL, params=params)
                
                # RenderのLogsで状況を確認するためのプリント（本番では消してもOK）
                print(f"--- Search Keyword: {keyword} ---")
                print(f"API Status Code: {res.status_code}")

                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            # 楽天APIはリストの中に辞書が入る特殊な構造なので、正確に抽出
                            info = h['hotel'][0]['hotelBasicInfo']
                            hotels.append(info)
                    else:
                        print("No hotels found in the response.")
                else:
                    # エラーが出た場合、詳細をログに出す
                    print(f"API Error Response: {res.text}")

            except Exception as e:
                print(f"Python Error: {str(e)}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

# Render用の起動設定
if __name__ == "__main__":
    # Renderから割り当てられるポート、なければ10000を使用
    port = int(os.environ.get("PORT", 10000))
    # 0.0.0.0で公開。debug=Falseが本番環境の推奨です。
    app.run(host="0.0.0.0", port=port, debug=False)
