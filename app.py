import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# IDが取れているかチェックするための変数
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2: return None
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    error_msg = "" # エラー表示用

    if request.method == 'POST':
        keyword = request.form.get('keyword')
        
        # IDチェック
        if not RAKUTEN_APP_ID:
            error_msg = "DEBUG: RAKUTEN_APP_IDがRender上で設定されていません。"
        
        if keyword and not error_msg:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 10
            }
            headers = {"referer": "https://mysite-l8l0.onrender.com/"}

            try:
                # 一番シンプルなキーワード検索でテスト
                res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=params, headers=headers, timeout=10)
                
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
                    else:
                        error_msg = f"DEBUG: 宿が見つかりませんでした。楽天の応答: {data.get('error_description', '不明なエラー')}"
                else:
                    error_msg = f"DEBUG: 楽天APIがエラーを返しました。ステータスコード: {res.status_code}"
            
            except Exception as e:
                error_msg = f"DEBUG: 通信中に例外が発生しました: {str(e)}"

    # index.htmlにerror_msgを渡すように修正（html側で表示されるようにします）
    return render_template('index.html', hotels=hotels, keyword=keyword, error_msg=error_msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
