"""Based Budik - Flask application"""

from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for

import config
import database


def compute_safe_wake_time(base_wake_time: str) -> str:
    """Vypočítá failsafe čas jako base_wake_time - FAILSAFE_OFFSET_MINUTES."""
    t = datetime.strptime(base_wake_time, "%H:%M")
    safe = t - timedelta(minutes=config.FAILSAFE_OFFSET_MINUTES)
    return safe.strftime("%H:%M")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.context_processor
def inject_config():
    return {"config": config}


@app.before_request
def ensure_db():
    database.init_db()


# --- Dashboard ---

@app.route("/")
def dashboard():
    alarms = database.get_all_alarms()
    # Attach delay stats to each alarm
    for alarm in alarms:
        alarm["stats"] = database.get_delay_stats(alarm["train_number"])
    return render_template("dashboard.html", alarms=alarms, active_tab="alarms")


# --- Alarm CRUD ---

@app.route("/alarm/new", methods=["GET", "POST"])
def alarm_new():
    if request.method == "POST":
        days = request.form.getlist("days_of_week")
        days = [int(d) for d in days] if days else [1, 2, 3, 4, 5]
        base_wake_time = request.form["base_wake_time"]
        database.create_alarm(
            train_number=request.form["train_number"],
            departure_station=request.form["departure_station"],
            arrival_station=request.form["arrival_station"],
            scheduled_departure=request.form["scheduled_departure"],
            base_wake_time=base_wake_time,
            safe_wake_time=compute_safe_wake_time(base_wake_time),
            prep_minutes=int(request.form.get("prep_minutes", 30)),
            delay_tolerance_minutes=int(request.form.get("delay_tolerance_minutes", 5)),
            days_of_week=days,
            name=request.form.get("name") or None,
        )
        return redirect(url_for("dashboard"))
    return render_template("alarm_form.html", alarm=None, active_tab="new")


@app.route("/alarm/<int:alarm_id>/edit", methods=["GET", "POST"])
def alarm_edit(alarm_id):
    alarm = database.get_alarm(alarm_id)
    if not alarm:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        days = request.form.getlist("days_of_week")
        days = [int(d) for d in days] if days else [1, 2, 3, 4, 5]
        base_wake_time = request.form["base_wake_time"]
        database.update_alarm(
            alarm_id,
            name=request.form.get("name") or None,
            train_number=request.form["train_number"],
            departure_station=request.form["departure_station"],
            arrival_station=request.form["arrival_station"],
            scheduled_departure=request.form["scheduled_departure"],
            base_wake_time=base_wake_time,
            safe_wake_time=compute_safe_wake_time(base_wake_time),
            prep_minutes=int(request.form.get("prep_minutes", 30)),
            delay_tolerance_minutes=int(request.form.get("delay_tolerance_minutes", 5)),
            days_of_week=days,
        )
        return redirect(url_for("dashboard"))
    return render_template("alarm_form.html", alarm=alarm, active_tab="alarms")


@app.route("/alarm/<int:alarm_id>/delete", methods=["POST"])
def alarm_delete(alarm_id):
    database.delete_alarm(alarm_id)
    return redirect(url_for("dashboard"))


@app.route("/alarm/<int:alarm_id>/toggle", methods=["POST"])
def alarm_toggle(alarm_id):
    database.toggle_alarm(alarm_id)
    return redirect(url_for("dashboard"))


# --- Setup ---

@app.route("/setup")
def setup_page():
    import macos_util
    checks = {
        "pmset": macos_util.check_pmset_permission(),
        "alarm_sound": macos_util.check_alarm_sound(),
    }
    return render_template("setup.html", active_tab="setup", checks=checks)


if __name__ == "__main__":
    database.init_db()
    app.run(host=config.HOST, port=config.PORT, debug=True)
