import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数から取得
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 【重要】収益化エラーを避けるため、最も汎用的な標準エンドポイントを使用
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # パラメータを最小限に絞る（accessKeyを含めると400エラーが出るケースが多いため）
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }

            try:
                # ドメイン制限エラーを避けるため、headersを空（自動）にしてリクエスト
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            # 収益化用URLを格納
                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                else:
                    # ここでエラー内容を詳しくログに出す
                    print(f"DEBUG API Error Detail: {res.status_code} - {res.text}")
            except Exception as e:
                print(f"DEBUG System Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    # Renderの推奨ポート10000をデフォルトに設定
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
