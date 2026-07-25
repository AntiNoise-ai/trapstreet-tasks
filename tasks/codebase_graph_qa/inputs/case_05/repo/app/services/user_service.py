def get_user(user_id):
    from app.services.order_service import get_orders_for_user  # local import to avoid a circular import
    orders = get_orders_for_user(user_id)
    return {"id": user_id, "orders": orders}
