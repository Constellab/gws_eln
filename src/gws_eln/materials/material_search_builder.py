from gws_core import SearchBuilder

from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material import Material
from gws_eln.suppliers.supplier import Supplier


class MaterialSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Material, default_orders=[Material.name])

    def add_name_filter(self, name: str) -> "MaterialSearchBuilder":
        """Filter the search query by material name (case-insensitive contains)"""
        like_pattern = f"%{name}%"
        self.add_expression(Material.name.ilike(like_pattern))
        return self

    def add_is_consumable_filter(self, is_consumable: bool) -> "MaterialSearchBuilder":
        """Filter the search query by consumable status"""
        self.add_expression(Material.is_consumable == is_consumable)
        return self

    def add_supplier_filter(self, supplier_id: str) -> "MaterialSearchBuilder":
        """Filter the search query by default supplier ID"""
        self.add_expression(Material.default_supplier == supplier_id)
        return self

    def add_supplier_join_filter(self, supplier_name: str) -> "MaterialSearchBuilder":
        """Filter the search query by supplier name (joins with Supplier table)"""
        like_pattern = f"%{supplier_name}%"
        self.add_join(Supplier, on=(Supplier.id == Material.default_supplier))
        self.add_expression(Supplier.name.ilike(like_pattern))
        return self

    def add_unit_type_filter(self, unit_type: UnitType) -> "MaterialSearchBuilder":
        """Filter the search query by default unit type"""
        self.add_expression(Material.default_unit_type == unit_type)
        return self
