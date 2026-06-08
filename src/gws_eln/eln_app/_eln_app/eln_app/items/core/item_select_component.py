import reflex as rx
from gws_reflex_main.gws_components import input_search_component
from reflex.vars import Var

from .item_select_state import ItemSelectState


def item_select_component(
    placeholder: str = "Search an item...",
    selected_item: Var | None = None,
    item_selected: rx.EventHandler | None = None,
    disabled: bool = False,
    **kwargs,
) -> rx.Component:
    """
    Reusable item search component.

    This component provides autocomplete functionality with search-as-you-type
    for selecting items.

    Args:
        placeholder: Placeholder text for the search input
        selected_item: Optional state var for selected item. If not provided,
            uses ItemSelectState.selected_item
        item_selected: Optional event handler for item selection. If not provided,
            uses ItemSelectState.select_item

    Returns:
        A reflex component for item selection with search

    Example:
        # Basic usage with internal state
        item_select_component(
            placeholder="Search items...",
        )

        # With custom state binding
        item_select_component(
            selected_item=MyState.selected_item,
            item_selected=MyState.handle_item_selected,
        )

        # Disabled state (read-only display)
        item_select_component(
            selected_item=MyState.selected_item,
            item_selected=MyState.handle_item_selected,
            disabled=True,
        )
    """
    # Use provided values or fall back to ItemSelectState defaults

    return input_search_component(
        search_result=ItemSelectState.search_results,
        selected_item=selected_item,
        item_selected=item_selected,
        search_trigger=ItemSelectState.search_items,
        placeholder=placeholder,
        disabled=disabled,
        min_input_search_length=0,
        init_search_on_focus=True,
        **kwargs,
    )
