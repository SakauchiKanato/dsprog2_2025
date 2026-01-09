import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "weather.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # ファイルへの書き込みを確実に見えるようにするため設定を変更
    conn.execute("PRAGMA journal_mode = DELETE")
    return conn

def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # エリア情報テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS areas (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        # 予報データテーブル
        # office_code: 取得元の支庁コード
        # area_code: 地域コード
        # report_datetime: 発表時刻
        # target_date: 予報対象日 (YYYY-MM-DD)
        # weather: 天気
        # pop: 降水確率
        # fetch_timestamp: データ取得日時
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                office_code TEXT,
                area_code TEXT,
                report_datetime TEXT,
                target_date TEXT,
                weather TEXT,
                pop INTEGER,
                fetch_timestamp TEXT,
                FOREIGN KEY (area_code) REFERENCES areas (code),
                UNIQUE(office_code, area_code, target_date, report_datetime)
            )
        """)
        conn.commit()
    finally:
        conn.close()

def save_area(code, name):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO areas (code, name) VALUES (?, ?)", (code, name))
        conn.commit()

def get_areas():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, name FROM areas")
        return cursor.fetchall()

def save_forecast(office_code, area_code, report_datetime, target_date, weather, pop):
    with get_connection() as conn:
        cursor = conn.cursor()
        fetch_timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO forecasts 
            (office_code, area_code, report_datetime, target_date, weather, pop, fetch_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (office_code, area_code, report_datetime, target_date, weather, pop, fetch_timestamp))
        conn.commit()

def get_forecasts_by_office_and_date(office_code, target_date):
    with get_connection() as conn:
        cursor = conn.cursor()
        # 最新の発表時刻のデータを取得する。その支庁に紐づく全エリア分。
        cursor.execute("""
            SELECT f.area_code, a.name, f.weather, f.pop, f.report_datetime 
            FROM forecasts f
            JOIN areas a ON f.area_code = a.code
            WHERE f.office_code = ? AND f.target_date = ?
            AND f.report_datetime = (
                SELECT MAX(report_datetime) 
                FROM forecasts 
                WHERE office_code = ? AND target_date = ?
            )
        """, (office_code, target_date, office_code, target_date))
        return cursor.fetchall()

def get_historical_dates_by_office(office_code):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT target_date 
            FROM forecasts 
            WHERE office_code = ?
            ORDER BY target_date DESC
        """, (office_code,))
        return [row[0] for row in cursor.fetchall()]

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
