from geopy.distance import geodesic

# 目的地：沖縄美ら海水族館
DEST_COORD = (26.694542346577375, 127.8779368039277)

# 宿のリスト
hotels = [
    {"name": "アーユルウェルネスリゾート&スパOkinawa", "lat": 26.70039133662295, "lng": 127.89790949277831},
    {"name": "ロイヤルビューホテル美ら海", "lat": 26.695201816996104, "lng": 127.87945568633229},
    {"name": "オリオンホテル モトブ リゾート＆スパ", "lat": 26.69877810920093, "lng": 127.87951246698786}
]

def format_dist(km):
    if km < 1:
        return f"{int(km * 1000)}m"
    else:
        return f"{round(km, 1)}km"

# 各宿に距離データを追加
for h in hotels:
    dist = geodesic(DEST_COORD, (h["lat"], h["lng"])).km
    h["distance_km"] = dist
    h["display_dist"] = format_dist(dist)

# 「近い順」に並び替え
sorted_hotels = sorted(hotels, key=lambda x: x["distance_km"])

print(f"\n★美ら海水族館から【近い順】のリスト★\n")
for i, h in enumerate(sorted_hotels, 1):
    print(f"{i}位: {h['name']} ({h['display_dist']})")
