"""Based Budik - Flask aplikace"""

from flask import Flask, render_template, request, redirect, url_for

import alarm_logic
import api_handler
import config
import database

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
    for alarm in alarms:
        alarm["stats"] = database.get_delay_stats(alarm["train_number"])
        alarm["last_check"] = database.get_last_check(alarm["id"])
        alarm["check_time"] = alarm_logic.compute_check_time(
            alarm["safe_wake_time"], alarm["check_before_minutes"]
        )
    return render_template("dashboard.html", alarms=alarms, active_tab="alarms")


# --- Alarm CRUD ---

@app.route("/alarm/new", methods=["GET", "POST"])
def alarm_new():
    if request.method == "POST":
        days = request.form.getlist("days_of_week")
        days = [int(d) for d in days] if days else [1, 2, 3, 4, 5]
        alarm_id = database.create_alarm(
            train_number=request.form["train_number"],
            departure_station=request.form["departure_station"],
            arrival_station=request.form["arrival_station"],
            scheduled_departure=request.form["scheduled_departure"],
            base_wake_time=request.form["base_wake_time"],
            safe_wake_time=request.form["safe_wake_time"],
            check_before_minutes=int(request.form.get("check_before_minutes", 5)),
            delay_tolerance_minutes=int(request.form.get("delay_tolerance_minutes", 0)),
            days_of_week=days,
            name=request.form.get("name") or None,
        )
        _auto_check_if_needed(alarm_id)
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
        database.update_alarm(
            alarm_id,
            name=request.form.get("name") or None,
            train_number=request.form["train_number"],
            departure_station=request.form["departure_station"],
            arrival_station=request.form["arrival_station"],
            scheduled_departure=request.form["scheduled_departure"],
            base_wake_time=request.form["base_wake_time"],
            safe_wake_time=request.form["safe_wake_time"],
            check_before_minutes=int(request.form.get("check_before_minutes", 5)),
            delay_tolerance_minutes=int(request.form.get("delay_tolerance_minutes", 0)),
            days_of_week=days,
        )
        _auto_check_if_needed(alarm_id)
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


# --- Manuální / automatická kontrola zpoždění ---

@app.route("/alarm/<int:alarm_id>/check", methods=["POST"])
def alarm_check(alarm_id):
    use_failsafe = _run_check(alarm_id)
    alarm = database.get_alarm(alarm_id)
    if alarm:
        import macos_util
        if use_failsafe:
            macos_util.notify("Based Budík – dřívější spoj",
                              f"Vstáváš v {alarm['safe_wake_time']} – API selhalo nebo velké zpoždění")
        else:
            macos_util.notify("Based Budík – vše v pořádku",
                              f"Vlak jede dobře, vstáváš v {alarm['base_wake_time']}")
        # Zvuk NE – zavoní scheduler přesně v čase buzení
    return redirect(url_for("dashboard"))


def _auto_check_if_needed(alarm_id: int):
    """Spustí kontrolu okamžitě pokud jsme v okně check_time..base_wake_time."""
    alarm = database.get_alarm(alarm_id)
    if alarm and alarm_logic.should_auto_check_now(alarm):
        _run_check(alarm_id)


def _run_check(alarm_id: int) -> bool:
    """
    Provede kontrolu zpoždění a uloží výsledek.
    Vrací True = použij failsafe, False = standard.
    """
    alarm = database.get_alarm(alarm_id)
    if not alarm:
        return True

    delay_min, api_success, api_source = api_handler.get_delay(
        alarm["train_number"], alarm["departure_station"]
    )
    use_failsafe = alarm_logic.should_use_failsafe(
        delay_min, api_success, alarm["delay_tolerance_minutes"]
    )
    database.record_delay(
        alarm_id=alarm_id,
        train_number=alarm["train_number"],
        scheduled_departure=alarm["scheduled_departure"],
        actual_delay_min=delay_min,
        api_source=api_source,
        api_success=api_success,
        failsafe_triggered=use_failsafe,
    )
    return use_failsafe


# --- Nastavení ---

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
