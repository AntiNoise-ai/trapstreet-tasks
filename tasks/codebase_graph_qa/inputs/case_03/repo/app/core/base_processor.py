class BaseProcessor:
    def run(self, item):
        self.validate(item)
        return self.finalize(item)

    def validate(self, item):
        if item is None:
            raise ValueError("empty item")
