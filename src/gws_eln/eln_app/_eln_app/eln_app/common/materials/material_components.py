import reflex as rx
from gws_eln.materials.material_dto import MaterialDTO

from ..eln_app_router import ElnAppRouter


def inline_material_component(material: MaterialDTO) -> rx.Component:
    """Create an inline component for a material link.

    :param material: The material DTO
    :type material: MaterialDTO
    :return: The inline material component
    :rtype: rx.Component
    """
    return rx.link(
        rx.text(material.name, size="2"),
        href=ElnAppRouter.get_material_detail_url(material.id),
    )
