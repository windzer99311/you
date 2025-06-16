from flask import Flask, render_template_string
import threading
import time
from datetime import datetime, timedelta
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

VIRTUAL_START_STR = "2025-06-13 00:00:00"
VIRTUAL_START = datetime.strptime(VIRTUAL_START_STR, "%Y-%m-%d %H:%M:%S")
BOOT_TIME_FILE = "boot_time.txt"
LOG_FILE = "logs.txt"

# Initialize or load boot time
if os.path.exists(BOOT_TIME_FILE):
    with open(BOOT_TIME_FILE, "r", encoding='utf-8') as f:
        REAL_SERVER_START = datetime.strptime(f.read().strip(), "%Y-%m-%d %H:%M:%S")
else:
    REAL_SERVER_START = datetime.now()
    with open(BOOT_TIME_FILE, "w", encoding='utf-8') as f:
        f.write(REAL_SERVER_START.strftime("%Y-%m-%d %H:%M:%S"))

# Background visiting logic
def wake_web():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    while True:
        log_lines = []
        now_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

        try:
            with open("weblist.txt", "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
                for url in urls:
                    try:
                        driver.get(url)
                        log_line = f"{now_str} ✅ {url} → 200"
                    except WebDriverException as e:
                        log_line = f"{now_str} ❌ {url} → Error: {e}"
                    print(log_line)
                    log_lines.append(log_line)
        except FileNotFoundError:
            log_lines.append(f"{now_str} ❌ weblist.txt not found.")

        if log_lines:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                for line in log_lines:
                    f.write(line + "\n")

        time.sleep(30)

# Start background thread
if not os.path.exists("wake_thread.lock"):
    open("wake_thread.lock", "w").close()
    threading.Thread(target=wake_web, daemon=True).start()

# Flask route
@app.route("/")
def home():
    elapsed_real = (datetime.now() - REAL_SERVER_START).total_seconds()
    current_virtual = VIRTUAL_START + timedelta(seconds=elapsed_real)

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-100:]
    else:
        lines = []

    html = f"""
    <html>
    <head>
        <title>Wake Web Flask</title>
        <style>
            .log-box {{
                height: 400px;
                overflow-y: auto;
                background: #f9f9f9;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-family: monospace;
                white-space: pre-wrap;
                color: #000;
            }}
        </style>
    </head>
    <body>
        <h1>Wake Web Flask</h1>
        <h3>Time running since:</h3>
        <pre>{current_virtual.strftime("%Y-%m-%d %H:%M:%S")}</pre>
        <h3>Request Log</h3>
        <div class="log-box">
            {"<br>".join(line.strip() for line in lines)}
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
