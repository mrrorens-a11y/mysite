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
            # 【重要】URLの最後に「.json」を直接つけました。これで404は出せません。
            url = "https://webservice.recruit.co.jp/jalan/hotel/v1.json" 
            params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 10
                # "format": "json" はURLに含めたので不要になります
            }
            try:
                # 余計な末尾処理をせず、そのままリクエスト
                res = requests.get(url, params=params, timeout=10)
                
                api_status = f"Status: {res.status_code}"
                
                if res.status_code == 200:
                    data = res.json()
                    j_hotels = data.get('results', {}).get('hotel', [])
                    if j_hotels:
                        api_status += f" | ✅{len(j_hotels)}件の宿を表示中"
                        for jh in j_hotels:
                            hotels.append({
                                "name": jh.get('hotel_name'),
                                "image": jh.get('hotel_image_sample_large'),
                                "price": f"¥{jh.get('sample_rate_from', '---')}",
                                "url": jh.get('plan_list_url'),
                                "address": jh.get('address')
                            })
                    else:
                        api_status += " | ⚠️データが空です（キーは正常）"
                else:
                    # 404が出た場合、URLがどう作られたかヒントを表示
                    api_status += f" | ❌エラー内容: {res.text[:30]}"
                    
            except Exception as e:
                api_status = f"🔥接続失敗: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, api_status=api_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
