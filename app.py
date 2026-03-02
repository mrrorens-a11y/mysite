from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

RAKUTEN_APP_ID = "99c6687c-934b-461a-91d2-cccac125bba8"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    keyword = request.args.get("keyword")

    url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

    params = {
        "format": "json",
        "keyword": keyword,
        "applicationId": RAKUTEN_APP_ID,
        "hits": 20
    }

    res = requests.get(url, params=params)

    print("========== 楽天からのレスポンス ==========")
    print(res.status_code)
    print(res.json())
    print("===========================================")

    return jsonify(res.json())

if __name__ == "__main__":
    app.run(debug=True)
