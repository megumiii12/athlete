from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from datetime import timedelta
from functools import wraps
from dotenv import load_dotenv
import os

from utils.db_utils import (
    init_db,
    insert_health_data,
    get_latest_data,
    get_history_data,
)
from utils.auth_utils import (
    init_auth_db,
    create_user,
    authenticate_user,
    get_user_by_token,
    update_password,
    generate_session_token
)
from utils.ai_model import HealthAIModel

# ======================
# INIT
# ======================
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,   # ✅ REQUIRED for Render HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)
)

# ======================
# DATABASE INIT (SAFE)
# ======================
if os.environ.get("DATABASE_URL"):
    init_db()
    init_auth_db()
    print("✅ Databases initialized")
else:
    print("⚠️ DATABASE_URL not found")

# ======================
# AI MODEL
# ======================
try:
    ai_model = HealthAIModel()
    print("✅ AI model loaded")
except Exception as e:
    print("⚠️ AI disabled:", e)
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
# AUTH API
# ======================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    uid = create_user(
        data["username"],
        data["email"],
        data["password"],
        data.get("gender"),
        data.get("age"),
    )
    return jsonify(success=bool(uid)), (200 if uid else 400)

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = authenticate_user(data["email"], data["password"])

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
    return jsonify(success=update_password(data["email"], data["new_password"]))

@app.route("/api/verify-session")
@login_required
def verify_session():
    u = request.current_user
    return jsonify(success=True, user=u)

# ======================
# SENSOR APIs
# ======================
@app.route("/api/sensor-data", methods=["POST"])
@login_required
def sensor_data():
    data = request.get_json()
    hr = float(data["heart_rate"])
    temp = float(data["temperature"])
    athlete_id = request.current_user["id"]

    pred = ai_model.predict(hr, temp) if ai_model else {
        "is_abnormal": hr > 120 or temp > 37.5,
        "alert_message": "Check readings"
    }

    insert_health_data(athlete_id, hr, temp, pred)
    return jsonify(success=True, data=pred)

# 🔥 ESP32 ENDPOINT (NO AUTH)
@app.route("/api/sensor-data-raw", methods=["POST"])
def sensor_data_raw():
    try:
        data = request.get_json(force=True)

        hr = float(data.get("heart_rate", 0))
        temp = float(data.get("temperature", 0))
        athlete_id = int(data.get("athlete_id", 1))
        alert = data.get("alert_message", "OK")

        pred = {
            "is_abnormal": hr == 0 or temp < 30 or temp > 37.5,
            "alert_message": alert
        }

        insert_health_data(athlete_id, hr, temp, pred)

        return jsonify(success=True), 200

    except Exception as e:
        print("❌ ESP32 ERROR:", e)
        return jsonify(success=False, error=str(e)), 400


# ======================
# DATA FOR GRAPHS
# ======================
@app.route("/api/latest-data")
@login_required
def latest_data():
    return jsonify(get_latest_data(request.current_user["id"]) or {})

@app.route("/api/history")
@login_required
def history():
    return jsonify(get_history_data(request.current_user["id"]))

@app.route("/api/health")
def health():
    return jsonify(status="ok")

# ======================
# ENTRY
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)