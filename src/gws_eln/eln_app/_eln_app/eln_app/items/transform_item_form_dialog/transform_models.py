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
    """The transformation chosen in the wizard's first step.

    Values match ``ActivityType`` for the specialised kinds; ``CUSTOM`` is the
    generic N->M transform (``ActivityType.TRANSFORM``).
    """

    SPLIT = "split"
    COMBINE = "combine"
    DILUTE = "dilute"
    CONCENTRATE = "concentrate"
    CUSTOM = "transform"


class TransformStep(IntEnum):
    """Steps of the transform wizard (serializes as int for the frontend)."""

    CHOOSE = 1  # pick the transformation kind
    BUILD = 2  # build the inputs/outputs


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
