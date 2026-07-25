from app.services.ledger_service import record_transaction


def charge_card(customer_id, amount):
    record_transaction(customer_id, amount, kind="charge")
    return True
