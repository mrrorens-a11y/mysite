import os
import requests
import sqlite3
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# 環境変数から取得
RAKUTEN_APP_ID       = os.environ.get("RAKUTEN_APP_ID", "").strip()
RAKUTEN_ACCESS_KEY   = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
SITE_URL             = os.environ.get("SITE_URL", "https://mysite-l8l0.onrender.com").strip()
RAKUTEN_API_URL      = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426"

# 【チェック】IDが読み込めているか画面に出す
if not RAKUTEN_APP_ID:
    print("[!] エラー: .env ファイルから RAKUTEN_APP_ID を読み込めませんでした。")
    print("    .env ファイルの書き方やファイル名（先頭にドットがあるか）を確認してください。")
else:
    # セキュリティのため、最初の4文字だけ表示
    print(f"[*] アプリIDを読み込みました: {RAKUTEN_APP_ID[:4]}****")

def collect_hotels(keyword):
    if not RAKUTEN_APP_ID: return # IDがなければ中止

    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()

    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey":     RAKUTEN_ACCESS_KEY,
        "affiliateId":   RAKUTEN_AFFILIATE_ID,
        "format":        "json",
        "keyword":       keyword,
        "hits":          15
    }

    headers = {
        "referer":    SITE_URL + "/",
        "origin":     SITE_URL,
        "user-agent": "Mozilla/5.0",
        "accept":     "application/json"
    }

    print(f"[*] 楽天API接続中... キーワード: {keyword}")
    try:
        res = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            count = 0
            for h in data.get("hotels", []):
                info = h["hotel"][0]["hotelBasicInfo"]
                name = info.get("hotelName")
                tel = info.get("telephoneNo")
                r_id = info.get("hotelNo")
                addr = (info.get("address1") or "") + (info.get("address2") or "")
                
                if tel:
                    cursor.execute('''
                        INSERT OR IGNORE INTO hotels (hotel_name, tel, rakuten_id, address)
                        VALUES (?, ?, ?, ?)
                    ''', (name, tel, str(r_id), addr))
                    count += 1
            conn.commit()
            print(f"[OK] 楽天から {count}件 保存しました！")
        else:
            print(f"[!] 失敗。Status: {res.status_code}, Msg: {res.text}")
    except Exception as e:
        print(f"[!] エラー: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    collect_hotels("箱根")
