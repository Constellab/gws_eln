import reflex as rx
from gws_reflex_main.gws_components import input_search_component
from reflex.vars import Var

from .material_select_state import MaterialSelectState


def material_select_component(
    placeholder: str = "Search a material...",
    selected_item: Var | None = None,
    item_selected: rx.EventHandler | None = None,
) -> rx.Component:
    """
    Reusable material search component.

    This component provides autocomplete functionality with search-as-you-type
    for selecting materials.

    Args:
        placeholder: Placeholder text for the search input
        selected_item: Optional state var for selected item. If not provided,
            uses MaterialSelectState.selected_material
        item_selected: Optional event handler for item selection. If not provided,
            uses MaterialSelectState.select_material

    Returns:
        A reflex component for material selection with search

    Example:
        # Basic usage with internal state
        material_select_component(
            placeholder="Search materials...",
        )

        # With custom state binding
        material_select_component(
            selected_item=MyState.selected_material,
            item_selected=MyState.handle_material_selected,
        )
    """
    return input_search_component(
        search_result=MaterialSelectState.search_results,
        selected_item=selected_item,
        item_selected=item_selected,
        search_trigger=MaterialSelectState.search_materials,
        placeholder=placeholder,
    )
