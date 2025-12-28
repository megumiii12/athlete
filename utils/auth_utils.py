import mysql.connector
from mysql.connector import Error
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'athlete_app'),
    'password': '12345678',
    'database': os.environ.get('DB_NAME', 'athlete_health_db')
}

def get_mysql_connection():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_auth_db():
    conn = get_mysql_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']}")
        cursor.execute(f"USE {MYSQL_CONFIG['database']}")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                gender ENUM('male', 'female', 'other'),
                age INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                INDEX idx_token (token),
                INDEX idx_user_id (user_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used TINYINT(1) DEFAULT 0,
                INDEX idx_token (token),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        conn.commit()
        print("✅ MySQL authentication tables initialized")
        return True
    except Error as e:
        print(f"Error initializing auth database: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def create_user(username, email, password, gender=None, age=None):
    conn = get_mysql_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return None
        
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, gender, age)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, email, password_hash, gender, age))
        
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except Error as e:
        print(f"Error creating user: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def authenticate_user(email, password):
    conn = get_mysql_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, email, password_hash, gender, age
            FROM users WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()
            del user['password_hash']
            return user
        
        return None
    except Error as e:
        print(f"Error authenticating user: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def generate_session_token(user_id, days=30):
    conn = get_mysql_connection()
    if not conn:
        return None
    
    try:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=days)
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE expires_at < NOW()")
        cursor.execute("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, token, expires_at))
        
        conn.commit()
        return token
    except Error as e:
        print(f"Error generating token: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_user_by_token(token):
    conn = get_mysql_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.gender, u.age
            FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.token = %s AND s.expires_at > NOW()
        """, (token,))
        
        user = cursor.fetchone()
        return user
    except Error as e:
        print(f"Error getting user by token: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def update_password(email, new_password):
    conn = get_mysql_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
        success = cursor.rowcount > 0
        conn.commit()
        return success
    except Error as e:
        print(f"Error updating password: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()