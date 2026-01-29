import reflex as rx
from gws_reflex_main.gws_components import input_search_component
from reflex.vars import Var

from .batch_select_state import BatchSelectState


def batch_select_component(
    placeholder: str = "Search a batch...",
    selected_item: Var | None = None,
    item_selected: rx.EventHandler | None = None,
    disabled: bool = False,
    **kwargs,
) -> rx.Component:
    """
    Reusable material batch search component.

    This component provides autocomplete functionality with search-as-you-type
    for selecting material batches.

    Args:
        placeholder: Placeholder text for the search input
        selected_item: Optional state var for selected item. If not provided,
            uses BatchSelectState.selected_batch
        item_selected: Optional event handler for item selection. If not provided,
            uses BatchSelectState.select_batch

    Returns:
        A reflex component for material batch selection with search

    Example:
        # Basic usage with internal state
        batch_select_component(
            placeholder="Search batches...",
        )

        # With custom state binding
        batch_select_component(
            selected_item=MyState.selected_batch,
            item_selected=MyState.handle_batch_selected,
        )

        # Disabled state (read-only display)
        batch_select_component(
            selected_item=MyState.selected_batch,
            item_selected=MyState.handle_batch_selected,
            disabled=True,
        )
    """
    # Use provided values or fall back to BatchSelectState defaults

    return input_search_component(
        search_result=BatchSelectState.search_results,
        selected_item=selected_item,
        item_selected=item_selected,
        search_trigger=BatchSelectState.search_batches,
        placeholder=placeholder,
        disabled=disabled,
        **kwargs,
    )
