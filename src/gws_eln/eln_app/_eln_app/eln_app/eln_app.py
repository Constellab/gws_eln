import reflex as rx
from gws_reflex_main import register_gws_reflex_app

from .locations.locations_page import locations_page
from .materials.materials_page import materials_page
from .suppliers.suppliers_page import suppliers_page

app = register_gws_reflex_app()


@rx.page()
def index():
    """Materials page (home)."""
    return materials_page()


@rx.page(route="/locations")
def locations():
    """Locations page."""
    return locations_page()


@rx.page(route="/suppliers")
def suppliers():
    """Suppliers page."""
    return suppliers_page()
