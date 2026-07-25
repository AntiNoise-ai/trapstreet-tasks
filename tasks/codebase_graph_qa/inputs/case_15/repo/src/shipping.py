def get_shipping_cost(order_id):
    """Returns the shipping cost for an order. Unrelated to delivery dates."""
    return 0


def track_package(tracking_number):
    """Looks up the current package location for a tracking number. Also unrelated to delivery dates."""
    return "in transit"
