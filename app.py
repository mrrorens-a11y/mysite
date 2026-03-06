import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    debug_msg = "" # 何が起きたか貯める変数
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            # --- 1. 楽天チェック ---
            r_url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
            r_params = {
                "applicationId": RAKUTEN_APP_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 5
            }
            try:
                r_res = requests.get(r_url, params=r_params, timeout=10)
                r_data = r_res.json()
                if 'hotels' in r_data:
                    for h in r_data['hotels']:
                        info = h['hotel'][0]['hotelBasicInfo']
                        hotels.append({"name": info['hotelName'], "site": "Rakuten", "price": info['hotelMinCharge'], "url": info['hotelInformationUrl'], "image": info['hotelImageUrl']})
                    debug_msg += f"✅楽天: {len(r_data['hotels'])}件発見 "
                else:
                    debug_msg += f"❌楽天: 宿が見つかりません(Code:{r_res.status_code}) "
            except Exception as e:
                debug_msg += f"⚠️楽天エラー: {str(e)} "

            # --- 2. じゃらんチェック ---
            j_url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
            j_params = {"key": RECRUIT_API_KEY, "keyword": keyword, "count": 5, "format": "json"}
            try:
                j_res = requests.get(j_url, params=j_params, timeout=10)
                j_data = j_res.json()
                j_list = j_data.get('results', {}).get('hotel', [])
                if j_list:
                    for jh in j_list:
                        hotels.append({"name": jh['hotel_name'], "site": "Jalan", "price": jh['sample_rate_from'], "url": jh['plan_list_url'], "image": jh['hotel_image_sample_large']})
                    debug_msg += f"✅じゃらん: {len(j_list)}件発見"
                else:
                    debug_msg += f"❌じゃらん: 宿が見つかりません(Code:{j_res.status_code})"
            except Exception as e:
                debug_msg += f"⚠️じゃらんエラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, debug_msg=debug_msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
