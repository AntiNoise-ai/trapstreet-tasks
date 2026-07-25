from app.services.payment_service import charge_card as pay
from app.services.notification_service import notify_customer


def handle_webhook(event):
    if event.type == "payment.requested":
        pay(event.customer_id, event.amount)
        notify_customer(event.customer_id, "charged")
    return {"status": "ok"}
