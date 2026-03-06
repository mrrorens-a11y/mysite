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
    api_status = ""  # 調査用メッセージ
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
            params = {
                "key": RECRUIT_API_KEY,
                "keyword": keyword,
                "count": 5,
                "format": "json"
            }
            try:
                res = requests.get(url, params=params, timeout=10)
                # --- 調査開始 ---
                api_status = f"Status: {res.status_code} | "
                
                if res.status_code == 200:
                    data = res.json()
                    # もしエラーメッセージが含まれていたら表示
                    error = data.get('results', {}).get('error')
                    if error:
                        api_status += f"❌APIエラー: {error[0].get('message')}"
                    
                    j_list = data.get('results', {}).get('hotel', [])
                    if j_list:
                        api_status += f"✅{len(j_list)}件の宿を発見しました！"
                        for jh in j_list:
                            hotels.append({
                                "name": jh.get('hotel_name'),
                                "image": jh.get('hotel_image_sample_large'),
                                "price": f"¥{jh.get('sample_rate_from', '---')}",
                                "url": jh.get('plan_list_url'),
                                "address": jh.get('address')
                            })
                    else:
                        api_status += "⚠️宿が0件です。キーワードやキー設定を確認してください。"
                else:
                    api_status += f"❌通信失敗: {res.text[:100]}"
                    
            except Exception as e:
                api_status = f"🔥システムエラー: {str(e)}"

    return render_template('index.html', hotels=hotels, keyword=keyword, api_status=api_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
