from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

RAKUTEN_APP_ID = "99c6687c-934b-461a-91d2-cccac125bba8"
RAKUTEN_ACCESS_KEY = "pk_d9C17gWx15sJvd3zfV6c1vXvKjrsSbd8rFSOOf1K0jY"  # ← これが accessKey
RAKUTEN_AFFILIATE_ID = "516c5cc9.1bfc6c7d.516c5cca.f7d5de3e"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    keyword = request.args.get("keyword")

    url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

    headers = {
        "X-Rakuten-Application-Id": RAKUTEN_APP_ID,
        "X-Rakuten-Access-Key": RAKUTEN_ACCESS_KEY
    }

    params = {
        "format": "json",
        "keyword": keyword,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "hits": 20
    }

    res = requests.get(url, headers=headers, params=params)
    return jsonify(res.json())

if __name__ == "__main__":
    app.run(debug=True)
