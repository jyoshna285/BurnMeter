import os
import sqlite3
import numpy as np
import xgboost as xgb
from flask import Flask, render_template, request, redirect, url_for, session
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# 🌿 Load environment variables
load_dotenv()

# 🚀 Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# 🔐 Google OAuth setup
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_url="/"
)
app.register_blueprint(google_bp, url_prefix="/")

# 💾 Initialize database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 🔍 Feature extraction for XGBoost
def get_features(data):
    gender = 0 if data['gender'] == 'Male' else 1
    intensity = data['intensity']
    hr, temp = {
        'Light': (90, 98.0),
        'Moderate': (110, 100.0),
        'Intense': (130, 102.0)
    }.get(intensity, (110, 100.0))

    return np.array([
        gender,
        int(data['age']),
        int(data['height']),
        int(data['weight']),
        int(data['duration']),
        hr,
        temp
    ]).reshape(1, -1)

# 🔗 Load the model
model = xgb.XGBRegressor()
model.load_model("xgb_calorie_model.json")

# 🌟 Base page
@app.route('/')
def base():
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        info = resp.json()
        session['username'] = info.get("email", "Guest")
        session['role'] = 'user'
    return render_template('base.html', username=session.get('username'))

# 🏠 Home
@app.route('/home')
def home():
    return render_template('home.html', username=session.get('username'))

# 📊 Dashboard
@app.route('/dashboard')
def dashboard():
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        info = resp.json()
        session['username'] = info.get("email", "Guest")
        session['role'] = 'user'
    return render_template('dashboard.html', username=session.get('username'), role=session.get('role'))

# 🔮 Predict calories
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    predicted = None
    if request.method == 'POST':
        form_data = request.form
        input_array = get_features(form_data)
        calories = model.predict(input_array)[0]
        predicted = round(calories, 2)
    return render_template('index.html', predicted=predicted, username=session.get('username'))

@app.route('/index')
def index():
    return render_template('index.html', predicted=None, username=session.get('username'))

# 👤 Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT password, role FROM users WHERE username = ?', (username,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session['username'] = username
            session['role'] = row[1]
            return redirect(url_for('dashboard'))
        else:
            return "❌ Invalid username or password"

    return render_template('login.html')

# 📝 Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            return "❌ Passwords do not match"

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                      (username, email, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "⚠️ Username or email already exists."

    return render_template('signup.html')

# 🔄 Password reset
@app.route('/reset', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        hashed = generate_password_hash(new_password)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('UPDATE users SET password = ? WHERE email = ?', (hashed, email))
        if c.rowcount == 0:
            conn.close()
            return "❌ Email not found."
        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template('reset.html')

# 🚪 Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('base'))

# 🚀 Run server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
