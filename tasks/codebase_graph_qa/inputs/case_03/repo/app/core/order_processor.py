from app.core.base_processor import BaseProcessor
from app.core.decorators import with_logging
from app.core.ledger import post_entry


class OrderProcessor(BaseProcessor):
    @with_logging
    def finalize(self, item):
        post_entry(item.id, item.total)
        return "finalized"
