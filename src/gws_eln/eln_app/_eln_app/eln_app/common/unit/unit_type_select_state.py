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
            UnitTypeSelectDTO(value=UnitType.COUNT.value, label="Count (pcs, cells, copies, CFU)"),
            UnitTypeSelectDTO(value=UnitType.MASS.value, label="Mass (kg, g, mg, µg, ng)"),
            UnitTypeSelectDTO(value=UnitType.VOLUME.value, label="Volume (L, mL, µL, nL)"),
            UnitTypeSelectDTO(value=UnitType.LENGTH.value, label="Length (m, cm, mm, µm)"),
            UnitTypeSelectDTO(
                value=UnitType.MOLE.value, label="Amount of substance (mol, mmol, µmol, nmol, pmol)"
            ),
        ]
