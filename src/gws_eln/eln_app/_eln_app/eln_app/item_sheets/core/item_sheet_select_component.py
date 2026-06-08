import reflex as rx
from gws_reflex_main.gws_components import input_search_component
from reflex.vars import Var

from .item_sheet_select_state import ItemSheetSelectState


def item_sheet_select_component(
    placeholder: str = "Search an item sheet...",
    selected_item: Var | None = None,
    item_selected: rx.EventHandler | None = None,
) -> rx.Component:
    """
    Reusable item sheet search component.

    This component provides autocomplete functionality with search-as-you-type
    for selecting item sheets.

    Args:
        placeholder: Placeholder text for the search input
        selected_item: Optional state var for selected item. If not provided,
            uses ItemSheetSelectState.selected_item_sheet
        item_selected: Optional event handler for item selection. If not provided,
            uses ItemSheetSelectState.select_item_sheet

    Returns:
        A reflex component for item sheet selection with search

    Example:
        # Basic usage with internal state
        item_sheet_select_component(
            placeholder="Search item sheets...",
        )

        # With custom state binding
        item_sheet_select_component(
            selected_item=MyState.selected_item_sheet,
            item_selected=MyState.handle_item_sheet_selected,
        )
    """
    return input_search_component(
        search_result=ItemSheetSelectState.search_results,
        selected_item=selected_item,
        item_selected=item_selected,
        search_trigger=ItemSheetSelectState.search_item_sheets,
        placeholder=placeholder,
        min_input_search_length=0,
        init_search_on_focus=True,
    )
