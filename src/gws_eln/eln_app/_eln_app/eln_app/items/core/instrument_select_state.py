import reflex as rx
from gws_core import BaseModelDTO, PageDTO
from gws_eln.items.item_search_builder import ItemSearchBuilder
from gws_reflex_main.gws_components import InputSearchResultDTO


class InstrumentSearchParam(BaseModelDTO):
    """DTO for instrument search parameters."""

    search_text: str
    page: int
    page_size: int


class InstrumentSelectState(rx.State):
    """State for searching non-consumable items to use as INSTRUMENT inputs.

    Mirrors ItemSelectState but restricts results to active, non-consumable
    items (instruments/equipment), the only items allowed as INSTRUMENT inputs.
    """

    search_results: rx.Field[PageDTO[InputSearchResultDTO] | None] = rx.field(None)

    @rx.event
    def search_instruments(self, query: dict):
        """Search active non-consumable items based on the query.

        :param query: The search query containing search_text, page, and page_size
        """
        search_param = InstrumentSearchParam.from_json(query)

        search_builder = ItemSearchBuilder.build_filtered(
            active_only=True,
            is_consumable=False,
            search_text=search_param.search_text,
        )

        result = search_builder.search_page(
            page=search_param.page, number_of_items_per_page=search_param.page_size
        )

        def get_display_text(item) -> str:
            if item.label:
                return f"{item.code} ({item.label})"
            return item.code

        self.search_results = result.map_page(
            lambda item: InputSearchResultDTO(
                id=item.id,
                display_text=get_display_text(item),
                object=item.to_dto(),
            )
        )
