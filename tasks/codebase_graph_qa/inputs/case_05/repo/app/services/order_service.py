from app.services.pricing_service import total_for_order


def get_orders_for_user(user_id):
    return [total_for_order(o) for o in _fetch(user_id)]


def _fetch(user_id):
    return []
