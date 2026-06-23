"""Search state for the Transform output wizard's ItemSheet dropdown.

Restricted to consumable item sheets: a transform output is always a consumable
item, so only consumable sheets may be chosen as its destination.
"""

import reflex as rx
from gws_core import PageDTO
from gws_eln.items.item_sheet_search_builder import ItemSheetSearchBuilder
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...item_sheets.core.item_sheet_select_state import SearchParam


class TransformOutputSheetSelectState(rx.State):
    """Consumable-only item sheet search for the output wizard."""

    results: rx.Field[PageDTO[InputSearchResultDTO] | None] = rx.field(None)

    @rx.event
    def search(self, query: dict):
        """Search consumable item sheets only."""
        search_param = SearchParam.from_json(query)
        search_builder = ItemSheetSearchBuilder()
        search_builder.add_is_consumable_filter(True)
        if search_param.search_text:
            search_builder.add_name_filter(search_param.search_text)
        result = search_builder.search_page(
            page=search_param.page, number_of_items_per_page=search_param.page_size
        )
        self.results = result.map_page(
            lambda item_sheet: InputSearchResultDTO(
                id=item_sheet.id,
                display_text=item_sheet.name,
                object=item_sheet.to_dto(),
            )
        )
