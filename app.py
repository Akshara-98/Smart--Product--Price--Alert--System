import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import mimetypes
mimetypes.add_type('text/css', '.css')

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import threading
import time
import os
from dotenv import load_dotenv

load_dotenv()

import scraper
import notifier

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_change_in_production')

# --- Database Configuration ---
# Use absolute path for SQLite so it works both locally and on Render
_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'price_tracker.db')
os.makedirs(os.path.dirname(_db_path), exist_ok=True)
_default_db_url = f'sqlite:///{_db_path}'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', _default_db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Session / Cookie config (needed for HTTPS on Render) ---
_is_production = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)
app.config['SESSION_COOKIE_SECURE'] = bool(_is_production)
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if _is_production else 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

db = SQLAlchemy(app)

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    alerts = db.relationship('Alert', backref='user', lazy=True)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    product_url = db.Column(db.String(500), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    is_notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_url': self.product_url,
            'target_price': self.target_price,
            'current_price': self.current_price,
            'user_email': self.user.email if self.user else None,
            'is_notified': self.is_notified,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

with app.app_context():
    db.create_all()

# --- Background Task ---
def check_prices_periodically():
    """
    Background thread that checks all non-notified alerts every 2 minutes.
    Each alert's email is sent to the alert's OWN user's registered email.
    """
    while True:
        with app.app_context():
            print("INFO: Starting background price check...")
            try:
                # Only check alerts where the user hasn't been notified yet
                active_alerts = Alert.query.filter_by(is_notified=False).all()
                print(f"INFO: Found {len(active_alerts)} unnotified alert(s) to check.")

                for alert in active_alerts:
                    try:
                        result = scraper.get_product_details(alert.product_url)

                        if result['success']:
                            current_price = result['current_price']
                            alert.product_name = result.get('product_name', alert.product_name)
                            alert.current_price = current_price

                            if current_price is not None and current_price <= alert.target_price:
                                # Always look up user directly by user_id — never rely on lazy relationship
                                owner = db.session.get(User, alert.user_id)
                                user_email = owner.email if owner else None

                                print(f"MATCH: Alert {alert.id} | '{alert.product_name[:40]}' | "
                                      f"current=Rs{current_price} <= target=Rs{alert.target_price} | "
                                      f"sending to -> {user_email or 'NO EMAIL FOUND'}")

                                email_sent = False
                                if user_email:
                                    email_sent = notifier.send_price_alert(
                                        user_email,
                                        alert.product_name,
                                        current_price,
                                        alert.target_price,
                                        alert.product_url
                                    )
                                else:
                                    print(f"WARNING: No email found for user_id={alert.user_id} (Alert {alert.id}). Skipping.")

                                if email_sent:
                                    alert.is_notified = True
                                    db.session.commit()
                                    print(f"SUCCESS: Alert {alert.id} marked notified. Email sent to {user_email}.")
                                else:
                                    db.session.commit()  # still save price update
                                    print(f"WARNING: Email failed for Alert {alert.id} ({user_email}). Will retry next cycle.")
                            else:
                                print(f"INFO: Alert {alert.id} | '{alert.product_name[:35]}' | "
                                      f"current=Rs{current_price} above target=Rs{alert.target_price} (no email).")
                                db.session.commit()  # Commit price update
                        else:
                            print(f"ERROR: Scrape failed for Alert {alert.id}: {result.get('error')}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"ERROR: Exception processing Alert {alert.id}: {e}")

                print("INFO: Background price check complete.")
            except Exception as outer_e:
                print(f"ERROR: Background scheduler exception: {outer_e}")

        # Check every 2 minutes
        time.sleep(120)

# Start background thread
thread = threading.Thread(target=check_prices_periodically, daemon=True)
thread.start()

# --- CORS Headers for Live Server (Port 5500) Support ---
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        return response

# --- Routes ---
@app.route('/')
def home():
    user_email = session.get('user_email')
    return render_template('index.html', user_email=user_email, current_view='dashboard')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
        else:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
        
        if not username or not email or not password:
            msg = 'All fields are required'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('index.html', current_view='register', error=msg)

        if User.query.filter_by(email=email).first():
            msg = 'Email already exists'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('index.html', current_view='register', error=msg)

        if User.query.filter_by(username=username).first():
            msg = 'Username already taken'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('index.html', current_view='register', error=msg)
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        session['user_email'] = new_user.email
        
        if request.is_json:
            return jsonify({'success': True, 'email': new_user.email, 'message': 'Account created successfully!'})
        return redirect(url_for('home'))
        
    return render_template('index.html', current_view='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            email = data.get('email', '').strip()
            password = data.get('password', '')
        else:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            if request.is_json:
                return jsonify({'success': True, 'email': user.email, 'message': 'Logged in successfully!'})
            return redirect(url_for('home'))
            
        msg = 'Invalid email or password'
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 401
        return render_template('index.html', current_view='login', error=msg)
        
    return render_template('index.html', current_view='login')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('home'))

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'email': session.get('user_email')})
    return jsonify({'authenticated': False})

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    # Always query the user directly to get their real registered email
    owner = db.session.get(User, user_id)
    user_email = owner.email if owner else None

    alerts = Alert.query.filter_by(user_id=user_id).order_by(Alert.created_at.desc()).all()

    # Auto-trigger notification for any alert whose price reached target but hasn't been notified
    for a in alerts:
        if a.current_price is not None and a.current_price <= a.target_price and not a.is_notified:
            if user_email:
                print(f"INFO: get_alerts trigger | Alert {a.id} | '{a.product_name[:30]}' -> sending to {user_email}")
                sent = notifier.send_price_alert(
                    user_email,       # <-- the logged-in user's OWN email from DB
                    a.product_name,
                    a.current_price,
                    a.target_price,
                    a.product_url
                )
                if sent:
                    a.is_notified = True
                    db.session.commit()
                    print(f"SUCCESS: Email sent to {user_email} for Alert {a.id}.")

    return jsonify([a.to_dict() for a in alerts])

@app.route('/api/alerts/refresh', methods=['POST', 'GET'])
def refresh_alerts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    # Query user directly by ID — get their real registered email
    owner = db.session.get(User, user_id)
    user_email = owner.email if owner else None
    alerts = Alert.query.filter_by(user_id=user_id).all()

    updated = 0
    notified = 0
    for a in alerts:
        try:
            res = scraper.get_product_details(a.product_url)
            if res.get('success'):
                curr = res.get('current_price')
                if curr is not None:
                    a.current_price = curr
                    a.product_name = res.get('product_name', a.product_name)
                    updated += 1

                    if curr <= a.target_price and not a.is_notified:
                        if user_email:
                            print(f"INFO: refresh trigger | Alert {a.id} | '{a.product_name[:35]}' -> sending to {user_email}")
                            sent = notifier.send_price_alert(
                                user_email,    # <-- the logged-in user's OWN email from DB
                                a.product_name,
                                curr,
                                a.target_price,
                                a.product_url
                            )
                            if sent:
                                a.is_notified = True
                                notified += 1
                                print(f"SUCCESS: Email sent to {user_email} for Alert {a.id}.")
                        else:
                            print(f"WARNING: No email found for user_id={user_id} during refresh. Skipping Alert {a.id}.")
        except Exception as e:
            print(f"ERROR: refresh check for Alert {a.id}: {e}")

    db.session.commit()
    return jsonify({
        'success': True,
        'message': f"Refreshed {updated} products. {notified} price alert(s) sent.",
        'alerts': [a.to_dict() for a in alerts]
    })

@app.route('/api/supported-sites', methods=['GET'])
def supported_sites():
    return jsonify({
        'sites': scraper.SUPPORTED_DOMAINS
    })

@app.route('/api/alerts', methods=['POST'])
def add_alert():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.json or {}
    url = data.get('url', '').strip()
    target_price = data.get('target_price')

    if not url or target_price is None:
        return jsonify({'success': False, 'message': 'Missing required fields (url, target_price)'}), 400

    # Validate URL
    if not scraper.is_supported_url(url):
        return jsonify({
            'success': False,
            'message': 'Please enter a valid product URL (http or https).'
        }), 400

    user_id = session['user_id']
    # Always query user directly by ID for their real registered email
    owner = db.session.get(User, user_id)
    user_email = owner.email if owner else None
    if user_email:
        session['user_email'] = user_email

    try:
        target_price_val = float(target_price)
        if target_price_val <= 0:
            return jsonify({'success': False, 'message': 'Target price must be greater than zero'}), 400

        # Initial scrape to get name and current price
        result = scraper.get_product_details(url)
        if not result['success']:
             return jsonify({'success': False, 'message': f"Scraping Error: {result.get('error')}"}), 400

        # Determine if target price is already reached immediately
        is_reached = result.get('current_price') is not None and result['current_price'] <= target_price_val
        email_sent = False

        if is_reached and user_email:
            email_sent = notifier.send_price_alert(
                user_email, 
                result['product_name'], 
                result['current_price'], 
                target_price_val, 
                url
            )

        new_alert = Alert(
            product_name=result['product_name'],
            product_url=url,
            target_price=target_price_val,
            current_price=result['current_price'],
            is_notified=email_sent,
            user_id=user_id
        )
        
        db.session.add(new_alert)
        db.session.commit()
        
        if is_reached:
            if email_sent:
                return jsonify({
                    'success': True,
                    'message': f"Target price reached! Alert email sent to {user_email}."
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f"Alert added! Target reached, but email could not be sent to {user_email or 'user'}."
                })

        return jsonify({'success': True, 'message': 'Alert added successfully! Monitoring initialized.'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid target price value'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/alerts/<int:id>', methods=['DELETE'])
def delete_alert(id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    alert = Alert.query.get(id)
    if not alert or alert.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Alert not found'}), 404
    
    db.session.delete(alert)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Alert deleted successfully'})

import socket

def find_available_port(default_port=5000):
    for p in [default_port, 5001, 5050, 8080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return default_port

if __name__ == '__main__':
    configured_port = int(os.environ.get('PORT', 5000))
    port = find_available_port(configured_port)
    print("\n" + "="*65)
    print("🚀 SMART PRODUCT PRICE ALERT SYSTEM IS READY!")
    print(f"👉 OPEN IN BROWSER: http://localhost:{port}")
    print("="*65 + "\n")
    app.run(debug=True, host='0.0.0.0', port=port)
