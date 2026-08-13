def charge_card(customer_id, amount):
    _log_charge(customer_id, amount)
    return True


def _log_charge(customer_id, amount):
    print(f"charge {customer_id} {amount}")
