import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os

MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'athlete_app'),
    'password': '12345678',
    'database': os.environ.get('DB_NAME', 'athlete_health_db')
}

def get_connection():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']}")
        cursor.execute(f"USE {MYSQL_CONFIG['database']}")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athletes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                age INT,
                gender ENUM('male', 'female', 'other'),
                email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                athlete_id INT NOT NULL,
                heart_rate DECIMAL(6,2),
                temperature DECIMAL(4,2),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_abnormal TINYINT(1) DEFAULT 0,
                alert_message TEXT,
                INDEX idx_athlete_timestamp (athlete_id, timestamp),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        conn.commit()
        print("✅ MySQL health data tables initialized")
        return True
    except Error as e:
        print(f"Error initializing database: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def insert_health_data(athlete_id, heart_rate, temperature, prediction):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO health_data 
            (athlete_id, heart_rate, temperature, is_abnormal, alert_message)
            VALUES (%s, %s, %s, %s, %s)
        """, (athlete_id, heart_rate, temperature, prediction["is_abnormal"], prediction["alert_message"]))
        
        conn.commit()
        print(f"✅ Data inserted: athlete_id={athlete_id}, HR={heart_rate}, Temp={temperature}")
        return True
    except Error as e:
        print(f"Error inserting health data: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_latest_data(athlete_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT heart_rate, temperature, timestamp, is_abnormal, alert_message
            FROM health_data
            WHERE athlete_id = %s
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (athlete_id,))
        
        row = cursor.fetchone()
        
        if row:
            row['is_abnormal'] = bool(row['is_abnormal'])
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
        
        return row
    except Error as e:
        print(f"Error getting latest data: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_history_data(athlete_id, hours=24):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        since = datetime.now() - timedelta(hours=hours)
        
        print(f"🔍 Querying health_data for athlete_id={athlete_id}, since={since}")
        
        cursor.execute("""
            SELECT heart_rate, temperature, timestamp, is_abnormal
            FROM health_data
            WHERE athlete_id = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        """, (athlete_id, since))
        
        rows = cursor.fetchall()
        print(f"📊 Found {len(rows)} rows for athlete {athlete_id}")
        
        for row in rows:
            row['is_abnormal'] = bool(row['is_abnormal'])
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
        
        return rows
    except Error as e:
        print(f"Error getting history data: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_abnormal_temp_history(athlete_id, temp_threshold=37.5, hours=168):
    """Get all readings where temperature exceeds threshold"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        since = datetime.now() - timedelta(hours=hours)
        
        print(f"🔍 Querying abnormal temps for athlete_id={athlete_id}, threshold={temp_threshold}")
        
        cursor.execute("""
            SELECT heart_rate, temperature, timestamp, is_abnormal
            FROM health_data
            WHERE athlete_id = %s AND timestamp >= %s AND temperature > %s
            ORDER BY timestamp DESC
        """, (athlete_id, since, temp_threshold))
        
        rows = cursor.fetchall()
        
        for row in rows:
            row['is_abnormal'] = bool(row['is_abnormal'])
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
        
        print(f"📊 Found {len(rows)} abnormal temperature readings for athlete {athlete_id}")
        return rows
    except Error as e:
        print(f"Error getting abnormal temp history: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()