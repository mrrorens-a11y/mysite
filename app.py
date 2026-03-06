import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Render環境変数（ここは設定済み）
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")

# 最もエラーが出にくい標準の窓口を使用
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            # 必須項目だけに絞り、確実に文字列として渡す
            params = {
                "applicationId": str(RAKUTEN_APP_ID).strip(),
                "affiliateId": str(RAKUTEN_AFFILIATE_ID).strip(),
                "format": "json",
                "keyword": keyword,
                "hits": 20
            }

            try:
                # 【成功の鍵】headersを一切送らず、API側に「標準的なプログラムからのアクセス」と認識させます
                res = requests.get(
                    RAKUTEN_API_URL,
                    params=params,
                    timeout=10
                )

                print(f"DEBUG STATUS: {res.status_code}")

                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        for h in data["hotels"]:
                            info = h["hotel"][0]["hotelBasicInfo"]
                            # アフィリエイトURL（hb.afl...）を優先的に取得
                            info["target_url"] = info.get("affiliateUrl") or info.get("hotelInformationUrl")
                            hotels.append(info)
                else:
                    # ここでエラーが出た場合、何が足りないか楽天が教えてくれます
                    print(f"DEBUG API ERROR DETAIL: {res.text}")

            except Exception as e:
                print(f"DEBUG SYSTEM ERROR: {e}")

    return render_template(
        "index.html",
        hotels=hotels,
        keyword=keyword
    )

if __name__ == "__main__":
    # Renderのポート検出エラーを完全に防ぐ設定
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
