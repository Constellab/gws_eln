"""State for managing the breadcrumb navigation component."""

from dataclasses import dataclass

import reflex as rx
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_service import MaterialService
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


class BreadcrumbState(ReflexMainState):
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
        # Start with base breadcrumb - Materials list
        items = [BreadcrumbItem(label="Materials", url=ElnAppRouter.get_material_list_url())]

        # Check if we're on a material detail page
        material_id = self.material_id
        if material_id:
            material = await self._get_material(material_id)
            if material:
                items.append(
                    BreadcrumbItem(
                        label=material.name,
                        url=ElnAppRouter.get_material_detail_url(material.id),
                    )
                )
            return items

        # Check if we're on a batch detail page
        batch_id = self.batch_id
        if batch_id:
            items.extend(await self._build_breadcrumbs_for_batch(batch_id))
            return items

        return items

    async def _get_material(self, material_id: str) -> Material | None:
        """Get a material by ID.

        :param material_id: The ID of the material
        :type material_id: str
        :return: The material or None if not found
        :rtype: Material | None
        """
        try:
            with await self.authenticate_user():
                material_service = MaterialService()
                return material_service.get_material(material_id)
        except Exception:
            return None

    async def _build_breadcrumbs_for_batch(self, batch_id: str) -> list[BreadcrumbItem]:
        """Build breadcrumb items for a batch page.

        This includes the material and all parent batches in the hierarchy.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :return: List of breadcrumb items for the batch hierarchy
        :rtype: list[BreadcrumbItem]
        """
        items: list[BreadcrumbItem] = []

        try:
            with await self.authenticate_user():
                batch_service = MaterialBatchService()
                # Get the full hierarchy including self and material
                hierarchy = batch_service.get_parent_hierarchy(
                    batch_id,
                    include_self=True,
                    include_material=True,
                )

            if not hierarchy:
                return items

            # The hierarchy is ordered: [self, parent, ..., root, material]
            # We need to reverse it to get: [material, root, ..., parent, self]
            hierarchy.reverse()

            for i, obj in enumerate(hierarchy):
                if i == 0:
                    # First item is the material
                    items.append(
                        BreadcrumbItem(
                            label=obj.name,
                            url=ElnAppRouter.get_material_detail_url(obj.id),
                        )
                    )
                else:
                    # Rest are batches
                    items.append(
                        BreadcrumbItem(
                            label=obj.name,
                            url=ElnAppRouter.get_batch_detail_url(obj.id),
                        )
                    )

        except Exception:
            pass

        return items
