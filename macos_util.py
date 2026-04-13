"""Based Budik - macOS systémové utility"""

import subprocess
import threading
from datetime import datetime

import config


def play_alarm():
    """Přehraje zvuk budíku (neblokující)."""
    threading.Thread(
        target=lambda: subprocess.run(["afplay", config.ALARM_SOUND_PATH], check=False),
        daemon=True
    ).start()


def stop_alarm():
    """Zastaví přehrávání afplay."""
    subprocess.run(["pkill", "afplay"], check=False)


def notify(title: str, message: str):
    """Zobrazí systémovou notifikaci."""
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], check=False)


def schedule_wake(wake_datetime: datetime):
    """Naplánuje probuzení Macu pomocí pmset. Vyžaduje sudoers nastavení."""
    formatted = wake_datetime.strftime("%m/%d/%Y %H:%M:%S")
    result = subprocess.run(
        ["sudo", "pmset", "schedule", "wake", formatted],
        capture_output=True, text=True
    )
    return result.returncode == 0


def cancel_wake():
    """Zruší naplánované probuzení."""
    subprocess.run(["sudo", "pmset", "schedule", "cancelall"], check=False)


def caffeinate(duration_seconds: int = config.CAFFEINATE_DURATION):
    """Zabrání uspání Macu po dobu duration_seconds (neblokující)."""
    proc = subprocess.Popen(["caffeinate", "-i", "-t", str(duration_seconds)])
    return proc


def check_pmset_permission() -> bool:
    """Ověří, že sudo pmset funguje bez hesla."""
    result = subprocess.run(
        ["sudo", "-n", "pmset", "-g"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def check_alarm_sound() -> bool:
    """Ověří, že soubor alarm.wav existuje."""
    import os
    return os.path.isfile(config.ALARM_SOUND_PATH)
