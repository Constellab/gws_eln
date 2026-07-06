from __future__ import annotations

from gws_core import SearchBuilder
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_status import ItemStatus


class ItemSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Item, default_orders=[Item.code.asc()])

    @classmethod
    def build_filtered(
        cls,
        *,
        active_only: bool = False,
        is_consumable: bool | None = None,
        has_concentration: bool | None = None,
        item_sheet_id: str | None = None,
        location_id: str | None = None,
        supplier_id: str | None = None,
        status: ItemStatus | None = None,
        unit_type: UnitType | None = None,
        exclude_ids: list[str] | None = None,
        search_text: str | None = None,
    ) -> ItemSearchBuilder:
        """Build an item search with the common item-selection filters.

        Central factory reused by every item list/search state: each parameter is
        optional and a ``None`` (or empty) value means "do not filter on it". So a
        caller wanting active consumables that carry a concentration just passes
        ``active_only=True, is_consumable=True, has_concentration=True``.

        :return: A configured (unexecuted) builder; call ``search_page``/``search_all``.
        :rtype: ItemSearchBuilder
        """
        builder = cls()
        if active_only:
            builder.add_active_only_filter()
        optional_filters = [
            (status, builder.add_status_filter),
            (is_consumable, builder.add_consumable_filter),
            (has_concentration, builder.add_has_concentration_filter),
            (unit_type, builder.add_unit_type_filter),
            (item_sheet_id, builder.add_item_sheet_filter),
            (location_id, builder.add_location_filter),
            (supplier_id, builder.add_supplier_filter),
            (exclude_ids, builder.add_exclude_ids_filter),
            (search_text, builder.add_label_or_code_filter),
        ]
        for value, apply_filter in optional_filters:
            if value is not None and value not in ("", []):
                apply_filter(value)
        return builder

    def add_item_sheet_filter(self, item_sheet_id: str) -> ItemSearchBuilder:
        """Filter the search query by item sheet ID"""
        self.add_expression(Item.item_sheet == item_sheet_id)
        return self

    def add_consumable_filter(self, is_consumable: bool) -> ItemSearchBuilder:
        """Filter by the item sheet's consumable flag (joins ItemSheet).

        Use ``add_consumable_filter(False)`` to restrict to non-consumable items
        (instruments/equipment), e.g. when picking INSTRUMENT inputs.
        """
        self.add_join(ItemSheet, on=(Item.item_sheet == ItemSheet.id))
        self.add_expression(ItemSheet.is_consumable == is_consumable)
        return self

    def add_has_concentration_filter(self, has_concentration: bool) -> ItemSearchBuilder:
        """Filter by whether the item carries a recorded concentration.

        ``True`` keeps only items that have a concentration (e.g. dilute targets
        and concentrate sources); ``False`` keeps only those without one.
        """
        self.add_expression(Item.concentration.is_null(not has_concentration))
        return self

    def add_unit_type_filter(self, unit_type: UnitType) -> ItemSearchBuilder:
        """Filter to items whose quantity is expressed in the given unit type.

        E.g. ``add_unit_type_filter(UnitType.VOLUME)`` to restrict to volume items
        (the only items usable as dilute diluents).
        """
        self.add_expression(Item.unit_type == unit_type)
        return self

    def add_location_filter(self, location_id: str) -> ItemSearchBuilder:
        """Filter the search query by location ID"""
        self.add_expression(Item.location == location_id)
        return self

    def add_supplier_filter(self, supplier_id: str) -> ItemSearchBuilder:
        """Filter the search query by supplier ID"""
        self.add_expression(Item.supplier == supplier_id)
        return self

    def add_code_filter(self, code: str) -> ItemSearchBuilder:
        """Filter the search query by code (case-insensitive contains)"""
        like_pattern = f"%{code}%"
        self.add_expression(Item.code.ilike(like_pattern))
        return self

    def add_label_filter(self, label: str) -> ItemSearchBuilder:
        """Filter the search query by label (case-insensitive contains)"""
        like_pattern = f"%{label}%"
        self.add_expression(Item.label.ilike(like_pattern))
        return self

    def add_label_or_code_filter(self, text: str) -> ItemSearchBuilder:
        """Filter the search query by label or code (case-insensitive contains)"""
        like_pattern = f"%{text}%"
        self.add_expression(
            (Item.label.ilike(like_pattern)) | (Item.code.ilike(like_pattern))
        )
        return self

    def add_notes_filter(self, notes: str) -> ItemSearchBuilder:
        """Filter the search query by notes (case-insensitive contains)"""
        like_pattern = f"%{notes}%"
        self.add_expression(Item.notes.ilike(like_pattern))
        return self

    def add_status_filter(self, status: ItemStatus) -> ItemSearchBuilder:
        """Filter the search query by item status"""
        self.add_expression(Item.status == status)
        return self

    def add_active_only_filter(self) -> ItemSearchBuilder:
        """Filter to only include active items"""
        self.add_expression(Item.status == ItemStatus.ACTIVE)
        return self

    def add_exclude_ids_filter(self, ids: list[str]) -> ItemSearchBuilder:
        """Exclude the given item ids from the results (no-op if the list is empty)."""
        if ids:
            self.add_expression(Item.id.not_in(ids))
        return self
