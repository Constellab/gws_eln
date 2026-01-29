from dataclasses import dataclass

import reflex as rx
from gws_eln.suppliers.supplier import Supplier


@dataclass
class SupplierSelectDTO:
    value: str
    label: str


class SupplierSelectState(rx.State):
    """State for managing supplier selection and loading suppliers from database."""

    _suppliers: list[SupplierSelectDTO] = []

    @rx.var
    def suppliers(self) -> list[SupplierSelectDTO]:
        """Load all suppliers from the database, sorted by name."""
        if not self._suppliers:
            supplier_list = list(Supplier.select().order_by(Supplier.name))
            self._suppliers = [
                SupplierSelectDTO(
                    value=str(supplier.id),
                    label=supplier.name,
                )
                for supplier in supplier_list
            ]

        return self._suppliers
