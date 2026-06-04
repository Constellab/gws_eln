from gws_core import SearchBuilder
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.suppliers.supplier import Supplier


class ItemSheetSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(ItemSheet, default_orders=[ItemSheet.name.asc()])

    def add_name_filter(self, name: str) -> "ItemSheetSearchBuilder":
        """Filter the search query by item sheet name (case-insensitive contains)"""
        like_pattern = f"%{name}%"
        self.add_expression(ItemSheet.name.ilike(like_pattern))
        return self

    def add_is_consumable_filter(self, is_consumable: bool) -> "ItemSheetSearchBuilder":
        """Filter the search query by consumable status"""
        self.add_expression(ItemSheet.is_consumable == is_consumable)
        return self

    def add_supplier_filter(self, supplier_id: str) -> "ItemSheetSearchBuilder":
        """Filter the search query by default supplier ID"""
        self.add_expression(ItemSheet.default_supplier == supplier_id)
        return self

    def add_supplier_join_filter(self, supplier_name: str) -> "ItemSheetSearchBuilder":
        """Filter the search query by supplier name (joins with Supplier table)"""
        like_pattern = f"%{supplier_name}%"
        self.add_join(Supplier, on=(Supplier.id == ItemSheet.default_supplier))
        self.add_expression(Supplier.name.ilike(like_pattern))
        return self

    def add_unit_type_filter(self, unit_type: UnitType) -> "ItemSheetSearchBuilder":
        """Filter the search query by default unit type"""
        self.add_expression(ItemSheet.default_unit_type == unit_type)
        return self
