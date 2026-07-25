import os


def refund(amount):
    timeout = int(os.environ.get("PAYMENT_TIMEOUT_MS", "3000"))
    return True
