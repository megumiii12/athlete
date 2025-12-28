import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set")
        return None
    try:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    except Exception as e:
        print("❌ DB error:", e)
        return None

def init_db():
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS health_data (
            id SERIAL PRIMARY KEY,
            athlete_id INT NOT NULL,
            heart_rate DECIMAL,
            temperature DECIMAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_abnormal BOOLEAN,
            alert_message TEXT
        )
        """)
        conn.commit()
        return True
    finally:
        conn.close()

def insert_health_data(athlete_id, hr, temp, pred):
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO health_data
        (athlete_id, heart_rate, temperature, is_abnormal, alert_message)
        VALUES (%s,%s,%s,%s,%s)
        """, (athlete_id, hr, temp, pred["is_abnormal"], pred["alert_message"]))
        conn.commit()
        return True
    finally:
        conn.close()

def get_latest_data(athlete_id):
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM health_data
        WHERE athlete_id=%s
        ORDER BY timestamp DESC LIMIT 1
        """, (athlete_id,))
        return cur.fetchone()
    finally:
        conn.close()
