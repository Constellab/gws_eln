"""State for managing the breadcrumb navigation component."""

from dataclasses import dataclass

import reflex as rx
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item import Item
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_reflex_main import ReflexMainState

from ..eln_app_router import ElnAppRouter


@dataclass
class BreadcrumbItem:
    """Represents a single item in the breadcrumb trail.

    :param label: The display text for this breadcrumb item
    :type label: str
    :param url: The URL to navigate to when clicked
    :type url: str
    """

    label: str
    url: str


class BreadcrumbState(rx.State):
    """State for managing the breadcrumb navigation component.

    This state builds breadcrumb trails by detecting the current page type
    from URL parameters and building the appropriate hierarchy.
    """

    @rx.var
    async def breadcrumbs(self) -> list[BreadcrumbItem]:
        """Get breadcrumb items for the current page.

        This method detects the current page type from URL and builds
        the breadcrumb trail based on the object type.

        :return: List of breadcrumb items
        :rtype: list[BreadcrumbItem]
        """
        # Start with base breadcrumb - ItemSheets list
        items = [BreadcrumbItem(label="ItemSheets", url=ElnAppRouter.get_item_sheet_list_url())]

        # Check if we're on a item_sheet detail page
        item_sheet_id = self.item_sheet_id
        if item_sheet_id:
            item_sheet = await self._get_item_sheet(item_sheet_id)
            if item_sheet:
                items.append(
                    BreadcrumbItem(
                        label=item_sheet.name,
                        url=ElnAppRouter.get_item_sheet_detail_url(item_sheet.id),
                    )
                )
            return items

        # Check if we're on a item detail page
        item_id = self.item_id
        if item_id:
            items.extend(await self._build_breadcrumbs_for_item(item_id))
            return items

        return items

    async def _get_item_sheet(self, item_sheet_id: str) -> ItemSheet | None:
        """Get a item_sheet by ID.

        :param item_sheet_id: The ID of the item_sheet
        :type item_sheet_id: str
        :return: The item_sheet or None if not found
        :rtype: ItemSheet | None
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            item_sheet_service = ItemSheetService()
            return item_sheet_service.get_item_sheet(item_sheet_id)

    async def _build_breadcrumbs_for_item(self, item_id: str) -> list[BreadcrumbItem]:
        """Build breadcrumb items for a item page.

        This includes the item_sheet and all parent items in the hierarchy.

        :param item_id: The ID of the item
        :type item_id: str
        :return: List of breadcrumb items for the item hierarchy
        :rtype: list[BreadcrumbItem]
        """
        item: Item
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            item_service = ItemService()
            item = item_service.get_item(item_id)

        return [
            BreadcrumbItem(
                label=item.item_sheet.name,
                url=ElnAppRouter.get_item_sheet_detail_url(item.item_sheet.id),
            ),
            BreadcrumbItem(
                label=item.code,
                url=ElnAppRouter.get_item_detail_url(item.id),
            ),
        ]
