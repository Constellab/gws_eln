import reflex as rx
from gws_core import BaseModelDTO, PageDTO
from gws_eln.items.item_sheet_search_builder import ItemSheetSearchBuilder
from gws_reflex_main.gws_components import InputSearchResultDTO


class SearchParam(BaseModelDTO):
    """DTO for search parameters."""

    search_text: str
    page: int
    page_size: int


class ItemSheetSelectState(rx.State):
    """State for managing item sheet search and selection."""

    search_results: rx.Field[PageDTO[InputSearchResultDTO] | None] = rx.field(None)

    @rx.event
    def search_item_sheets(self, query: dict):
        """Search item sheets based on the query.

        :param query: The search query containing search_text, page, and page_size
        """
        search_param = SearchParam.from_json(query)

        search_builder = ItemSheetSearchBuilder()

        if search_param.search_text:
            search_builder.add_name_filter(search_param.search_text)

        result = search_builder.search_page(
            page=search_param.page, number_of_items_per_page=search_param.page_size
        )

        self.search_results = result.map_page(
            lambda item_sheet: InputSearchResultDTO(
                id=item_sheet.id,
                display_text=item_sheet.name,
                object=item_sheet.to_dto(),
            )
        )
