import os

# Render provides the PORT environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1          # Keep at 1 so background thread runs only once
threads = 4
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
