"""Based Budik - Configuration"""

import os

# Flask
SECRET_KEY = os.environ.get("BUDIK_SECRET_KEY", "dev-secret-key-change-in-prod")
HOST = "127.0.0.1"
PORT = 5000

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "alarm_data.db")

# Train API
API_BASE_URL = "https://www.cd.cz/api"
API_TIMEOUT = 10  # seconds

# Alarm defaults
DEFAULT_PREP_MINUTES = 30
CHECK_BEFORE_MINUTES = 15  # how many minutes before alarm to check API
FAILSAFE_OFFSET_MINUTES = 15  # how much earlier is safe_wake_time vs base_wake_time

# macOS
ALARM_SOUND_PATH = os.path.join(os.path.dirname(__file__), "static", "alarm.wav")
CAFFEINATE_DURATION = 1200  # 20 minutes in seconds
