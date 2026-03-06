import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # 1. まずは「楽天」でベースの宿リストを作る
            r_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
            try:
                r_res = requests.get(r_url, params={
                    "applicationId": RAKUTEN_APP_ID,
                    "format": "json",
                    "keyword": keyword,
                    "hits": 10
                }, timeout=5)
                
                if r_res.status_code == 200:
                    r_data = r_res.json()
                    for h in r_data.get('hotels', []):
                        info = h['hotel'][0]['hotelBasicInfo']
                        h_name = info['hotelName']
                        
                        # --- ステップ2: 楽天で見つけた宿名で「じゃらん」にピンポイントで聞く ---
                        j_price = "設定なし"
                        j_url = None
                        
                        if RECRUIT_API_KEY:
                            try:
                                # 宿名で検索（完全一致に近いものを探すため1件だけ取得）
                                j_res = requests.get("https://webservice.recruit.co.jp/jalan/hotel/v1/", params={
                                    "key": RECRUIT_API_KEY,
                                    "keyword": h_name, 
                                    "count": 1,
                                    "format": "json"
                                }, timeout=3)
                                
                                if j_res.status_code == 200:
                                    j_data = j_res.json()
                                    j_list = j_data.get('results', {}).get('hotel', [])
                                    if j_list:
                                        # 宿名の一部が一致しているか簡易チェック
                                        if j_list[0]['hotel_name'][:5] in h_name:
                                            j_price = f"¥{j_list[0].get('sample_rate_from', '---')}"
                                            j_url = j_list[0].get('plan_list_url')
                            except: pass # じゃらんでエラーが起きても楽天は守る

                        # 楽天とじゃらんのデータを1つのカードにまとめる（ステップ3）
                        hotels.append({
                            "name": h_name,
                            "image": info['hotelImageUrl'],
                            "r_price": f"¥{info.get('hotelMinCharge', '---')}",
                            "r_url": info.get('affiliateUrl') or info.get('hotelInformationUrl'),
                            "j_price": j_price,
                            "j_url": j_url
                        })
            except Exception as e:
                print(f"Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
