import sqlite3

def add_hotel_manual(rakuten_id, jalan_id, yahoo_id, name):
    # tomarun.db に接続（なければ自動で作られます）
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    
    # テーブルがまだない場合に備えて作成
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
    
    # データを登録、すでにある場合は更新（REPLACE）
    cursor.execute('''
        INSERT OR REPLACE INTO hotels (rakuten_id, jalan_id, yahoo_id, hotel_name)
        VALUES (?, ?, ?, ?)
    ''', (str(rakuten_id), str(jalan_id), str(yahoo_id), name))
    
    conn.commit()
    conn.close()
    print(f"--- 登録完了 ---")
    print(f"宿名: {name}")
    print(f"楽天ID: {rakuten_id} -> じゃらんID: {jalan_id}, YahooID: {yahoo_id}")

# --- ここに情報を入れて実行するだけ ---
if __name__ == "__main__":
    # ここを書き換えることで次々と追加できます
    add_hotel_manual("136206", "335007", "00902459", "ロイヤルビューホテル美ら海")
