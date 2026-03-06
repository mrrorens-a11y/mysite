import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    api_status = "" 
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # 【重要】URLの末尾にスラッシュを入れず、json形式を明示
            url = "https://webservice.recruit.co.jp/jalan/hotel/v1" 
            params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 10,
                "format": "json"  # 小文字でjson
            }
            try:
                # タイムアウトを少し長めの15秒に設定（迷いを防ぐ）
                res = requests.get(url, params=params, timeout=15)
                
                api_status = f"Status: {res.status_code}"
                
                if res.status_code == 200:
                    data = res.json()
                    # 階層を深くチェック
                    results = data.get('results', {})
                    j_hotels = results.get('hotel', [])
                    
                    if j_hotels:
                        api_status += f" | ✅{len(j_hotels)}件ヒット！"
                        for jh in j_hotels:
                            hotels.append({
                                "name": jh.get('hotel_name'),
                                "image": jh.get('hotel_image_sample_large'),
                                "price": f"¥{jh.get('sample_rate_from', '---')}",
                                "url": jh.get('plan_list_url'),
                                "address": jh.get('address')
                            })
                    else:
                        api_status += " | ⚠️宿が見つかりません（APIは正常応答）"
                else:
                    # 404の時に、APIが何を言っているか中身を少し覗く
                    api_status += f" | ❌詳細: {res.text[:50]}"
                    
            except Exception as e:
                api_status = f"🔥接続エラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, api_status=api_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
