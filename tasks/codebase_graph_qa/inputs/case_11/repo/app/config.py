import os


class Settings:
    def __init__(self):
        self.RETRY_LIMIT = int(os.environ.get("RETRY_LIMIT", "3"))
        self.QUEUE_NAME = os.environ.get("QUEUE_NAME", "default")


settings = Settings()
