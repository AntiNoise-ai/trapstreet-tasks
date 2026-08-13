def reserve_stock(items):
    for item in items:
        _decrement(item)


def _decrement(item):
    item.quantity -= 1
