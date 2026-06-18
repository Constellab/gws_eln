from gws_core import SearchBuilder
from gws_eln.items.item import Item
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_status import ItemStatus


class ItemSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Item, default_orders=[Item.code.asc()])

    def add_item_sheet_filter(self, item_sheet_id: str) -> "ItemSearchBuilder":
        """Filter the search query by item sheet ID"""
        self.add_expression(Item.item_sheet == item_sheet_id)
        return self

    def add_consumable_filter(self, is_consumable: bool) -> "ItemSearchBuilder":
        """Filter by the item sheet's consumable flag (joins ItemSheet).

        Use ``add_consumable_filter(False)`` to restrict to non-consumable items
        (instruments/equipment), e.g. when picking INSTRUMENT inputs.
        """
        self.add_join(ItemSheet, on=(Item.item_sheet == ItemSheet.id))
        self.add_expression(ItemSheet.is_consumable == is_consumable)
        return self

    def add_location_filter(self, location_id: str) -> "ItemSearchBuilder":
        """Filter the search query by location ID"""
        self.add_expression(Item.location == location_id)
        return self

    def add_supplier_filter(self, supplier_id: str) -> "ItemSearchBuilder":
        """Filter the search query by supplier ID"""
        self.add_expression(Item.supplier == supplier_id)
        return self

    def add_code_filter(self, code: str) -> "ItemSearchBuilder":
        """Filter the search query by code (case-insensitive contains)"""
        like_pattern = f"%{code}%"
        self.add_expression(Item.code.ilike(like_pattern))
        return self

    def add_label_filter(self, label: str) -> "ItemSearchBuilder":
        """Filter the search query by label (case-insensitive contains)"""
        like_pattern = f"%{label}%"
        self.add_expression(Item.label.ilike(like_pattern))
        return self

    def add_label_or_code_filter(self, text: str) -> "ItemSearchBuilder":
        """Filter the search query by label or code (case-insensitive contains)"""
        like_pattern = f"%{text}%"
        self.add_expression(
            (Item.label.ilike(like_pattern)) | (Item.code.ilike(like_pattern))
        )
        return self

    def add_notes_filter(self, notes: str) -> "ItemSearchBuilder":
        """Filter the search query by notes (case-insensitive contains)"""
        like_pattern = f"%{notes}%"
        self.add_expression(Item.notes.ilike(like_pattern))
        return self

    def add_status_filter(self, status: ItemStatus) -> "ItemSearchBuilder":
        """Filter the search query by item status"""
        self.add_expression(Item.status == status)
        return self

    def add_active_only_filter(self) -> "ItemSearchBuilder":
        """Filter to only include active items"""
        self.add_expression(Item.status == ItemStatus.ACTIVE)
        return self
