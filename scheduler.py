"""Scheduler - kontrola zpoždění a nastavení budíků"""

from datetime import datetime, timedelta
from typing import Optional
import logging

import config
import database
import macos_util

logger = logging.getLogger(__name__)


def get_train_delay(train_number: str) -> Optional[int]:
    """
    Vrátí aktuální zpoždění vlaku v minutách, nebo None pokud se nepodaří.
    """
    try:
        import requests
        
        # TODO: Implementujte volání CD API
        # Prozatím vrací None (API chyba = failsafe)
        logger.info(f"Checking delay for train {train_number}")
        return None
    except Exception as e:
        logger.error(f"Failed to check train delay: {e}")
        return None


def check_and_schedule_alarms():
    """
    Kontroluje všechny aktivní budíky a v případě potřeby je naplánuje.
    Spouští se každou minutu.
    """
    try:
        alarms = database.get_active_alarms()
        now = datetime.now()
        today = now.date()
        
        for alarm in alarms:
            # Zkontroluj, zda je dnes активní den
            weekday = today.weekday() + 1  # Python: 0=Monday, weekday: 1=Monday
            if weekday not in alarm["days_of_week"]:
                continue
            
            # Zjisti check_time (CHECK_BEFORE_MINUTES před safe_wake_time)
            safe_time = datetime.strptime(alarm["safe_wake_time"], "%H:%M").time()
            check_time = datetime.combine(today, safe_time) - timedelta(minutes=config.CHECK_BEFORE_MINUTES)
            
            # Zkontroluj, zda je teď čas na check
            if check_time <= now < check_time + timedelta(minutes=1):
                # Zkontroluj, zda už nebyl dnes zkontrolován
                last_check = database.get_alarm_last_check(alarm["id"], today)
                if last_check is None:
                    logger.info(f"Checking alarm {alarm['id']} ({alarm['train_number']}) at {now}")
                    
                    # Zkontroluj zpoždění vlaku
                    actual_delay = get_train_delay(alarm["train_number"])
                    api_success = actual_delay is not None
                    failsafe_triggered = False
                    
                    # Rozhodni, kdy zvonit
                    if actual_delay is None or actual_delay > alarm["delay_tolerance_minutes"]:
                        # Failsafe - zvonit v safe_wake_time
                        wake_time_str = alarm["safe_wake_time"]
                        failsafe_triggered = True
                    else:
                        # Normální čas - zvonit v base_wake_time
                        wake_time_str = alarm["base_wake_time"]
                    
                    wake_time = datetime.combine(today, datetime.strptime(wake_time_str, "%H:%M").time())
                    
                    # Nastav probuzení
                    success = macos_util.schedule_wake(wake_time)
                    logger.info(
                        f"Alarm {alarm['id']}: delay={actual_delay}min, "
                        f"tolerance={alarm['delay_tolerance_minutes']}min, "
                        f"failsafe={failsafe_triggered}, "
                        f"wake_time={wake_time_str}, "
                        f"pmset_success={success}"
                    )
                    
                    # Ulož záznam
                    database.record_delay(
                        alarm_id=alarm["id"],
                        train_number=alarm["train_number"],
                        scheduled_departure=alarm["scheduled_departure"],
                        actual_delay_min=actual_delay,
                        api_source="cd_api",
                        api_success=api_success,
                        failsafe_triggered=failsafe_triggered,
                    )
                    
                    # Markuj, že byl dnes zkontrolován
                    database.set_alarm_last_check(alarm["id"], today)
                    
                    # Spusti zvuk a notifikaci
                    try:
                        macos_util.play_alarm()
                        macos_util.notify(
                            "Budík",
                            f"{alarm.get('name', alarm['train_number'])} v {wake_time_str}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to play alarm or notify: {e}")
    
    except Exception as e:
        logger.error(f"Error in check_and_schedule_alarms: {e}")
