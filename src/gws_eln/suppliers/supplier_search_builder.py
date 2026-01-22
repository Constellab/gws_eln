from gws_core import SearchBuilder

from gws_eln.suppliers.supplier import Supplier


class SupplierSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Supplier, default_orders=[Supplier.name])

    def add_name_filter(self, name: str) -> "SupplierSearchBuilder":
        """Filter the search query by supplier name (case-insensitive contains)"""
        like_pattern = f"%{name}%"
        self.add_expression(Supplier.name.ilike(like_pattern))
        return self
