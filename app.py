import os
import requests
import math
from flask import Flask, render_template, request

app = Flask(__name__)

# 環境変数から各IDを取得
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_ACCESS_KEY = os.environ.get('RAKUTEN_ACCESS_KEY')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')

# 楽天APIのURL（キーワード検索）
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 緯度経度から2点間の距離(km)を計算する関数
def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return None
    R = 6371.0  # 地球の半径
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = ""
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }
            
            # 【重要】403エラーを防ぐためのヘッダー（成功している設定を維持）
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "origin": "https://mysite-l8l0.onrender.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "accept": "application/json"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if 'hotels' in data:
                        base_lat = None
                        base_lon = None
                        
                        for h in data['hotels']:
                            info = h['hotel'][0]['hotelBasicInfo']
                            
                            # 【修正ポイント】楽天APIのミリ秒単位の緯度経度を「度」に変換
                            # 3,600,000で割ることで、Googleマップ等と同じ形式になり、距離が正確になります
                            lat = float(info['latitude']) / 3600000
                            lon = float(info['longitude']) / 3600000
                            
                            # 一旦、1軒目の宿を基準点とする（後で「目的地特定機能」へ拡張予定）
                            if base_lat is None:
                                base_lat = lat
                                base_lon = lon

                            # 正しい数値で距離を計算
                            dist = calculate_distance(base_lat, base_lon, lat, lon)
                            
                            # 距離の表示テキストを作成
                            if dist is not None:
                                if dist < 0.03:  # 30m以内
                                    info['display_distance'] = "すぐ近く"
                                elif dist < 1.0:
                                    info['display_distance'] = f"{int(dist * 1000)}m"
                                else:
                                    info['display_distance'] = f"{round(dist, 1)}km"
                            else:
                                info['display_distance'] = ""

                            # アフィリエイトURLの設定
                            info['target_url'] = info.get('affiliateUrl') or info.get('hotelInformationUrl')
                            hotels.append(info)
            except Exception as e:
                print(f"DEBUG: Error: {e}")

    return render_template('index.html', hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
