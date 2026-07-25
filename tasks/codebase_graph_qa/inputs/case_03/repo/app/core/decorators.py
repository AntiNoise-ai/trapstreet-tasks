import functools


def with_logging(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _audit(func.__name__)
        return func(*args, **kwargs)
    return wrapper


def _audit(name):
    print(f"audit: {name}")
