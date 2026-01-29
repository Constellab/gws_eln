import reflex as rx
from gws_core.core.model.model_dto import BaseModelDTO, PageDTO
from gws_eln.materials.material_batch_search_builder import MaterialBatchSearchBuilder
from gws_reflex_main.gws_components import InputSearchResultDTO


class SearchParam(BaseModelDTO):
    """DTO for search parameters."""

    search_text: str
    page: int
    page_size: int


class BatchSelectState(rx.State):
    """State for managing material batch search and selection."""

    search_results: PageDTO | None = None

    @rx.event
    def search_batches(self, query: dict):
        """Search batches based on the query.

        :param query: The search query containing search_text, page, and page_size
        """
        search_param = SearchParam.from_json(query)

        search_builder = MaterialBatchSearchBuilder()
        search_builder.add_active_only_filter()

        if search_param.search_text:
            search_builder.add_label_or_batch_number_filter(search_param.search_text)

        result = search_builder.search_page(
            page=search_param.page, number_of_items_per_page=search_param.page_size
        )

        def get_display_text(batch) -> str:
            if batch.label:
                return f"{batch.batch_number} ({batch.label})"
            return batch.batch_number

        self.search_results = result.map_page(
            lambda batch: InputSearchResultDTO(
                id=batch.id,
                display_text=get_display_text(batch),
                object=batch.to_dto(),
            )
        )
