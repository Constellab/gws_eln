"""Search state for the Transform input dialog.

Provides two independent, filtered item searches: one restricted to consumable
items, one restricted to non-consumable items (instruments). Each feeds its own
dropdown so the user picks the input type explicitly.
"""

import reflex as rx
from gws_core import PageDTO
from gws_eln.items.item_search_builder import ItemSearchBuilder
from gws_reflex_main.gws_components import InputSearchResultDTO

from ..core.item_select_state import SearchParam
from .transform_item_form_dialog_state import TransformItemFormDialogState


def _to_result(item) -> InputSearchResultDTO:
    display_text = f"{item.code} ({item.label})" if item.label else item.code
    return InputSearchResultDTO(id=item.id, display_text=display_text, object=item.to_dto())


class TransformInputSelectState(rx.State):
    """Two filtered item searches (consumable / instrument) for the input dialog.

    Items already added as inputs are excluded from the results (so the same item
    can't be added twice), except the one currently being edited.
    """

    consumable_results: rx.Field[PageDTO[InputSearchResultDTO] | None] = rx.field(None)
    instrument_results: rx.Field[PageDTO[InputSearchResultDTO] | None] = rx.field(None)

    async def _search(self, query: dict, is_consumable: bool):
        search_param = SearchParam.from_json(query)

        transform_state = await self.get_state(TransformItemFormDialogState)
        excluded_ids = [
            row.item_id
            for row in transform_state.inputs
            if row.id != transform_state._editing_input_id
        ]

        search_builder = ItemSearchBuilder()
        search_builder.add_active_only_filter()
        search_builder.add_consumable_filter(is_consumable)
        search_builder.add_exclude_ids_filter(excluded_ids)
        if search_param.search_text:
            search_builder.add_label_or_code_filter(search_param.search_text)
        result = search_builder.search_page(
            page=search_param.page, number_of_items_per_page=search_param.page_size
        )
        return result.map_page(_to_result)

    @rx.event
    async def search_consumables(self, query: dict):
        """Search consumable items not already used as inputs."""
        self.consumable_results = await self._search(query, True)

    @rx.event
    async def search_instruments(self, query: dict):
        """Search instruments (non-consumable) not already used as inputs."""
        self.instrument_results = await self._search(query, False)
