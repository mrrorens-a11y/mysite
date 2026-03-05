import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# 新しいキーをRenderのEnvironment Variablesで更新してください
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""
    debug_msg = ""
    
    if keyword:
        # 【重要】2026年最新：スラッシュなしのURL
        url = "https://webservice.recruit.co.jp/jalan/hotel/v1"
        params = {
            "key": RECRUIT_API_KEY,
            "keyword": keyword,
            "count": 10,
            "format": "json"
        }
        
        try:
            # タイムアウトを少し長めの15秒に設定
            res = requests.get(url, params=params, timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                # じゃらんAPIのデータ構造を深く掘る
                results = data.get('results', {})
                j_hotels = results.get('hotel', [])
                
                if not j_hotels:
                    debug_msg = f"「{keyword}」で見つかりませんでした。別のキーワード（例：沖縄）を試してください。"
                else:
                    if isinstance(j_hotels, dict): j_hotels = [j_hotels]
                    for h in j_hotels:
                        hotels.append({
                            "name": h.get('hotel_name'),
                            "image": h.get('hotel_image_sample_large'),
                            "display_distance": "📍 検索成功",
                            "jalan_price": f"¥{h.get('sample_rate_from', '---')}",
                            "jalan_url": h.get('plan_list_url')
                        })
            else:
                # 404が出た場合、URLが間違っている可能性を通知
                debug_msg = f"じゃらん側からエラーが返りました (Status: {res.status_code})"
                
        except Exception as e:
            debug_msg = f"通信エラー: {str(e)}"
            
    return render_template('index.html', hotels=hotels, keyword=keyword, debug_msg=debug_msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
