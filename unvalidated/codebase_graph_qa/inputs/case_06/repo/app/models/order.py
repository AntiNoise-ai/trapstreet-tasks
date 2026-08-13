from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.customer import Customer  # only for type hints, never executes at runtime


class Order:
    def __init__(self, customer_id):
        self.customer_id = customer_id

    def total(self):
        from app.pricing.calculator import compute_total  # real runtime import
        return compute_total(self)
