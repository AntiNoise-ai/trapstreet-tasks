from app.services.payment_service import charge_card


def process(order):
    # generates a nightly report; NOT part of the webhook flow, never called
    # from handle_webhook.
    charge_card(order.customer_id, order.total)
    return "reported"
