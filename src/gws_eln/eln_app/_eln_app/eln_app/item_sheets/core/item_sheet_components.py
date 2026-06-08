import reflex as rx
from gws_eln.items.item_sheet_dto import ItemSheetDTO

from ...common.eln_app_router import ElnAppRouter


def inline_item_sheet_link(item_sheet: ItemSheetDTO) -> rx.Component:
    """Create an inline component for a item sheet link.

    :param item_sheet: The item sheet DTO
    :type item_sheet: ItemSheetDTO
    :return: The inline item sheet component
    :rtype: rx.Component
    """
    return rx.link(
        rx.text(item_sheet.name, size="2", color="var(--accent-9)"),
        href=ElnAppRouter.get_item_sheet_detail_url(item_sheet.id),
    )
