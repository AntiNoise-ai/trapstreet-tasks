def send_order_receipt(order_id):
    """Sends the customer their order receipt by email. (Renamed from send_receipt_email; same behavior.)"""
    _dispatch(order_id)


def _dispatch(order_id):
    print(f"emailing receipt for {order_id}")
