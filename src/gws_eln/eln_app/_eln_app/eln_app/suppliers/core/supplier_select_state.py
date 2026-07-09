from dataclasses import dataclass

import reflex as rx
from gws_eln.suppliers.supplier import Supplier
from gws_reflex_main import ReflexMainState


@dataclass
class SupplierSelectDTO:
    value: str
    label: str


class SupplierSelectState(rx.State):
    """State for managing supplier selection and loading suppliers from database."""

    # Explicit list var (not a computed var) so it can be reliably refreshed
    # after a supplier is created on the fly from another form.
    suppliers: list[SupplierSelectDTO] = []
    _loaded: bool = False

    async def _load(self) -> None:
        """Load all suppliers from the database, sorted by name."""
        main_state = await self.get_state(ReflexMainState)
        try:
            with await main_state.authenticate_user():
                supplier_list = list(Supplier.select().order_by(Supplier.name))
        except Exception:
            self.suppliers = []
            return
        self.suppliers = [
            SupplierSelectDTO(value=str(supplier.id), label=supplier.name)
            for supplier in supplier_list
        ]
        self._loaded = True

    @rx.event
    async def ensure_loaded(self):
        """Load the suppliers once, when a select mounts."""
        if not self._loaded:
            await self._load()

    async def reload(self) -> None:
        """Force the supplier list to be reloaded from the database."""
        await self._load()
