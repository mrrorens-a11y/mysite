import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Renderの環境変数
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    api_status = "" 
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # 修正ポイント：URLの末尾を確実にAPIが受け取れる形にしました
            url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
            params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 10,
                "format": "json" # ここでjsonを指定
            }
            try:
                # 404を防ぐために、あえて最後にスラッシュを入れない、またはパラメータを厳密に送ります
                res = requests.get(url.rstrip('/'), params=params, timeout=10)
                
                api_status = f"Status: {res.status_code}"
                
                if res.status_code == 200:
                    data = res.json()
                    # じゃらん特有のデータ構造（results -> hotel）を正しく解析
                    j_hotels = data.get('results', {}).get('hotel', [])
                    if j_hotels:
                        for jh in j_hotels:
                            hotels.append({
                                "name": jh.get('hotel_name'),
                                "image": jh.get('hotel_image_sample_large'),
                                "price": f"¥{jh.get('sample_rate_from', '---')}",
                                "url": jh.get('plan_list_url'),
                                "address": jh.get('address')
                            })
                    else:
                        api_status += " | ⚠️宿が0件です（キーワードを変えてみてください）"
                else:
                    api_status += f" | ❌通信失敗（URLまたはキーの不備）"
                    
            except Exception as e:
                api_status = f"🔥エラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, api_status=api_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
