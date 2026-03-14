import sqlite3

def init_db():
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT,
            tel TEXT UNIQUE,
            rakuten_id TEXT,
            jalan_id TEXT,
            address TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("DBファイル 'tomarun.db' が作成されました！")

if __name__ == "__main__":
    init_db()
