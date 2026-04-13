"""Based Budik - SQLite database operations"""

import json
import sqlite3
from datetime import datetime

import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            train_number TEXT NOT NULL,
            departure_station TEXT NOT NULL,
            arrival_station TEXT NOT NULL,
            scheduled_departure TEXT NOT NULL,
            base_wake_time TEXT NOT NULL,
            safe_wake_time TEXT NOT NULL,
            prep_minutes INTEGER NOT NULL DEFAULT 30,
            delay_tolerance_minutes INTEGER NOT NULL DEFAULT 5,
            days_of_week TEXT NOT NULL DEFAULT '[1,2,3,4,5]',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS delay_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alarm_id INTEGER NOT NULL,
            train_number TEXT NOT NULL,
            check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scheduled_departure TEXT,
            actual_delay_min INTEGER,
            api_source TEXT,
            api_success INTEGER NOT NULL DEFAULT 0,
            failsafe_triggered INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (alarm_id) REFERENCES alarms(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# --- Alarms CRUD ---

def create_alarm(train_number, departure_station, arrival_station,
                 scheduled_departure, base_wake_time, safe_wake_time,
                 prep_minutes=30, delay_tolerance_minutes=5, days_of_week=None, name=None):
    if days_of_week is None:
        days_of_week = [1, 2, 3, 4, 5]
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO alarms
           (name, train_number, departure_station, arrival_station,
            scheduled_departure, base_wake_time, safe_wake_time,
            prep_minutes, delay_tolerance_minutes, days_of_week)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, train_number, departure_station, arrival_station,
         scheduled_departure, base_wake_time, safe_wake_time,
         prep_minutes, delay_tolerance_minutes, json.dumps(days_of_week))
    )
    alarm_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alarm_id


def get_alarm(alarm_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM alarms WHERE id = ?", (alarm_id,)).fetchone()
    conn.close()
    if row:
        return _row_to_alarm(row)
    return None


def get_all_alarms():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM alarms ORDER BY base_wake_time").fetchall()
    conn.close()
    return [_row_to_alarm(r) for r in rows]


def get_active_alarms():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alarms WHERE is_active = 1 ORDER BY base_wake_time"
    ).fetchall()
    conn.close()
    return [_row_to_alarm(r) for r in rows]


def update_alarm(alarm_id, **kwargs):
    if "days_of_week" in kwargs and isinstance(kwargs["days_of_week"], list):
        kwargs["days_of_week"] = json.dumps(kwargs["days_of_week"])
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [alarm_id]
    conn = get_connection()
    conn.execute(f"UPDATE alarms SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_alarm(alarm_id):
    conn = get_connection()
    conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
    conn.commit()
    conn.close()


def toggle_alarm(alarm_id):
    conn = get_connection()
    conn.execute(
        "UPDATE alarms SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (alarm_id,)
    )
    conn.commit()
    conn.close()


# --- Delay History ---

def record_delay(alarm_id, train_number, scheduled_departure,
                 actual_delay_min, api_source, api_success, failsafe_triggered):
    conn = get_connection()
    conn.execute(
        """INSERT INTO delay_history
           (alarm_id, train_number, scheduled_departure,
            actual_delay_min, api_source, api_success, failsafe_triggered)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (alarm_id, train_number, scheduled_departure,
         actual_delay_min, api_source, int(api_success), int(failsafe_triggered))
    )
    conn.commit()
    conn.close()


def get_delay_stats(train_number, days=14):
    """Get delay statistics for a train over the last N days."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT actual_delay_min, api_success
           FROM delay_history
           WHERE train_number = ?
             AND api_success = 1
             AND check_time >= datetime('now', ?)
           ORDER BY check_time DESC""",
        (train_number, f"-{days} days")
    ).fetchall()
    conn.close()

    if not rows:
        return {"total_checks": 0, "avg_delay": 0, "max_delay": 0,
                "delay_over_5": 0, "delay_over_10": 0, "pct_over_5": 0, "pct_over_10": 0}

    delays = [r["actual_delay_min"] for r in rows if r["actual_delay_min"] is not None]
    total = len(delays)
    if total == 0:
        return {"total_checks": len(rows), "avg_delay": 0, "max_delay": 0,
                "delay_over_5": 0, "delay_over_10": 0, "pct_over_5": 0, "pct_over_10": 0}

    over_5 = sum(1 for d in delays if d > 5)
    over_10 = sum(1 for d in delays if d > 10)

    return {
        "total_checks": total,
        "avg_delay": round(sum(delays) / total, 1),
        "max_delay": max(delays),
        "delay_over_5": over_5,
        "delay_over_10": over_10,
        "pct_over_5": round(over_5 / total * 100),
        "pct_over_10": round(over_10 / total * 100),
    }


# --- Helpers ---

def _row_to_alarm(row):
    d = dict(row)
    d["days_of_week"] = json.loads(d["days_of_week"])
    return d
