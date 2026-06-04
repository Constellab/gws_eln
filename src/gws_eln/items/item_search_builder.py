from gws_core import SearchBuilder
from gws_eln.items.item import Item
from gws_eln.items.item_status import ItemStatus


class ItemSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Item, default_orders=[Item.batch_number.asc()])

    def add_item_sheet_filter(self, item_sheet_id: str) -> "ItemSearchBuilder":
        """Filter the search query by item sheet ID"""
        self.add_expression(Item.item_sheet == item_sheet_id)
        return self

    def add_location_filter(self, location_id: str) -> "ItemSearchBuilder":
        """Filter the search query by location ID"""
        self.add_expression(Item.location == location_id)
        return self

    def add_parent_batch_filter(self, parent_batch_id: str) -> "ItemSearchBuilder":
        """Filter the search query by parent batch ID"""
        self.add_expression(Item.parent_item == parent_batch_id)
        return self

    def add_original_batches_only_filter(self) -> "ItemSearchBuilder":
        """Filter to only include original batches (no parent)"""
        self.add_expression(Item.parent_item.is_null(True))
        return self

    def add_aliquots_only_filter(self) -> "ItemSearchBuilder":
        """Filter to only include aliquots (has parent)"""
        self.add_expression(Item.parent_item.is_null(False))
        return self

    def add_supplier_filter(self, supplier_id: str) -> "ItemSearchBuilder":
        """Filter the search query by supplier ID"""
        self.add_expression(Item.supplier == supplier_id)
        return self

    def add_batch_number_filter(self, batch_number: str) -> "ItemSearchBuilder":
        """Filter the search query by batch number (case-insensitive contains)"""
        like_pattern = f"%{batch_number}%"
        self.add_expression(Item.batch_number.ilike(like_pattern))
        return self

    def add_label_filter(self, label: str) -> "ItemSearchBuilder":
        """Filter the search query by label (case-insensitive contains)"""
        like_pattern = f"%{label}%"
        self.add_expression(Item.label.ilike(like_pattern))
        return self

    def add_label_or_batch_number_filter(self, text: str) -> "ItemSearchBuilder":
        """Filter the search query by label or batch number (case-insensitive contains)"""
        like_pattern = f"%{text}%"
        self.add_expression(
            (Item.label.ilike(like_pattern)) | (Item.batch_number.ilike(like_pattern))
        )
        return self

    def add_notes_filter(self, notes: str) -> "ItemSearchBuilder":
        """Filter the search query by notes (case-insensitive contains)"""
        like_pattern = f"%{notes}%"
        self.add_expression(Item.notes.ilike(like_pattern))
        return self

    def add_status_filter(self, status: ItemStatus) -> "ItemSearchBuilder":
        """Filter the search query by batch status"""
        self.add_expression(Item.status == status)
        return self

    def add_active_only_filter(self) -> "ItemSearchBuilder":
        """Filter to only include active batches"""
        self.add_expression(Item.status == ItemStatus.ACTIVE)
        return self
