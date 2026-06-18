import reflex as rx
from gws_reflex_main.gws_components import input_search_component

from .instrument_select_state import InstrumentSelectState


def instrument_select_component(
    placeholder: str = "Search an instrument...",
    item_selected: rx.EventHandler | None = None,
    disabled: bool = False,
    **kwargs,
) -> rx.Component:
    """Reusable search component restricted to active non-consumable items.

    Autocomplete search-as-you-type for picking INSTRUMENT inputs. Only active
    non-consumable items (instruments/equipment) are proposed.

    Args:
        placeholder: Placeholder text for the search input
        item_selected: Event handler called when an instrument is picked
        disabled: Whether the input is disabled
    """
    return input_search_component(
        search_result=InstrumentSelectState.search_results,
        selected_item=None,
        item_selected=item_selected,
        search_trigger=InstrumentSelectState.search_instruments,
        placeholder=placeholder,
        disabled=disabled,
        min_input_search_length=0,
        init_search_on_focus=True,
        **kwargs,
    )
