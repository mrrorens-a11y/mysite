import sqlite3

def add_hotel_manual(rakuten_id, jalan_id, yahoo_id, name):
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT,
            rakuten_id TEXT UNIQUE,
            jalan_id TEXT,
            yahoo_id TEXT,
            address TEXT
        )
    ''')
    
    # データを登録（あなたが指定した通りの形式で保存します）
    cursor.execute('''
        INSERT OR REPLACE INTO hotels (rakuten_id, jalan_id, yahoo_id, hotel_name)
        VALUES (?, ?, ?, ?)
    ''', (str(rakuten_id), str(jalan_id), str(yahoo_id), name))
    
    conn.commit()
    conn.close()
    print(f"--- 登録完了 ---")
    print(f"じゃらんID: {jalan_id} で保存しました")

if __name__ == "__main__":
    # 指定の形式で実行
    add_hotel_manual("136206", "yad335007", "00902459", "ロイヤルビューホテル美ら海")
