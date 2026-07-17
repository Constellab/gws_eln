"""Data types shared by the Transform dialog state, builders and components.

Pure definitions (enums, committed-row dataclasses, constants) with no Reflex or
service dependency, so they can be imported freely from either side.
"""

from dataclasses import dataclass
from enum import Enum, IntEnum


class OutputStep(IntEnum):
    """Steps of the output wizard (serializes as int for the frontend)."""

    SHEET = 1  # choose or create the destination ItemSheet
    ITEM = 2  # create the produced item


class TransformKind(Enum):
    """The activity chosen in the wizard's first step.

    Values match ``ActivityType`` for the specialised kinds; ``CUSTOM`` is the
    generic N->M transform (``ActivityType.TRANSFORM``). ``MOVE`` and ``RELABEL``
    are not transformations and are only offered when the chooser is launched
    from a note: they carry the chooser card's copy, then hand over to their own
    standalone dialog instead of this wizard's build step.
    """

    SPLIT = "split"
    COMBINE = "combine"
    DILUTE = "dilute"
    CONCENTRATE = "concentrate"
    CONSUME = "consume"
    MOVE = "move"
    RELABEL = "relabel"
    CUSTOM = "transform"


class TransformStep(IntEnum):
    """Steps of the transform wizard (serializes as int for the frontend)."""

    CHOOSE = 1  # pick the transformation kind
    BUILD = 2  # build the inputs/outputs


# One-line title per kind, shown on the chooser card and as the dialog title.
KIND_TITLES: dict[str, str] = {
    TransformKind.SPLIT.value: "Split",
    TransformKind.COMBINE.value: "Combine",
    TransformKind.DILUTE.value: "Dilute",
    TransformKind.CONCENTRATE.value: "Concentrate",
    TransformKind.CONSUME.value: "Consume",
    TransformKind.MOVE.value: "Move",
    TransformKind.RELABEL.value: "Relabel",
    TransformKind.CUSTOM.value: "Custom transform",
}

# Short one-line summary per kind, shown under the card title and as the dialog
# subtitle. The full text lives in KIND_DESCRIPTIONS (the card's info tooltip).
KIND_SUBTITLES: dict[str, str] = {
    TransformKind.SPLIT.value: "One source item → several new items.",
    TransformKind.COMBINE.value: "Several items → one new item.",
    TransformKind.DILUTE.value: "Target + diluent → one diluted item.",
    TransformKind.CONCENTRATE.value: "One item → one more concentrated item.",
    TransformKind.CONSUME.value: "Reduce one item's stock (no new item).",
    TransformKind.MOVE.value: "Change one item's location.",
    TransformKind.RELABEL.value: "Change one item's label.",
    TransformKind.CUSTOM.value: "Any number of inputs → any number of outputs.",
}

# Full description per kind, shown in the chooser card's info tooltip.
# Single source of truth so the tooltip and any reuse never drift.
KIND_DESCRIPTIONS: dict[str, str] = {
    TransformKind.SPLIT.value: (
        "Use Split to divide one source item into two or more output items. The total "
        "quantity of the outputs must not exceed the quantity taken from the source item. "
        "Each output is created as a separate item and inherits relevant information and "
        "traceability from the source item."
    ),
    TransformKind.COMBINE.value: (
        "Use Combine when two or more source items are merged to create one new output "
        "item. The quantities used from each input are deducted from their available "
        "stock, and the new output item is linked to all source items through its "
        "transformation history."
    ),
    TransformKind.DILUTE.value: (
        "Use Dilute when one target item is mixed with one or more diluents to create one "
        "new item with a lower concentration. The quantities used from the target and "
        "diluent items are deducted from their available stock, and the output remains "
        "linked to all inputs through its transformation history."
    ),
    TransformKind.CONCENTRATE.value: (
        "Use Concentrate when exactly one source item is processed to create exactly one "
        "output item with a higher concentration, typically by removing solvent or "
        "reducing volume."
    ),
    TransformKind.CONSUME.value: (
        "Use Consume when a quantity is used, spent, destroyed, or otherwise"
        "removed from the available stock without creating any output item. "
        "The consumed quantity is deducted from the source item, and the activity "
        "remains recorded in the item history."
    ),
    TransformKind.MOVE.value: (
        "Use Move when an item physically changes location, without any change to its "
        "quantity or identity. The item's location is updated and the move is recorded "
        "in its history, keeping the trail of where it has been stored."
    ),
    TransformKind.RELABEL.value: (
        "Use Relabel when an item's label must be corrected or renamed, without any "
        "change to its quantity, location or identity. The previous and new labels are "
        "both recorded in the item history."
    ),
    TransformKind.CUSTOM.value: (
        "Use Custom Transform when any number of input items must be converted into any "
        "number of output items and the operation does not fit the predefined Split, "
        "Combine, Dilute, or Concentrate transformations. The transformation records the "
        "quantities, identities, and lineage of all inputs and outputs."
    ),
}


# A combine needs at least this many consumable ingredients.
COMBINE_MIN_INPUTS = 2

# A split must produce at least this many outputs (1 output would be a move/aliquot).
SPLIT_MIN_OUTPUTS = 2

# Roles for the two consumable inputs of a dilute (target is the item being diluted).
INPUT_ROLE_TARGET = "target"
INPUT_ROLE_DILUENT = "diluent"


@dataclass
class TransformInputRow:
    """One committed input (item or instrument) consumed by the transform."""

    id: str
    item_id: str
    sheet_id: str  # the item's sheet id (used to fix the output sheet for split)
    sheet_code: str  # the item's sheet code (for the output code preview)
    sheet_name: str
    code: str
    label: str
    loc: str
    is_consumable: bool
    qty: str  # raw, for DTO (empty for instruments)
    unit: str  # raw, for DTO
    unit_type: str  # for re-populating the edit form
    available: str  # available quantity (display), for re-populating the edit form
    qty_base: str  # available quantity in base unit, for edit-time validation
    consumed: str  # display, e.g. "4 units" or "instrument"
    role: str = ""  # dilute role: INPUT_ROLE_TARGET / INPUT_ROLE_DILUENT ("" otherwise)
    init_conc: str = ""  # the item's current concentration (for concentrate/dilute checks)
    init_conc_unit: str = ""  # unit of init_conc ("" when none)


@dataclass
class TransformOutputRow:
    """One committed output (new item) produced by the transform."""

    id: str
    sheet_id: str
    sheet_code: str
    sheet_name: str
    label: str
    loc: str
    qty: str  # raw, for DTO
    unit: str  # raw, for DTO
    location_id: str  # raw, for DTO
    conc: str  # raw, for DTO
    conc_unit: str  # raw, for DTO ("" when none)
    code_preview: str
    produced: str  # display
    dilution_factor: str = ""  # raw, for DTO (concentrate/dilute audit; "" when none)
    concentration_method: str = ""  # ConcentrationMethod value (concentrate audit; "" when none)
    override_reason: str = ""  # justification when the label diverges from the source (split)
    notes: str = ""  # the output item's own note (kept off the activity's note)
    expiry_date: str = ""  # ISO date (required for consumable outputs; "" when unset)
