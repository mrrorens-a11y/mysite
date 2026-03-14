import sqlite3
import requests
import time

RECRUIT_API_KEY = "518acb106b819a34"

def update_jalan_ids():
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, hotel_name, tel FROM hotels WHERE jalan_id IS NULL')
    rows = cursor.fetchall()
    
    print(f"未紐付けの宿: {len(rows)}件 を処理します...")

    for row in rows:
        db_id, name, tel = row
        # 数字だけを抽出
        tel_clean = "".join(filter(str.isdigit, tel))
        
        url = "https://webservice.recruit.co.jp/jalan/hotel/v1/"
        params = {
            "key": RECRUIT_API_KEY,
            "tel": tel_clean,
            "format": "json"
        }
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            if "results" in data and "hotel" in data["results"]:
                j_id = data["results"]["hotel"][0]["hotelId"]
                cursor.execute('UPDATE hotels SET jalan_id = ? WHERE id = ?', (j_id, db_id))
                print(f"[+] 成功: {name}")
            else:
                print(f"[x] 不一致: {name}")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"[!] エラー: {e}")
            
    conn.commit()
    conn.close()
    print("紐付け作業が完了しました。")

if __name__ == "__main__":
    update_jalan_ids()
