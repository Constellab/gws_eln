from dataclasses import dataclass

import reflex as rx
from gws_eln.suppliers.supplier import Supplier


@dataclass
class SupplierSelectDTO:
    value: str
    label: str


class SupplierSelectState(rx.State):
    """State for managing supplier selection and loading suppliers from database."""

    @rx.var
    def suppliers(self) -> list[SupplierSelectDTO]:
        """Load all suppliers from the database, sorted by name."""
        supplier_list = list(Supplier.select().order_by(Supplier.name))
        return [
            SupplierSelectDTO(
                value=str(supplier.id),
                label=supplier.name,
            )
            for supplier in supplier_list
        ]
