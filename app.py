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
app.config['SQLALCHEMY_DATABASE_BIT_DB'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///price_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    Background thread that checks all non-notified alerts every 10 minutes.
    """
    while True:
        with app.app_context():
            print("INFO: Starting background price check...")
            try:
                # Only check alerts where the user hasn't been notified yet
                active_alerts = Alert.query.filter_by(is_notified=False).all()
                
                for alert in active_alerts:
                    try:
                        result = scraper.get_product_details(alert.product_url)
                        
                        if result['success']:
                            current_price = result['current_price']
                            alert.product_name = result['product_name']  # Update name in case it changed
                            alert.current_price = current_price
                            
                            if current_price <= alert.target_price:
                                user_email = alert.user.email if alert.user else None
                                print(f"MATCH: '{alert.product_name}' dropped to ₹{current_price} <= ₹{alert.target_price}. Triggering email...")
                                
                                email_sent = False
                                if user_email:
                                    email_sent = notifier.send_price_alert(
                                        user_email, 
                                        alert.product_name, 
                                        current_price, 
                                        alert.target_price, 
                                        alert.product_url
                                    )
                                
                                alert_id = alert.id
                                alert_recipient = user_email or "Unknown User"
                                # Delete alert immediately after target reached
                                db.session.delete(alert)
                                db.session.commit()
                                
                                if email_sent:
                                    print(f"SUCCESS: Alert ID {alert_id} deleted for {alert_recipient} after email sent.")
                                else:
                                    print(f"WARNING: Alert ID {alert_id} deleted for {alert_recipient}, but email sending failed or email missing.")
                            else:
                                print(f"INFO: '{alert.product_name}' price ₹{current_price} is above target ₹{alert.target_price}.")
                                db.session.commit()  # Commit name/price update
                        else:
                            print(f"ERROR: Failed to scrape {alert.product_url}: {result.get('error')}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"ERROR: Exception while processing alert ID {alert.id}: {e}")
                
                print("INFO: Background price check complete.")
            except Exception as outer_e:
                print(f"ERROR: Exception in background scheduler loop: {outer_e}")
        
        # Check every 10 minutes (600 seconds)
        time.sleep(600)

# Start background thread
thread = threading.Thread(target=check_prices_periodically, daemon=True)
thread.start()

# --- Routes ---
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user_email=session.get('user_email'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not username or not email or not password:
            return render_template('register.html', error='All fields are required')

        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already exists')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already taken')
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('home'))
            
        return render_template('login.html', error='Invalid email or password')
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    alerts = Alert.query.filter_by(user_id=session['user_id']).order_by(Alert.created_at.desc()).all()
    return jsonify([a.to_dict() for a in alerts])

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

    # Validate URL is from a supported site
    if not scraper.is_supported_url(url):
        return jsonify({
            'success': False,
            'message': 'Unsupported site. Supported: Amazon, Flipkart, Myntra, Meesho, AJIO, Nykaa, Snapdeal, Tata CLiQ, and more.'
        }), 400

    user_id = session['user_id']
    user_email = session.get('user_email')

    try:
        target_price_val = float(target_price)
        if target_price_val <= 0:
            return jsonify({'success': False, 'message': 'Target price must be greater than zero'}), 400

        # Initial scrape to get name and current price
        result = scraper.get_product_details(url)
        if not result['success']:
             return jsonify({'success': False, 'message': f"Scraping Error: {result.get('error')}"}), 400

        new_alert = Alert(
            product_name=result['product_name'],
            product_url=url,
            target_price=target_price_val,
            current_price=result['current_price'],
            user_id=user_id
        )
        
        db.session.add(new_alert)
        db.session.commit()
        
        # Immediate check if target reached
        if result['current_price'] <= target_price_val:
             email_sent = notifier.send_price_alert(
                            user_email, 
                            result['product_name'], 
                            result['current_price'], 
                            target_price_val, 
                            url
                        )
             # Delete alert if target reached
             db.session.delete(new_alert)
             db.session.commit()
             
             if email_sent:
                 return jsonify({'success': True, 'message': 'Target price is already reached! Alert email sent to your inbox.'})
             else:
                 return jsonify({'success': True, 'message': 'Target price is already reached! (Configure SMTP in .env to receive email alerts).'})

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
