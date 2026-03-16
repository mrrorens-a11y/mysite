import sqlite3

def init_db():
    conn = sqlite3.connect('tomarun.db')
    cursor = conn.cursor()
    
    # テーブル作成（存在しない場合）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hotels (
            rakuten_id TEXT PRIMARY KEY,
            jalan_id TEXT,
            yahoo_id TEXT,
            hotel_name TEXT
        )
    ''')

    # 最新の宿データリスト
    hotels_list = [
        ("15062", "yad346870", "00030772", "ロイヤルビューホテル美ら海"),
        ("172796", "yad344384", "00907941", "ゆくりなリゾート沖縄 海風"),
        ("14584", "yad314427", "00030565", "ホテルマハイナ ウェルネスリゾートオキナワ"),
        ("166326", "yad307933", "00050672", "コスタベージャ　コンドミニアムリゾート＜本部町＞"),
        ("177856", "yad348214", "00050889", "カリーコンド美ら海"),
        ("145419", "yad307948", "00002000", "オリオンホテル　モトブリゾート＆スパ"),
        ("149384", "yad336920", "00030200", "ウィステリア・コンドミニアム・リゾート"),
        ("141237", "yad338738", "00904289", "美ら海ビレッジ"),
        ("67833", "yad396860", "00050210", "Ｆｕｋｕｇｉ　Ｔｅｒｒａｃｅ（フクギテラス）"),
        ("184542", "yad300252", "00913637", "ニルヤカナヤＢＩＳＥ")
    ]

    # データの登録・更新（INSERT OR REPLACE で重複を防ぐ）
    for rakuten_id, jalan_id, yahoo_id, name in hotels_list:
        cursor.execute('''
            INSERT OR REPLACE INTO hotels (rakuten_id, jalan_id, yahoo_id, hotel_name)
            VALUES (?, ?, ?, ?)
        ''', (rakuten_id, jalan_id, yahoo_id, name))

    conn.commit()
    print(f"成功: {len(hotels_list)}件の宿データを登録・更新しました。")
    conn.close()

if __name__ == "__main__":
    init_db()
