import os
import asyncio
import httpx
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# --- 環境変数設定 ---
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

# APIエンドポイント
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

def format_distance(m):
    """
    距離を1000m未満は'm'、それ以上は'km'で分かりやすく表示
    """
    if m is None or m == "": return ""
    try:
        m = float(m)
        return f"{int(m)}m" if m < 1000 else f"{round(m/1000, 1)}km"
    except ValueError:
        return ""

async def get_jalan_data(client, r_name):
    """
    じゃらんAPIを非同期で叩き、楽天のホテル名と照合して料金を返す
    """
    if not RECRUIT_API_KEY:
        return "---", ""
    
    j_params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 5
    }
    
    try:
        # タイムアウトを5秒に設定し、レスポンスを待つ
        res = await client.get(JALAN_API_URL, params=j_params, timeout=5.0)
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                for j_hotel in j_data["results"]["hotel"]:
                    # ホテル名の類似度をチェック（75%以上の一致で同一とみなす）
                    score = fuzz.token_sort_ratio(r_name, j_hotel["hotelName"])
                    if score > 75:
                        price = j_hotel.get("sampleRateFrom")
                        url = j_hotel.get("urls", {}).get("pc")
                        return (f"¥{price}" if price else "---"), url
    except Exception as e:
        print(f"Async Jalan Error for {r_name}: {e}")
    
    return "---", ""

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 1. 楽天APIリクエスト（ベースとなるホテルリストを取得）
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "format": "json",
                "keyword": keyword,
                "hits": 15
            }
            # Render等で動かす際のReferer制限対策（必要に応じて）
            headers = {
                "referer": "https://mysite-l8l0.onrender.com/",
                "user-agent": "Mozilla/5.0"
            }

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    
                    if "hotels" in data:
                        # --- 【非同期処理の実行】 ---
                        async def fetch_all_jalan():
                            async with httpx.AsyncClient() as client:
                                # 全ホテルのじゃらん検索を「一斉に」開始
                                tasks = [
                                    get_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) 
                                    for h in data["hotels"]
                                ]
                                return await asyncio.gather(*tasks)

                        # 非同期ループを回して結果を取得
                        jalan_results = asyncio.run(fetch_all_jalan())

                        # 楽天データとじゃらんの結果を統合
                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            j_price, j_url = jalan_results[idx]
                            
                            item = {
                                "hotelName": info.get("hotelName"),
                                "hotelImageUrl": info.get("hotelImageUrl"),
                                "address1": info.get("address1", ""),
                                "address2": info.get("address2", ""),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "display_distance": format_distance(info.get("searchDistance")),
                                "target_url": info.get("affiliateUrl") or info.get("hotelInformationUrl"),
                                "jalan_price": j_price,
                                "jalan_url": j_url
                            }
                            hotels.append(item)
            except Exception as e:
                print(f"Rakuten API Error: {e}")
    
    return render_template("index.html", hotels=hotels, keyword=keyword)

if __name__ == "__main__":
    # Render等の環境に合わせてポート番号を取得
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
