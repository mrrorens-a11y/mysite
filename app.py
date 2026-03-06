import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# RenderのEnvironment Variablesの並び順に合わせました
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""
    debug_msg = ""
    
    if keyword:
        # 【重要】404回避：末尾にスラッシュを入れないURL形式
        j_url = "https://webservice.recruit.co.jp/jalan/hotel/v1"
        j_params = {
            "key": RECRUIT_API_KEY,
            "keyword": keyword,
            "count": 10,
            "format": "json"
        }
        
        try:
            # APIキーが空でないかチェック
            if not RECRUIT_API_KEY:
                debug_msg = "RECRUIT_API_KEYが設定されていません。"
            else:
                j_res = requests.get(j_url, params=j_params, timeout=10)
                
                if j_res.status_code == 200:
                    data = j_res.json()
                    results = data.get('results', {})
                    
                    # APIキーが間違っている場合、200でも中身にエラーが入ることがあります
                    if 'error' in results:
                        debug_msg = f"APIエラー: {results['error'][0].get('message')}"
                    else:
                        j_list = results.get('hotel', [])
                        if isinstance(j_list, dict): j_list = [j_list]
                        
                        for h in j_list:
                            # 楽天検索
                            r_price = "確認中"
                            r_url = "#"
                            r_params = {
                                "applicationId": RAKUTEN_APP_ID,
                                "affiliateId": RAKUTEN_AFFILIATE_ID,
                                "keyword": h.get('hotel_name'),
                                "hits": 1,
                                "format": "json"
                            }
                            try:
                                r_res = requests.get("https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", params=r_params, timeout=3)
                                if r_res.status_code == 200:
                                    r_data = r_res.json().get('hotels', [])
                                    if r_data:
                                        r_info = r_data[0]['hotel'][0]['hotelBasicInfo']
                                        r_price = f"¥{r_info.get('hotelMinCharge', '---')}"
                                        r_url = r_info.get('affiliateUrl') or r_info.get('hotelInformationUrl')
                            except: pass

                            hotels.append({
                                "name": h.get('hotel_name'),
                                "image": h.get('hotel_image_sample_large'),
                                "j_price": f"¥{h.get('sample_rate_from', '---')}",
                                "j_url": h.get('plan_list_url'),
                                "r_price": r_price,
                                "r_url": r_url
                            })
                else:
                    # ここで404の理由を特定
                    debug_msg = f"じゃらんAPIエラー: {j_res.status_code} (URLまたはキー設定の不備)"
                
        except Exception as e:
            debug_msg = f"システムエラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, debug_msg=debug_msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
