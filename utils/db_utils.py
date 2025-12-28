import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")

# ======================
# DB CONNECTION
# ======================
def get_connection():
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set")
        return None

    try:
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )
    except Exception as e:
        print("❌ DB connection error:", e)
        return None


# ======================
# INIT HEALTH DATA TABLE
# ======================
def init_db():
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
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


# ======================
# INSERT SENSOR DATA
# ======================
def insert_health_data(athlete_id, heart_rate, temperature, pred):
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO health_data
                (athlete_id, heart_rate, temperature, is_abnormal, alert_message)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                athlete_id,
                heart_rate,
                temperature,
                pred.get("is_abnormal"),
                pred.get("alert_message")
            ))
            conn.commit()
            return True
    finally:
        conn.close()


# ======================
# GET LATEST DATA
# ======================
def get_latest_data(athlete_id):
    conn = get_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM health_data
                WHERE athlete_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (athlete_id,))
            return cur.fetchone()
    finally:
        conn.close()
