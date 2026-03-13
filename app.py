import os
import asyncio
import httpx
import requests
import urllib.parse
from flask import Flask, render_template, request

app = Flask(__name__)

# ── 環境変数 ──────────────────────────────────────────
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
RECRUIT_API_KEY      = os.environ.get("RECRUIT_API_KEY", "")
# バリューコマース スイッチリンクのベースURL (Renderの環境変数に設定)
VC_SWITCH_LINK_BASE  = os.environ.get("VC_SWITCH_LINK", "")

# 起動時チェック
print(f"[INIT] RAKUTEN_APP_ID: {'YES' if RAKUTEN_APP_ID else '*** MISSING ***'}")
print(f"[INIT] VC_SWITCH_LINK: {'YES' if VC_SWITCH_LINK_BASE else 'not set'}")

RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"

# ── ユーティリティ関数 ─────────────────────────────────

def wrap_vc(url: str) -> str:
    """URLをバリューコマース スイッチリンクでラップする"""
    if not VC_SWITCH_LINK_BASE or not url:
        return url
    # 末尾にエンコードしたURLを結合
    return VC_SWITCH_LINK_BASE + urllib.parse.quote(url, safe="")

def format_distance(dist_km):
    """0.5km を 500m と表示するロジック"""
    try:
        d = float(dist_km)
        if d < 1:
            return f"{int(d * 1000)}m"
        return f"{d}km"
    except (ValueError, TypeError):
        return dist_km

async def fetch_jalan_data(client, r_name):
    """じゃらんAPIから価格とURLを取得"""
    encoded_name = urllib.parse.quote(r_name)
    fallback_url = f"https://www.jalan.net/fwSearch.do?fw={encoded_name}"
    if not RECRUIT_API_KEY:
        return "---", fallback_url

    j_params = {
        "key": RECRUIT_API_KEY,
        "keyword": r_name,
        "format": "json",
        "count": 1
    }
    try:
        res = await client.get(
            "https://webservice.recruit.co.jp/jalan/hotel/v1/",
            params=j_params,
            timeout=3.0
        )
        if res.status_code == 200:
            j_data = res.json()
            if "results" in j_data and "hotel" in j_data["results"]:
                j_hotel = j_data["results"]["hotel"][0]
                price = j_hotel.get("sampleRateFrom")
                url = j_hotel.get("urls", {}).get("pc")
                return (f"¥{price}" if price else "---"), (url or fallback_url)
    except Exception:
        pass
    return "---", fallback_url

# ── ルート ──────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    hotels = []
    keyword = ""
    error_msg = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if not RAKUTEN_APP_ID:
            error_msg = "楽天APIキーが設定されていません。"
            return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)

        if keyword:
            # 楽天APIパラメータ（accessKeyは含めない）
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "format":        "json",
                "keyword":       keyword,
                "hits":          10,
            }
            if RAKUTEN_AFFILIATE_ID:
                params["affiliateId"] = RAKUTEN_AFFILIATE_ID

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)
                
                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:
                        # 並列で他社データを取得
                        async def get_all_prices():
                            async with httpx.AsyncClient() as client:
                                tasks = [fetch_jalan_data(client, h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")) for h in data["hotels"]]
                                return await asyncio.gather(*tasks)

                        try:
                            jalan_results = asyncio.run(get_all_prices())
                        except Exception:
                            jalan_results = [("---", f"https://www.jalan.net/fwSearch.do?fw={urllib.parse.quote(h['hotel'][0]['hotelBasicInfo'].get('hotelName',''))}") for h in data["hotels"]]

                        for idx, h in enumerate(data["hotels"]):
                            info = h["hotel"][0]["hotelBasicInfo"]
                            name = info.get("hotelName", "")
                            
                            # 距離のフォーマット（楽天の 'nearestStation' などから距離情報がある場合）
                            # 今回は例として 'searchStep' 等がないため項目準備のみ
                            dist_raw = info.get("hotelMinCharge", "") # ダミー用。本来は距離プロパティを入れる

                            # URL生成とVCラップ
                            rakuten_raw_url = info.get("affiliateUrl") or info.get("hotelInformationUrl", "")
                            rakuten_url = wrap_vc(rakuten_raw_url)

                            hotels.append({
                                "hotelName":      name,
                                "hotelImageUrl":  info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "target_url":     rakuten_url,
                                "jalan_price":    jalan_results[idx][0],
                                "jalan_url":      wrap_vc(jalan_results[idx][1]), # 他社も収益化するならwrap
                                "yahoo_url":      wrap_vc(f"https://travel.yahoo.co.jp/search/?stext={urllib.parse.quote(name)}"),
                                "booking_url":    f"https://www.booking.com/searchresults.ja.html?ss={urllib.parse.quote(name)}",
                            })
                    else:
                        error_msg = "宿が見つかりませんでした。"
                else:
                    error_msg = f"楽天APIエラー: {res.status_code}"

            except Exception as e:
                print(f"[ERROR] {e}")
                error_msg = "通信エラーが発生しました。"

    return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
