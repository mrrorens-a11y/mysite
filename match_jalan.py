import sqlite3
import requests
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()
RECRUIT_API_KEY = os.environ.get("RECRUIT_API_KEY")

def match_jalan():
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, hotel_name, tel FROM hotels WHERE jalan_id IS NULL')
    rows = cursor.fetchall()
    
    if not rows:
        print("[!] 処理するデータがありません。")
        conn.close()
        return

    print(f"[*] {len(rows)}件の宿をチェックします...")

    for row in rows:
        db_id, name, tel = row
        tel_clean = re.sub(r'\D', '', tel)
        
        url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
        params = {
            "key": RECRUIT_API_KEY,
            "tel": tel_clean,
            "format": "json"
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            
            # ステータスコードが200（成功）以外なら原因を表示
            if res.status_code != 200:
                print(f"[!] 通信失敗: {name}")
                print(f"    ステータス: {res.status_code}")
                print(f"    エラー内容: {res.text[:100]}")
                continue

            data = res.json()
            if "results" in data and "hotel" in data["results"]:
                j_id = data["results"]["hotel"][0]["hotelId"]
                cursor.execute('UPDATE hotels SET jalan_id = ? WHERE id = ?', (j_id, db_id))
                print(f"[Match] {name} -> {j_id}")
            else:
                print(f"[No Match] {name} (じゃらんに未登録の可能性があります)")
            
            time.sleep(0.5) # 負荷軽減のために少し長めに待機
            
        except Exception as e:
            print(f"[Error] {name}: {e}")
            
    conn.commit()
    conn.close()
    print("[完了] 作業が終わりました！")

if __name__ == "__main__":
    match_jalan()
