def post_entry(order_id, amount):
    _write(order_id, amount)


def _write(order_id, amount):
    print(f"ledger: {order_id} {amount}")


def reconcile_all():
    # scheduled job, unrelated to OrderProcessor.run
    print("reconciling")
