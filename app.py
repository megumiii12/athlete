from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from utils.db_utils import init_db, insert_health_data, get_latest_data
from utils.auth_utils import (
    init_auth_db, create_user, authenticate_user,
    get_user_by_token, update_password, generate_session_token
)
from utils.ai_model import HealthAIModel
from datetime import timedelta
from functools import wraps
from dotenv import load_dotenv
import os

# Load env vars
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

# ======================
# CONFIG
# ======================
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # Render handles HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)
)

# ======================
# INIT DATABASES (SAFE)
# ======================
if os.environ.get("DATABASE_URL"):
    try:
        print("🔧 Initializing databases...")
        init_db()
        init_auth_db()
        print("✅ Databases initialized")
    except Exception as e:
        print("❌ DB init failed:", e)
else:
    print("⚠️ DATABASE_URL not set, skipping DB init")

# ======================
# AI MODEL (SAFE)
# ======================
try:
    ai_model = HealthAIModel()
    print("✅ AI model loaded")
except Exception as e:
    print("⚠️ AI model not loaded:", e)
    ai_model = None

# ======================
# AUTH DECORATOR
# ======================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = session.get("token")

        if not token:
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                token = auth.split(" ")[1]

        if not token:
            return redirect(url_for("index"))

        user = get_user_by_token(token)
        if not user:
            session.clear()
            return redirect(url_for("index"))

        request.current_user = user
        return f(*args, **kwargs)
    return wrapper

# ======================
# PAGES
# ======================
@app.route("/")
def index():
    return render_template("cpe22.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("2ndpage.html")

# ======================
# AUTH APIs
# ======================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    user_id = create_user(
        data.get("username"),
        data.get("email"),
        data.get("password"),
        data.get("gender"),
        data.get("age"),
    )

    if user_id:
        return jsonify(success=True)
    return jsonify(success=False, error="Email exists"), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = authenticate_user(data.get("email"), data.get("password"))

    if not user:
        return jsonify(success=False), 401

    token = generate_session_token(user["id"])
    session.permanent = True
    session["token"] = token

    return jsonify(success=True, token=token, user=user)

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(success=True)

@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    if update_password(data.get("email"), data.get("new_password")):
        return jsonify(success=True)
    return jsonify(success=False), 404

# ======================
# DATA APIs
# ======================
@app.route("/api/sensor-data", methods=["POST"])
@login_required
def sensor_data():
    data = request.get_json()
    hr = float(data["heart_rate"])
    temp = float(data["temperature"])
    athlete_id = request.current_user["id"]

    if ai_model:
        pred = ai_model.predict(hr, temp, request.current_user.get("age", 25))
    else:
        abnormal = hr > 100 or temp > 37.5
        pred = {
            "is_abnormal": abnormal,
            "alert_message": "Check readings" if abnormal else "Normal",
        }

    insert_health_data(athlete_id, hr, temp, pred)
    return jsonify(success=True, data=pred)

@app.route("/api/latest-data")
@login_required
def latest_data():
    row = get_latest_data(request.current_user["id"])
    return jsonify(row or {})

@app.route("/api/health")
def health():
    return jsonify(status="ok")

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
