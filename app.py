import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数から「じゃらんキー」を取得
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # --- 🍊 じゃらんAPIだけで検索 ---
            url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
            params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 20, # たっぷり20件
                "format": "json"
            }
            try:
                res = requests.get(url, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    j_list = data.get('results', {}).get('hotel', [])
                    for jh in j_list:
                        hotels.append({
                            "name": jh.get('hotel_name'),
                            "image": jh.get('hotel_image_sample_large'),
                            "price": f"¥{jh.get('sample_rate_from', '---')}",
                            "url": jh.get('plan_list_url'), # じゃらんの予約ページ
                            "address": jh.get('address', '住所情報なし'),
                            "site": "Jalan"
                        })
            except Exception as e:
                print(f"DEBUG Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
