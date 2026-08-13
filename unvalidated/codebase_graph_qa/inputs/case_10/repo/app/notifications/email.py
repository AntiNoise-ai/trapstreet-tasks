import os


def send(to):
    timeout = int(os.environ["EMAIL_TIMEOUT_MS"])  # a different key -- not PAYMENT_TIMEOUT_MS
    return True
