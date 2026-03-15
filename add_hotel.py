import sqlite3

def add_hotel_manual(rakuten_id, jalan_id, yahoo_id, name):
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    
    # テーブル作成（念のため）
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
    
    # 登録または更新
    cursor.execute('''
        INSERT OR REPLACE INTO hotels (rakuten_id, jalan_id, yahoo_id, hotel_name)
        VALUES (?, ?, ?, ?)
    ''', (str(rakuten_id), str(jalan_id), str(yahoo_id), name))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # データをリスト化して一気に回す
    hotels_list = [
        ("15062", "yad335007", "00902459", "ロイヤルビューホテル美ら海"),
        ("172796", "yad344384", "00907941", "ゆくりなリゾート沖縄 海風"),
        ("14584", "yad314427", "00030565", "ホテルマハイナ ウェルネスリゾートオキナワ"),
        ("166326", "yad307933", "00050672", "コスタベージャ　コンドミニアムリゾート＜本部町＞"),
        ("177856", "yad348214", "00050889", "カリーコンド美ら海"),
        ("145419", "yad307948", "00002000", "オリオンホテル　モトブリゾート＆スパ"),
        ("14584", "yad314427", "00030565", "ウィステリア・コンドミニアム・リゾート"),
        ("141237", "yad338738", "00904289", "美ら海ビレッジ"),
        ("67833", "yad396860", "00050210", "Ｆｕｋｕｇｉ　Ｔｅｒｒａｃｅ（フクギテラス）"),
        ("184542", "yad300252", "00913637", "ニルヤカナヤＢＩＳＥ"),
    ]

    print("--- データベース登録開始 ---")
    for r_id, j_id, y_id, name in hotels_list:
        add_hotel_manual(r_id, j_id, y_id, name)
        print(f"完了: {name}")
    print("--- 全10件の登録が終了しました ---")
