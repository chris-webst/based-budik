"""Based Budik - API handler pro zpoždění vlaků

Stub verze – vrací None (API nenalezeno) dokud neimplementujeme cd.cz v kroku 3.
Scheduler a alarm_logic s tím počítají: None api_success=False -> failsafe.
"""


def get_delay(train_number: str, departure_station: str):
    """
    Zjistí zpoždění vlaku.

    Returns:
        (delay_minutes, api_success, api_source)
        delay_minutes: int nebo None (pokud API selhalo)
        api_success:   True pokud API odpovědělo
        api_source:    identifikátor zdroje dat
    """
    # TODO: implementovat v kroku 3 (cd.cz Ticket API)
    return None, False, "stub"
