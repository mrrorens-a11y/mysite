import os
import asyncio
import httpx
import requests
import urllib.parse
from flask import Flask, render_template, request

app = Flask(__name__)

# ── 環境変数（.strip()で余分なスペース・改行を除去）──────────────
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
RECRUIT_API_KEY      = os.environ.get("RECRUIT_API_KEY", "").strip()
VC_SWITCH_LINK_BASE  = os.environ.get("VC_SWITCH_LINK", "").strip()

# ── 起動時に全変数をログ出力（値の先頭4文字だけ表示して確認）──
print("=" * 50)
print(f"[INIT] RAKUTEN_APP_ID     : '{RAKUTEN_APP_ID[:4]}...' len={len(RAKUTEN_APP_ID)}" if RAKUTEN_APP_ID else "[INIT] RAKUTEN_APP_ID     : *** MISSING ***")
print(f"[INIT] RAKUTEN_ACCESS_KEY : '{RAKUTEN_ACCESS_KEY[:4]}...' len={len(RAKUTEN_ACCESS_KEY)}" if RAKUTEN_ACCESS_KEY else "[INIT] RAKUTEN_ACCESS_KEY : (not set)")
print(f"[INIT] RAKUTEN_AFFILIATE_ID: '{RAKUTEN_AFFILIATE_ID[:4]}...' len={len(RAKUTEN_AFFILIATE_ID)}" if RAKUTEN_AFFILIATE_ID else "[INIT] RAKUTEN_AFFILIATE_ID: (not set)")
print("=" * 50)

RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"


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

        if not RAKUTEN_APP_ID:
            error_msg = "RAKUTEN_APP_ID が未設定です。Render環境変数を確認してください。"
            return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)

        if keyword:
            # ── パラメータ構築 ──────────────────────────────
            params = {
                "applicationId": RAKUTEN_APP_ID,
                "format":        "json",
                "keyword":       keyword,
                "hits":          10,
            }
            # accessKey がある場合のみ追加
            if RAKUTEN_ACCESS_KEY:
                params["accessKey"] = RAKUTEN_ACCESS_KEY

            # affiliateId がある場合のみ追加
            if RAKUTEN_AFFILIATE_ID:
                params["affiliateId"] = RAKUTEN_AFFILIATE_ID

            # ── デバッグ：送信パラメータをログ出力 ──────────
            print(f"[API] keyword='{keyword}'")
            print(f"[API] applicationId='{params['applicationId']}' (len={len(params['applicationId'])})")
            print(f"[API] accessKey set: {'YES' if 'accessKey' in params else 'NO'}")
            print(f"[API] affiliateId set: {'YES' if 'affiliateId' in params else 'NO'}")

            try:
                res = requests.get(RAKUTEN_API_URL, params=params, timeout=10)

                print(f"[API] Status: {res.status_code}")
                print(f"[API] Response: {res.text[:500]}")

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
                        print(f"[API] No hotels in response. Keys: {list(data.keys())}")
                else:
                    error_msg = f"楽天APIエラー ({res.status_code}): {res.text[:200]}"

            except Exception as e:
                print(f"[ERROR] {e}")
                error_msg = "通信エラーが発生しました。"

    return render_template("index.html", hotels=hotels, keyword=keyword, error_msg=error_msg)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
