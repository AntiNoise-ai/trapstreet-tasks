from app.services.payment_service import charge_card
from app.services.inventory_service import reserve_stock


def handle_order(order):
    reserve_stock(order.items)
    charge_card(order.customer_id, order.total)
    return {"status": "ok"}
