def notify_customer(customer_id, message):
    _send(customer_id, message)


def _send(customer_id, message):
    print(f"-> {customer_id}: {message}")
