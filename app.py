import os
import asyncio
import httpx
import math
import requests
from flask import Flask, render_template, request
from rapidfuzz import fuzz

app = Flask(__name__)

# 環境変数
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID")
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"
JALAN_API_URL = "https://webservice.recruit.co.jp/jalan/hotel/v1/"

# 沖縄スポット
DESTINATIONS = {
    "恩納村": {"lat": 26.5050, "lng": 127.8767},
    "美ら海水族館": {"lat": 26.6943, "lng": 127.8781},
    "那覇空港": {"lat": 26.2064, "lng": 127.6465},
    "国際通り": {"lat": 26.2155, "lng": 127.6853},
    "首里城": {"lat": 26.2170, "lng": 127.7195},
    "アメリカンビレッジ": {"lat": 26.3164, "lng": 127.7576},
    "万座毛": {"lat": 26.5050, "lng": 127.8500},
    "古宇利島": {"lat": 26.7020, "lng": 128.0200},
    "瀬長島ウミカジテラス": {"lat": 26.1748, "lng": 127.6461},
    "那覇駅": {"lat": 26.2125, "lng": 127.6792},
}

# 距離表示
def format_distance(m):
    if m is None:
        return None
    m = float(m)
    if m < 1000:
        return f"{int(m)}m"
    else:
        return f"{round(m/1000,2)}km"

# 距離計算
def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat2 or not lon2:
        return None

    R = 6371000
    rad_lat1 = math.radians(lat1)
    rad_lat2 = math.radians(lat2)
    dlat = rad_lat2 - rad_lat1
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(rad_lat1)*math.cos(rad_lat2)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


# じゃらんAPI
async def get_jalan_data(client, name):

    if not RECRUIT_API_KEY:
        return "---",""

    params = {
        "key": RECRUIT_API_KEY,
        "keyword": name,
        "format": "json",
        "count": 3
    }

    try:

        res = await client.get(JALAN_API_URL, params=params)

        if res.status_code == 200:

            data = res.json()

            if "results" in data and "hotel" in data["results"]:

                for hotel in data["results"]["hotel"]:

                    if fuzz.token_sort_ratio(name, hotel["hotelName"]) > 75:

                        price = hotel.get("sampleRateFrom")

                        return f"¥{price}" if price else "---", hotel["urls"]["pc"]

    except:
        pass

    return "---",""


@app.route("/", methods=["GET","POST"])
def index():

    hotels=[]
    keyword=""

    if request.method=="POST":

        keyword=request.form.get("keyword","").strip()

        params={
            "applicationId":RAKUTEN_APP_ID,
            "affiliateId":RAKUTEN_AFFILIATE_ID,
            "keyword":keyword,
            "format":"json",
            "hits":20
        }

        headers={
            "User-Agent":"Mozilla/5.0"
        }

        res=requests.get(RAKUTEN_API_URL,params=params,headers=headers)

        if res.status_code==200:

            data=res.json()

            if "hotels" in data:

                base_coords=DESTINATIONS.get(keyword)

                async def fetch_all():

                    async with httpx.AsyncClient() as client:

                        tasks=[]

                        for h in data["hotels"]:

                            name=h["hotel"][0]["hotelBasicInfo"]["hotelName"]

                            tasks.append(get_jalan_data(client,name))

                        return await asyncio.gather(*tasks)

                try:
                    jalan_results=asyncio.run(fetch_all())
                except:
                    jalan_results=[("---","")]*len(data["hotels"])

                for i,h in enumerate(data["hotels"]):

                    info=h["hotel"][0]["hotelBasicInfo"]

                    j_price,j_url=jalan_results[i]

                    lat=info.get("latitude")
                    lng=info.get("longitude")

                    display_dist=None

                    if base_coords and lat and lng:

                        raw=calculate_distance(
                            base_coords["lat"],
                            base_coords["lng"],
                            float(lat),
                            float(lng)
                        )

                        display_dist=format_distance(raw)

                    hotels.append({

                        "hotelName":info.get("hotelName"),
                        "hotelImageUrl":info.get("hotelImageUrl"),
                        "address1":info.get("address1"),
                        "hotelMinCharge":info.get("hotelMinCharge"),
                        "display_distance":display_dist,
                        "target_url":info.get("hotelInformationUrl"),
                        "jalan_price":j_price,
                        "jalan_url":j_url

                    })

    return render_template("index.html",hotels=hotels,keyword=keyword)


if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
