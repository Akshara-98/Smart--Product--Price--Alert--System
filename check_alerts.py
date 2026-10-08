from app import app, Alert, db
with app.app_context():
    alerts = Alert.query.all()
    print("ID | Notified | URL")
    for a in alerts:
        print(f"{a.id} | {a.is_notified} | {a.product_url}")
