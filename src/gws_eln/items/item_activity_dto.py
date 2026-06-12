from attr import dataclass
from gws_core import BaseModelDTO
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.items.item import Item
from gws_eln.items.item_dto import ItemDTO


class ItemActivityResponseDTO(BaseModelDTO):
    """Response DTO containing both item and activity information.

    Returned by controller endpoints that update an item and create an activity.
    """

    item: ItemDTO
    activity: ActivityDTO | None = None


@dataclass
class ItemActivityResult:
    """Result of an item operation that creates an activity.

    Holds both the updated item and the created activity,
    so callers can access either without re-querying.
    """

    item: Item
    activity: Activity | None = None

    def to_dto(self) -> ItemActivityResponseDTO:
        return ItemActivityResponseDTO(
            item=self.item.to_dto(), activity=self.activity.to_dto() if self.activity else None
        )


class TransformResponseDTO(BaseModelDTO):
    """Response DTO for a transform (split/combine) that creates one activity,
    mutates 1..N input items and creates 1..N output items.

    Returned by endpoints so the frontend can re-fetch the whole affected set
    (mutated inputs + new outputs) without extra round-trips.
    """

    activity: ActivityDTO
    inputs: list[ItemDTO]
    outputs: list[ItemDTO]


@dataclass
class TransformResult:
    """Result of a transform operation (split/combine).

    Holds the single created activity, the mutated source items (`inputs`)
    and the newly created items (`outputs`), so callers can access any of
    them without re-querying.
    """

    activity: Activity
    inputs: list[Item]
    outputs: list[Item]

    def to_dto(self) -> TransformResponseDTO:
        return TransformResponseDTO(
            activity=self.activity.to_dto(),
            inputs=[item.to_dto() for item in self.inputs],
            outputs=[item.to_dto() for item in self.outputs],
        )
