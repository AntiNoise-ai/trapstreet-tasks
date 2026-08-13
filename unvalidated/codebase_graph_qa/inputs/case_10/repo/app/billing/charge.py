import os


def charge(amount):
    timeout = int(os.environ["PAYMENT_TIMEOUT_MS"])
    return _do_charge(amount, timeout)


def _do_charge(amount, timeout):
    return True
