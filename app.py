from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db_utils import init_db, insert_health_data, get_latest_data, get_history_data, get_abnormal_temp_history, get_connection
from utils.auth_utils import (
    init_auth_db, create_user, authenticate_user, 
    get_user_by_token, update_password, generate_session_token
)
from utils.ai_model import HealthAIModel
from datetime import datetime, timedelta
import os
from functools import wraps
from dotenv import load_dotenv
import mysql.connector

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Session and Cookie Configuration
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['SESSION_COOKIE_SAMESITE'] = None
app.config['SESSION_COOKIE_SECURE'] = False

# Production configurations
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Initialize databases on startup
try:
    print("🔧 Initializing databases...")
    init_db()
    init_auth_db()
    print("✅ Databases initialized successfully!")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")

# Initialize AI Model
try:
    ai_model = HealthAIModel()
    print("✅ AI Model loaded successfully!")
except Exception as e:
    print(f"⚠️ AI Model not loaded: {e}")
    ai_model = None

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check session
        token = session.get('token')
        
        # If no token in session, check Authorization header
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            # Redirect to login page instead of returning JSON
            return redirect(url_for('index'))
        
        user = get_user_by_token(token)
        if not user:
            # Clear invalid session and redirect
            session.clear()
            return redirect(url_for('index'))
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('cpe22.html')  

@app.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('2ndpage.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        gender = data.get('gender')
        age = data.get('age')
        
        if not all([username, email, password]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        user_id = create_user(username, email, password, gender, age)
        
        if user_id:
            return jsonify({'success': True, 'message': 'Registration successful', 'user_id': user_id})
        else:
            return jsonify({'success': False, 'error': 'Email already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({'success': False, 'error': 'Missing credentials'}), 400
        
        user = authenticate_user(email, password)
        
        if user:
            token = generate_session_token(user['id'])
            
            # Set session with permanent flag
            session.permanent = True
            session['token'] = token
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            print(f"✅ Login successful for {user['username']}, Token: {token[:10]}...")
            
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'], 
                    'username': user['username'], 
                    'email': user['email']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        new_password = data.get('new_password')
        
        success = update_password(email, new_password)
        
        if success:
            return jsonify({'success': True, 'message': 'Password updated'})
        else:
            return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-session', methods=['GET'])
@login_required
def verify_session():
    return jsonify({
        'success': True,
        'user': {
            'id': request.current_user['id'],
            'username': request.current_user['username'],
            'email': request.current_user['email']
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Server running'})

@app.route('/api/sensor-data', methods=['POST'])
@login_required
def receive_sensor_data():
    """Receive sensor data and associate with current logged-in user"""
    try:
        data = request.get_json()
        heart_rate = float(data.get('heart_rate'))
        temperature = float(data.get('temperature'))
        athlete_id = request.current_user['id']  # Use current user's ID
        
        print(f"📊 Sensor: HR={heart_rate}, Temp={temperature}, User ID={athlete_id}")

        if ai_model:
            prediction = ai_model.predict(heart_rate, temperature, request.current_user.get('age', 25))
        else:
            is_abnormal = (heart_rate > 100 or temperature > 37.5)
            prediction = {
                'is_abnormal': int(is_abnormal),
                'confidence': 0.5,
                'alert_message': 'Check readings' if is_abnormal else 'Normal',
                'heart_rate': heart_rate,
                'temperature': temperature
            }
        
        insert_health_data(athlete_id, heart_rate, temperature, prediction)
        
        return jsonify({'success': True, 'data': prediction})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/sensor-data-raw', methods=['POST', 'OPTIONS'])
def receive_sensor_data_raw():
    """Receive sensor data without authentication (for IoT devices)"""
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    
    try:
        data = request.get_json()
        heart_rate = float(data.get('heart_rate'))
        temperature = float(data.get('temperature'))
        # Get athlete_id from request - REQUIRED for raw endpoint
        athlete_id = int(data.get('athlete_id'))
        
        # Validate athlete_id exists
        if not athlete_id:
            return jsonify({'success': False, 'error': 'athlete_id is required'}), 400
        
        print(f"📊 Sensor: HR={heart_rate}, Temp={temperature}, Athlete ID={athlete_id}")

        if ai_model:
            prediction = ai_model.predict(heart_rate, temperature)
        else:
            is_abnormal = (heart_rate > 100 or temperature > 37.5)
            prediction = {
                'is_abnormal': int(is_abnormal),
                'confidence': 0.5,
                'alert_message': 'Check readings' if is_abnormal else 'Normal',
                'heart_rate': heart_rate,
                'temperature': temperature
            }
        
        insert_health_data(athlete_id, heart_rate, temperature, prediction)
        
        response = jsonify({'success': True, 'data': prediction})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/latest-data', methods=['GET'])
@login_required
def latest_data():
    athlete_id = request.current_user['id']
    row = get_latest_data(athlete_id)
    if not row:
        return jsonify({'message': 'No data found'}), 404
    return jsonify(row)

@app.route('/api/history', methods=['GET'])
@login_required
def history_data():
    athlete_id = request.current_user['id']
    
    print(f"📋 /api/history called - Athlete ID: {athlete_id}")
    
    conn = get_connection()
    if not conn:
        print("❌ Failed to get database connection")
        return jsonify([]), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get ALL data for this athlete (no time filter for debugging)
        cursor.execute("""
            SELECT heart_rate, temperature, timestamp, is_abnormal
            FROM health_data
            WHERE athlete_id = %s
            ORDER BY timestamp DESC
        """, (athlete_id,))
        
        rows = cursor.fetchall()
        print(f"✅ Query returned {len(rows)} rows for athlete {athlete_id}")
        
        for row in rows:
            row['is_abnormal'] = bool(row['is_abnormal'])
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
        
        print(f"📊 Returning {len(rows)} records")
        return jsonify(rows)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/abnormal-temp-history', methods=['GET'])
@login_required
def abnormal_temp_history():
    """Get all abnormal temperature readings for the user"""
    try:
        athlete_id = request.current_user['id']
        hours = int(request.args.get('hours', 168))
        temp_threshold = float(request.args.get('threshold', 37.5))
        
        data = get_abnormal_temp_history(athlete_id, temp_threshold, hours)
        
        print(f"✅ Retrieved {len(data)} abnormal readings for user {athlete_id}")
        return jsonify(data)
    except Exception as e:
        print(f"❌ Error fetching abnormal temp history: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)