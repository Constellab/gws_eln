import reflex as rx
from gws_core import BaseModelDTO, PageDTO
from gws_eln.materials.material_search_builder import MaterialSearchBuilder
from gws_reflex_main.gws_components import InputSearchResultDTO


class SearchParam(BaseModelDTO):
    """DTO for search parameters."""

    search_text: str
    page: int
    page_size: int


class MaterialSelectState(rx.State):
    """State for managing material search and selection."""

    search_results: PageDTO | None = None

    @rx.event
    def search_materials(self, query: dict):
        """Search materials based on the query.

        :param query: The search query containing search_text, page, and page_size
        """
        search_param = SearchParam.from_json(query)

        search_builder = MaterialSearchBuilder()

        if search_param.search_text:
            search_builder.add_name_filter(search_param.search_text)

        result = search_builder.search_page(
            page=search_param.page, number_of_items_per_page=search_param.page_size
        )

        self.search_results = result.map_page(
            lambda material: InputSearchResultDTO(
                id=material.id,
                display_text=material.name,
                object=material.to_dto(),
            )
        )
