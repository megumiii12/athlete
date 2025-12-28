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

# ======================
# GET HISTORY DATA (FOR GRAPHS)
# ======================
def get_history_data(athlete_id, hours=24):
    conn = get_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT heart_rate, temperature, timestamp, is_abnormal, alert_message
                FROM health_data
                WHERE athlete_id = %s
                AND timestamp >= NOW() - INTERVAL '%s HOURS'
                ORDER BY timestamp ASC
            """, (athlete_id, hours))

            rows = cur.fetchall()

            # Convert timestamp + boolean
            result = []
            for row in rows:
                row = dict(row)
                row["timestamp"] = row["timestamp"].isoformat() if row["timestamp"] else None
                row["is_abnormal"] = bool(row["is_abnormal"])
                result.append(row)

            return result
    except Exception as e:
        print("❌ get_history_data error:", e)
        return []
    finally:
        conn.close()


# ======================
# GET ABNORMAL TEMPERATURE HISTORY
# ======================
def get_abnormal_temp_history(athlete_id, threshold=37.5, hours=168):
    conn = get_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT heart_rate, temperature, timestamp
                FROM health_data
                WHERE athlete_id = %s
                AND temperature >= %s
                AND timestamp >= NOW() - INTERVAL '%s HOURS'
                ORDER BY timestamp DESC
            """, (athlete_id, threshold, hours))

            rows = cur.fetchall()

            result = []
            for row in rows:
                row = dict(row)
                row["timestamp"] = row["timestamp"].isoformat() if row["timestamp"] else None
                result.append(row)

            return result
    except Exception as e:
        print("❌ get_abnormal_temp_history error:", e)
        return []
    finally:
        conn.close()
