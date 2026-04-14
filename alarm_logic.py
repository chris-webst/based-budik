"""Based Budik - Čistá logika rozhodování budíku"""

from datetime import datetime, timedelta


def should_use_failsafe(delay_minutes, api_success: bool, tolerance_minutes: int) -> bool:
    """
    Binární rozhodnutí: failsafe (safe_wake_time) nebo standard (base_wake_time)?

    Returns True  -> zavoní v safe_wake_time (dřívější spoj)
    Returns False -> zavoní v base_wake_time (standardní čas)

    Pravidlo:
    - API selhalo (timeout, chyba, vlak nenalezen) -> failsafe
    - Zpoždění > tolerance_minutes                 -> failsafe
    - Jinak                                        -> standard
    """
    if not api_success or delay_minutes is None:
        return True
    return delay_minutes > tolerance_minutes


def compute_check_time(safe_wake_time: str, check_before_minutes: int) -> str:
    """Vrátí čas kontroly jako HH:MM (safe_wake_time - check_before_minutes)."""
    t = datetime.strptime(safe_wake_time, "%H:%M")
    return (t - timedelta(minutes=check_before_minutes)).strftime("%H:%M")


def should_auto_check_now(alarm: dict) -> bool:
    """
    True pokud jsme v okně, kdy bychom měli kontrolu spustit okamžitě.

    Okno: check_time <= now <= base_wake_time (a alarm je aktivní pro dnešní den)
    """
    now = datetime.now()
    weekday = now.isoweekday()  # 1=Po, 7=Ne
    if weekday not in alarm["days_of_week"]:
        return False
    if not alarm["is_active"]:
        return False

    today = now.date()

    def to_dt(hhmm: str) -> datetime:
        return datetime.strptime(hhmm, "%H:%M").replace(
            year=today.year, month=today.month, day=today.day
        )

    check_dt = to_dt(alarm["safe_wake_time"]) - timedelta(minutes=alarm["check_before_minutes"])
    base_dt = to_dt(alarm["base_wake_time"])

    return check_dt <= now <= base_dt
