from app.config import settings


def process():
    for _ in range(settings.RETRY_LIMIT):
        _attempt()


def _attempt():
    return True
