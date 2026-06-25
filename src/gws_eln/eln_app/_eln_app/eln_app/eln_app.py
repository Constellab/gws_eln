import reflex as rx
import reflex_enterprise as rxe
from gws_reflex_main import register_gws_reflex_app

from .item_sheets.item_sheet_detail_page import item_sheet_detail_page
from .item_sheets.item_sheet_detail_state import ItemSheetDetailState
from .item_sheets.item_sheets_list_state import ItemSheetsListState
from .item_sheets.item_sheets_page import item_sheets_page
from .items.item_detail_page import item_detail_page
from .items.item_detail_state import ItemDetailState
from .locations.locations_list_state import LocationsListState
from .locations.locations_page import locations_page
from .notes.note_detail_page import note_detail_page
from .notes.note_detail_state import NoteDetailState
from .notes.notes_list_state import NotesListState
from .notes.notes_page import notes_page
from .suppliers.suppliers_list_state import SuppliersListState
from .suppliers.suppliers_page import suppliers_page

app = register_gws_reflex_app(rxe.App())


@rx.page(route="/", on_load=[NotesListState.on_load])
def notes():
    """Notes page."""
    return notes_page()


@rx.page(route="/item_sheets", on_load=[ItemSheetsListState.on_load])
def index():
    """ItemSheets page (home)."""
    return item_sheets_page()


@rx.page(route="/locations", on_load=[LocationsListState.on_load])
def locations():
    """Locations page."""
    return locations_page()


@rx.page(route="/suppliers", on_load=[SuppliersListState.on_load])
def suppliers():
    """Suppliers page."""
    return suppliers_page()


@rx.page(route="/item_sheets/[item_sheet_id]", on_load=[ItemSheetDetailState.on_load])
def item_sheet_detail():
    """ItemSheet detail page."""
    return item_sheet_detail_page()


@rx.page(route="/notes/[note_id]", on_load=[NoteDetailState.on_load])
def note_detail():
    """Note detail page."""
    return note_detail_page()


@rx.page(route="/items/[item_id]", on_load=[ItemDetailState.on_load])
def item_detail():
    """Item detail page."""
    return item_detail_page()
