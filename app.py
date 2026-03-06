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
            # URLはこれで確定です
            url = "https://webservice.recruit.co.jp/jalan/hotel/v1/" 
            params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 10,
                "format": "json"
            }
            # 【重要】リクルートに「ブラウザからのアクセスだよ」と思わせるヘッダー
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://mysite-l8l0.onrender.com/"
            }
            try:
                res = requests.get(url, params=params, headers=headers, timeout=10)
                
                api_status = f"Status: {res.status_code}"
                
                if res.status_code == 200:
                    data = res.json()
                    j_hotels = data.get('results', {}).get('hotel', [])
                    if j_hotels:
                        api_status += f" | ✅成功！{len(j_hotels)}件表示"
                        for jh in j_hotels:
                            hotels.append({
                                "name": jh.get('hotel_name'),
                                "image": jh.get('hotel_image_sample_large'),
                                "price": f"¥{jh.get('sample_rate_from', '---')}",
                                "url": jh.get('plan_list_url'),
                                "address": jh.get('address')
                            })
                    else:
                        api_status += " | ⚠️データなし（キーワード不適合）"
                else:
                    # 403の時、何が拒否されたかログに出す
                    api_status += f" | ❌拒否されました (403)"
                    
            except Exception as e:
                api_status = f"🔥接続エラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, api_status=api_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
