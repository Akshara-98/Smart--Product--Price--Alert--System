# 🚀 PriceTracker Pro

A full-stack, real-time e-commerce price tracking and automated email alert web application.

## ✨ Features
- **Consolidated UI (`index.html`)**: Sleek dark-mode glassmorphic interface with embedded responsive CSS and interactive JavaScript.
- **Multi-Platform Scraping**: Real-time extraction of product names and prices from:
  - Amazon (`amazon.in`, `amazon.com`, `amazon.co.uk`, `amzn.to`, etc.)
  - Flipkart & Shopsy
  - Myntra
  - Meesho
  - AJIO
  - Tata CLiQ, Nykaa, Snapdeal, Reliance Digital, Croma
- **Automated Alerts**: Background monitoring thread automatically checks tracked product prices every 10 minutes and dispatches HTML email notifications via SMTP whenever target price criteria are satisfied.
- **User Authentication**: Secure user registration and session-based login.

---

## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd price
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory (or edit `.env`):
```ini
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-google-app-password
SECRET_KEY=your_secret_key
PORT=5000
```
> **Note for Gmail users**: Use a 16-character [Google App Password](https://myaccount.google.com/apppasswords), not your standard Gmail login password.

---

## 🏃 Running the Application

Start the Flask server:
```bash
python app.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 📦 Pushing to GitHub

To push this repository to GitHub:
```bash
# 1. Initialize git (if not already done)
git init

# 2. Stage and commit files
git add .
git commit -m "Initial commit: PriceTracker Pro single-file UI and automated price tracking"

# 3. Add your remote repository
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git

# 4. Push to GitHub
git push -u origin main
```

