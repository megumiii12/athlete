import psycopg2
import psycopg2.extras
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
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
        print("❌ DB connection error:", e)
        return None

def init_auth_db():
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            gender VARCHAR(10),
            age INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
        """)

        conn.commit()
        return True
    finally:
        conn.close()

def create_user(username, email, password, gender=None, age=None):
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            return None

        pw_hash = generate_password_hash(password)
        cur.execute("""
        INSERT INTO users (username, email, password_hash, gender, age)
        VALUES (%s,%s,%s,%s,%s) RETURNING id
        """, (username, email, pw_hash, gender, age))

        conn.commit()
        return cur.fetchone()["id"]
    finally:
        conn.close()

def authenticate_user(email, password):
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            del user["password_hash"]
            return user
        return None
    finally:
        conn.close()

def generate_session_token(user_id, days=30):
    conn = get_connection()
    if not conn:
        return None

    try:
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(days=days)

        cur = conn.cursor()
        cur.execute("""
        INSERT INTO sessions (user_id, token, expires_at)
        VALUES (%s,%s,%s)
        """, (user_id, token, expires))

        conn.commit()
        return token
    finally:
        conn.close()

def get_user_by_token(token):
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT u.id,u.username,u.email,u.gender,u.age
        FROM users u
        JOIN sessions s ON u.id=s.user_id
        WHERE s.token=%s AND s.expires_at>NOW()
        """, (token,))
        return cur.fetchone()
    finally:
        conn.close()

def update_password(email, new_password):
    conn = get_connection()
    if not conn:
        return False

    try:
        pw_hash = generate_password_hash(new_password)
        cur = conn.cursor()
        cur.execute("""
        UPDATE users SET password_hash=%s WHERE email=%s
        """, (pw_hash, email))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
