from app import app, db, User, Alert

with app.app_context():
    print("--- Users ---")
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id}, Username: {u.username}, Email: {u.email}")
    
    print("\n--- Alerts ---")
    alerts = Alert.query.all()
    for a in alerts:
        print(f"ID: {a.id}, Product: {a.product_name}, Email: {a.user.email if a.user else 'N/A'}, Notified: {a.is_notified}")
