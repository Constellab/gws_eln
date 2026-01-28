from dataclasses import dataclass

import reflex as rx
from gws_eln.materials.material import Material


@dataclass
class MaterialSelectDTO:
    value: str
    label: str


class MaterialSelectState(rx.State):
    """State for managing material selection and loading materials from database."""

    _materials: list[MaterialSelectDTO] = []

    @rx.var
    def materials(self) -> list[MaterialSelectDTO]:
        """Load all materials from the database, sorted by name."""
        if not self._materials:
            material_list = list(
                Material.select()
                .order_by(Material.name)
            )
            self._materials = [
                MaterialSelectDTO(
                    value=str(material.id),
                    label=material.name,
                )
                for material in material_list
            ]

        return self._materials
