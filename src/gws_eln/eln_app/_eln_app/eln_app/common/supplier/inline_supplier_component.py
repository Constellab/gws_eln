"""Inline supplier component for displaying supplier info on a single line."""

import reflex as rx
from gws_eln.suppliers.supplier_dto import SupplierDTO


def inline_supplier_component(supplier: SupplierDTO | rx.Var[SupplierDTO]) -> rx.Component:
    """Create an inline component to display supplier information.

    Displays the supplier name on a single line.

    :param supplier: The supplier DTO to display
    :type supplier: SupplierDTO | rx.Var[SupplierDTO]
    :return: The inline supplier component
    :rtype: rx.Component
    """
    return rx.text(supplier.name, size="2")
