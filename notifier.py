import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

from pathlib import Path
dotenv_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Built-in SMTP Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip('\"\'')
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "pricealert167@gmail.com").strip('\"\'')
# Correct Google App Password: gnfynlwmhwbgskxc
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "gnfynlwmhwbgskxc").strip('\"\'').replace(" ", "")

def send_price_alert(user_email, product_name, current_price, target_price, product_url):
    """
    Sends an email notification to the user when a price drop is detected.
    Sender: SMTP_USERNAME (pricealert167@gmail.com)
    Recipient: user_email (the user's email)
    """
    if not user_email or not user_email.strip():
        print("ERROR: Recipient email address is missing.")
        return False

    user_email = user_email.strip()
    server_host = os.environ.get("SMTP_SERVER", SMTP_SERVER).strip('\"\'')
    server_port = int(os.environ.get("SMTP_PORT", SMTP_PORT))
    sender_user = os.environ.get("SMTP_USERNAME", SMTP_USERNAME).strip('\"\'')
    sender_pass = os.environ.get("SMTP_PASSWORD", SMTP_PASSWORD).strip('\"\'').replace(" ", "")

    # Sanity check password fallback if environment was empty or wrong
    if not sender_pass or sender_pass == "gnfynlwmhwbjskxc":
        sender_pass = "gnfynlwmhwbgskxc"

    if not sender_user or not sender_pass:
        print(f"ERROR: SMTP credentials missing. Skipping email to {user_email}.")
        return False

    print(f"INFO: Sending price alert from {sender_user} to {user_email} for '{product_name}'...")
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"PriceTracker Pro <{sender_user}>"
        msg['To'] = user_email
        msg['Subject'] = f"🚀 Price Drop Alert: {product_name[:40]}..."

        body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; background-color: #f8fafc; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: auto; background: #ffffff; border: 1px solid #e2e8f0; padding: 40px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="display: inline-block; background: #10b981; color: white; padding: 15px; border-radius: 50%; margin-bottom: 15px; font-size: 30px; line-height: 1;">
                        🎉
                    </div>
                    <h2 style="color: #0f172a; margin: 0; font-size: 24px;">Target Price Reached!</h2>
                    <p style="color: #64748b; margin-top: 8px;">Your product is now available at or below your desired price.</p>
                </div>
                
                <div style="background: #f1f5f9; padding: 25px; border-radius: 12px; margin: 30px 0;">
                    <h3 style="margin-top: 0; color: #334155; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em;">Product Details</h3>
                    <p style="font-weight: 600; font-size: 18px; margin: 10px 0; color: #0f172a;">{product_name}</p>
                    
                    <table style="width: 100%; margin-top: 15px; border-collapse: collapse;">
                        <tr>
                            <td style="color: #64748b; padding-bottom: 8px; font-size: 15px;">Current Price:</td>
                            <td style="text-align: right; color: #10b981; font-weight: 700; font-size: 22px; padding-bottom: 8px;">₹{current_price:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="color: #64748b; font-size: 15px;">Your Target:</td>
                            <td style="text-align: right; color: #3b82f6; font-weight: 600; font-size: 18px;">₹{target_price:,.2f}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{product_url}" target="_blank" style="background: #3b82f6; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 10px; font-weight: 700; display: inline-block; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                        🛒 View Product on Site
                    </a>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                <p style="font-size: 13px; color: #94a3b8; text-align: center; line-height: 1.6;">
                    You received this email because you created a price alert on PriceTracker Pro for <strong>{user_email}</strong>.<br>
                    <strong>Happy Shopping!</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(server_host, server_port, timeout=20) as server:
            server.set_debuglevel(0)
            server.starttls()
            server.login(sender_user, sender_pass)
            server.send_message(msg)
            
        print(f"SUCCESS: Email sent successfully to {user_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print(f"CRITICAL ERROR: SMTP Authentication failed for {sender_user}. Please check App Password.")
        return False
    except smtplib.SMTPConnectError:
        print(f"ERROR: Could not connect to SMTP server {server_host}:{server_port}.")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected exception while sending email to {user_email}: {e}")
        return False