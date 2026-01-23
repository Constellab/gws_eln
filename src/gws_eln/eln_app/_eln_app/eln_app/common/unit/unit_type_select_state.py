from dataclasses import dataclass

import reflex as rx
from gws_eln.core.unit_type import UnitType


@dataclass
class UnitTypeSelectDTO:
    value: str
    label: str


class UnitTypeSelectState(rx.State):
    """State for managing unit type selection."""

    @rx.var
    def unit_types(self) -> list[UnitTypeSelectDTO]:
        """Get all unit types for the select dropdown."""
        return [
            UnitTypeSelectDTO(value=UnitType.COUNT.value, label="Count (units)"),
            UnitTypeSelectDTO(value=UnitType.MASS.value, label="Mass (g, kg, mg)"),
            UnitTypeSelectDTO(value=UnitType.VOLUME.value, label="Volume (L, mL, uL)"),
            UnitTypeSelectDTO(value=UnitType.LENGTH.value, label="Length (m, cm, mm)"),
        ]
