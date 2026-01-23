import reflex as rx
from gws_reflex_main import register_gws_reflex_app

from .locations.locations_list_state import LocationsListState
from .locations.locations_page import locations_page
from .materials.material_detail_page import material_detail_page
from .materials.material_detail_state import MaterialDetailState
from .materials.materials_list_state import MaterialsListState
from .materials.materials_page import materials_page
from .suppliers.suppliers_list_state import SuppliersListState
from .suppliers.suppliers_page import suppliers_page

app = register_gws_reflex_app()


@rx.page(on_load=[MaterialsListState.on_load])
def index():
    """Materials page (home)."""
    return materials_page()


@rx.page(route="/locations", on_load=[LocationsListState.on_load])
def locations():
    """Locations page."""
    return locations_page()


@rx.page(route="/suppliers", on_load=[SuppliersListState.on_load])
def suppliers():
    """Suppliers page."""
    return suppliers_page()


@rx.page(route="/materials/[material_id]", on_load=[MaterialDetailState.on_load])
def material_detail():
    """Material detail page."""
    return material_detail_page()
