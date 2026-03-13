import os
import asyncio
import httpx
import requests
import urllib.parse
from flask import Flask, render_template, request

app = Flask(__name__)

# ── 環境変数 ──────────────────────────────────────────────────────
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
RECRUIT_API_KEY      = os.environ.get("RECRUIT_API_KEY", "").strip()
VC_SWITCH_LINK_BASE  = os.environ.get("VC_SWITCH_LINK", "").strip()

# ── 起動時チェック ────────────────────────────────────────────────
print("=" * 60)
print(f"[INIT] RAKUTEN_APP_ID     : {'SET ('+str(len(RAKUTEN_APP_ID))+' chars)' if RAKUTEN_APP_ID else '*** MISSING ***'}")
print(f"[INIT] RAKUTEN_ACCESS_KEY : {'SET ('+str(len(RAKUTEN_ACCESS_KEY))+' chars)' if RAKUTEN_ACCESS_KEY else '*** MISSING ***'}")
print(f"[INIT] RAKUTEN_AFFILIATE_ID: {'SET' if RAKUTEN_AFFILIATE_ID else 'not set (optional)'}")
print("=" * 60)

# ── 新APIドメイン（2026年2月移行済み）────────────────────────────
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"


def wrap_vc(url: str) -> str:
    """URLをバリューコマース スイッチリンクでラップ"""
    if not VC_SWITCH_LINK_BASE or not url:
        return url
    return VC_SWITCH_LINK_BASE + urllib.parse.quote(url, safe="")


async def fetch_jalan_data(client, r_name):
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
                url   = j_hotel.get("urls", {}).get("pc")
                return (f"¥{price}" if price else "---"), (url or fallback_url)
    except Exception:
        pass
    return "---", fallback_url


@app.route("/", methods=["GET", "POST"])
def index():
    hotels    = []
    keyword   = ""
    error_msg = ""

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY:
            error_msg = "RAKUTEN_APP_ID または RAKUTEN_ACCESS_KEY が未設定です。"
            return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)

        if keyword:
            # ── 新API パラメータ ──────────────────────────────────
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey":     RAKUTEN_ACCESS_KEY,   # 新APIでは必須
                "format":        "json",
                "keyword":       keyword,
                "hits":          10,
            }
            if RAKUTEN_AFFILIATE_ID:
                params["affiliateId"] = RAKUTEN_AFFILIATE_ID

            # ── 新API認証ヘッダー（Bearer形式）──────────────────
            headers = {
                "Authorization": f"Bearer {RAKUTEN_ACCESS_KEY}",
            }

            print(f"[API] Calling: {RAKUTEN_API_URL}")
            print(f"[API] keyword='{keyword}'")

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)

                print(f"[API] Status: {res.status_code}")
                if res.status_code != 200:
                    print(f"[API] Response: {res.text[:300]}")

                if res.status_code == 200:
                    data = res.json()
                    if "hotels" in data:

                        async def get_all_prices():
                            async with httpx.AsyncClient() as client:
                                tasks = [
                                    fetch_jalan_data(
                                        client,
                                        h["hotel"][0]["hotelBasicInfo"].get("hotelName", "")
                                    )
                                    for h in data["hotels"]
                                ]
                                return await asyncio.gather(*tasks)

                        try:
                            jalan_results = asyncio.run(get_all_prices())
                        except Exception:
                            jalan_results = [
                                (
                                    "---",
                                    f"https://www.jalan.net/fwSearch.do?fw="
                                    f"{urllib.parse.quote(h['hotel'][0]['hotelBasicInfo'].get('hotelName', ''))}"
                                )
                                for h in data["hotels"]
                            ]

                        for idx, h in enumerate(data["hotels"]):
                            info     = h["hotel"][0]["hotelBasicInfo"]
                            name     = info.get("hotelName", "")
                            enc_name = urllib.parse.quote(name)

                            rakuten_raw_url = (
                                info.get("affiliateUrl")
                                or info.get("hotelInformationUrl", "")
                            )
                            rakuten_url = wrap_vc(rakuten_raw_url)

                            hotels.append({
                                "hotelName":      name,
                                "hotelImageUrl":  info.get("hotelImageUrl"),
                                "hotelMinCharge": info.get("hotelMinCharge"),
                                "target_url":     rakuten_url,
                                "jalan_price":    jalan_results[idx][0],
                                "jalan_url":      jalan_results[idx][1],
                                "yahoo_url":      f"https://travel.yahoo.co.jp/search/?stext={enc_name}",
                                "booking_url":    f"https://www.booking.com/searchresults.ja.html?ss={enc_name}",
                            })
                    else:
                        error_msg = "該当する宿が見つかりませんでした。"
                        print(f"[API] No hotels. Response keys: {list(data.keys())}")
                else:
                    error_msg = f"楽天APIエラー ({res.status_code}): {res.text[:200]}"

            except Exception as e:
                print(f"[ERROR] {e}")
                error_msg = "通信エラーが発生しました。"

    return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
