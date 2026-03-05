import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# APIキー
RECRUIT_API_KEY = os.environ.get('RECRUIT_API_KEY')
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID')


@app.route('/', methods=['GET', 'POST'])
def index():
    hotels = []
    keyword = request.form.get('keyword', '').strip() if request.method == 'POST' else ""

    if keyword:

        print("検索キーワード:", keyword)

        # じゃらんAPI
        url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

        params = {
            "key": RECRUIT_API_KEY,
            "keyword": keyword,
            "count": 10,
            "format": "json"
        }

        try:
            res = requests.get(url, params=params, timeout=10)

            print("じゃらんAPIステータス:", res.status_code)

            if res.status_code == 200:

                data = res.json()

                print("じゃらんレスポンス:", data)

                results = data.get("results", {})
                available = int(results.get("results_available", 0))

                print("宿件数:", available)

                j_hotels = results.get("hotel", [])

                # 1件だけのとき
                if isinstance(j_hotels, dict):
                    j_hotels = [j_hotels]

                for h in j_hotels:

                    # 楽天価格
                    rakuten_price = "確認中"
                    rakuten_url = ""

                    if len(hotels) < 5:

                        r_params = {
                            "applicationId": RAKUTEN_APP_ID,
                            "affiliateId": RAKUTEN_AFFILIATE_ID,
                            "keyword": h['hotel_name'],
                            "hits": 1,
                            "format": "json"
                        }

                        try:
                            r_res = requests.get(
                                "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426",
                                params=r_params,
                                timeout=3
                            )

                            if r_res.status_code == 200:

                                r_data = r_res.json().get("hotels", [])

                                if r_data:
                                    r_info = r_data[0]['hotel'][0]['hotelBasicInfo']

                                    rakuten_price = f"¥{r_info.get('hotelMinCharge', '---')}"

                                    rakuten_url = (
                                        r_info.get("affiliateUrl")
                                        or r_info.get("hotelInformationUrl")
                                    )

                        except Exception as e:
                            print("楽天APIエラー:", e)

                    hotels.append({
                        "name": h.get("hotel_name"),
                        "image": h.get("hotel_image_sample_large"),
                        "display_distance": "キーワード検索",
                        "jalan_price": f"¥{h.get('sample_rate_from', '---')}",
                        "rakuten_price": rakuten_price,
                        "jalan_url": h.get("plan_list_url"),
                        "rakuten_url": rakuten_url
                    })

        except Exception as e:
            print("じゃらんAPIエラー:", e)

    return render_template("index.html", hotels=hotels, keyword=keyword)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
