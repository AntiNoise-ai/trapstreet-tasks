from app.api import orders_api
from app.api import health_api as health


def setup():
    orders_api.register()
    health.register()
