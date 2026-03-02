import requests

# ===== あなたの情報 =====
APPLICATION_ID = "99c6687c-934b-461a-91d2-cccac125bba8"
ACCESS_KEY = "pk_X0YMu5r1uH81LhQSx9jkv4w3yEcBaAQ9T1XvueirvEH"
REFERER_URL = "https://mysite-l8l0.onrender.com/"
# ========================

url = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

headers = {
    "Referer": REFERER_URL,
    "User-Agent": "Mozilla/5.0"
}

params = {
    "format": "json",
    "keyword": "沖縄",
    "applicationId": APPLICATION_ID,
    "accessKey": ACCESS_KEY
}

response = requests.get(url, headers=headers, params=params)

print("ステータス:", response.status_code)
print(response.text)
