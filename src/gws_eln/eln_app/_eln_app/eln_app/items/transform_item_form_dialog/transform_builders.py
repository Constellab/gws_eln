"""Pure validation and DTO-building logic for the Transform dialog.

These functions operate only on the committed row dataclasses (+ scalar form
values) and return the service DTOs, raising :class:`ReflexAppException` on
invalid input. They hold no Reflex state and perform no service calls, so the
dialog state stays a thin orchestrator and this logic is unit-testable on its own.
"""

from decimal import Decimal

from gws_eln.core.concentration_method import ConcentrationMethod
from gws_eln.core.concentration_unit import (
    convert_concentration,
    same_concentration_family,
)
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import (
    CombineInputDTO,
    CombineItemDTO,
    ConcentrateItemDTO,
    DiluteDiluentDTO,
    DiluteItemDTO,
    SplitItemDTO,
    SplitOutputDTO,
    TransformInputDTO,
    TransformItemsDTO,
    TransformOutputDTO,
)
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_base import ReflexAppException

from .transform_models import (
    COMBINE_MIN_INPUTS,
    INPUT_ROLE_DILUENT,
    INPUT_ROLE_TARGET,
    SPLIT_MIN_OUTPUTS,
    TransformInputRow,
    TransformOutputRow,
)

# ------------------------------------------------------------------ validation & math


def validate_consumed_quantity(
    qty_str: str, unit: str, unit_type: str, item_qty_base: str, item_available: str
) -> None:
    """Validate a draft consumed quantity against the item's availability.

    :raises ReflexAppException: if the quantity is invalid, non-positive, or
        exceeds the available quantity of the selected item.
    """
    try:
        qty = Decimal(qty_str.strip())
    except (ArithmeticError, ValueError):
        raise ReflexAppException("Invalid quantity") from None
    if qty <= 0:
        raise ReflexAppException("Quantity must be positive")
    base_qty = UnitConverter.to_base_unit(qty, unit, UnitType(unit_type))
    if base_qty > Decimal(item_qty_base):
        raise ReflexAppException(
            f"Consumed quantity ({qty_str.strip()} {unit}) "
            f"exceeds the available quantity ({item_available})"
        )


def sum_base_quantity(
    rows: list[TransformInputRow] | list[TransformOutputRow], unit_type: UnitType
) -> Decimal:
    """Sum the rows' quantities converted to the base unit of ``unit_type``."""
    total = Decimal(0)
    for row in rows:
        total += UnitConverter.to_base_unit(Decimal(row.qty), row.unit, unit_type)
    return total


def validate_concentration_change(
    init_conc: str,
    init_unit: str,
    out_conc: str,
    out_unit: str,
    must_increase: bool,
    kind_label: str,
) -> None:
    """Enforce the output concentration and its direction for concentrate/dilute.

    The output concentration (value + unit) is mandatory. The direction is
    checked only when it can be compared meaningfully: the source/target
    already carries a concentration AND both values are in the **same family**
    (converted via :func:`convert_concentration`) — then concentrate must raise
    it and dilute must lower it. A cross-family output unit is accepted as-is:
    the direction can't be inferred across families, so it is left to the user.

    :raises ReflexAppException: if the output concentration is missing, or if it
        changes in the wrong direction while in the same family as the source's.
    """
    # Output concentration is mandatory for concentrate/dilute.
    if not out_conc or not out_unit:
        raise ReflexAppException(f"{kind_label} requires an output concentration (value and unit)")
    # Without a source concentration, or across different families, the
    # direction can't be compared — accept it and leave it to the user.
    if not init_conc or not init_unit:
        return
    if not same_concentration_family(init_unit, out_unit):
        return
    # Compare in the output's unit (same family → lossless conversion).
    initial = convert_concentration(init_conc, init_unit, out_unit)
    final = Decimal(out_conc)
    if must_increase and final <= initial:
        raise ReflexAppException(
            "Concentrate must increase the concentration "
            "(output concentration must be higher than the source's)"
        )
    if not must_increase and final >= initial:
        raise ReflexAppException(
            "Dilute must decrease the concentration "
            "(output concentration must be lower than the target's)"
        )


# ------------------------------------------------------------------ DTO builders


def _instrument_ids(inputs: list[TransformInputRow]) -> list[str]:
    return [row.item_id for row in inputs if not row.is_consumable]


def _require_label(output: TransformOutputRow) -> str:
    """Return the output's stripped label, which is mandatory.

    :raises ReflexAppException: if the output has no label.
    """
    label = (output.label or "").strip()
    if not label:
        raise ReflexAppException("Each output item needs a label")
    return label


def build_split(
    inputs: list[TransformInputRow],
    outputs: list[TransformOutputRow],
    notes: str | None,
    note_id: str | None,
) -> tuple[str, SplitItemDTO]:
    """Validate and build the split DTO. Returns ``(source_item_id, dto)``."""
    source = next((row for row in inputs if row.is_consumable), None)
    if source is None:
        raise ReflexAppException("Split needs a source consumable item")
    if not source.qty:
        raise ReflexAppException("Split needs a consumed quantity for the source item")
    if len(outputs) < SPLIT_MIN_OUTPUTS:
        raise ReflexAppException(f"Split needs at least {SPLIT_MIN_OUTPUTS} outputs")

    output_dtos = [
        SplitOutputDTO(
            quantity=Decimal(row.qty),
            unit=row.unit,
            location_id=row.location_id or None,
            label=_require_label(row),
        )
        for row in outputs
    ]
    dto = SplitItemDTO(
        quantity_contributed=Decimal(source.qty),
        unit=source.unit,
        outputs=output_dtos,
        instrument_item_ids=_instrument_ids(inputs),
        notes=notes,
        note_id=note_id,
    )
    return source.item_id, dto


def build_combine(
    inputs: list[TransformInputRow],
    outputs: list[TransformOutputRow],
    notes: str | None,
    note_id: str | None,
) -> CombineItemDTO:
    """Validate and build the combine DTO."""
    consumables = [row for row in inputs if row.is_consumable]
    if len(consumables) < COMBINE_MIN_INPUTS:
        raise ReflexAppException(f"Combine needs at least {COMBINE_MIN_INPUTS} consumable inputs")
    if any(not row.qty for row in consumables):
        raise ReflexAppException("Each consumable input needs a quantity")
    if len(outputs) != 1:
        raise ReflexAppException("Combine produces exactly one output")
    output = outputs[0]

    input_dtos = [
        CombineInputDTO(item_id=row.item_id, quantity=Decimal(row.qty), unit=row.unit)
        for row in consumables
    ]
    return CombineItemDTO(
        inputs=input_dtos,
        output_item_sheet_id=output.sheet_id,
        output_quantity=Decimal(output.qty),
        output_unit=output.unit,
        instrument_item_ids=_instrument_ids(inputs),
        output_location_id=output.location_id or None,
        output_label=_require_label(output),
        output_concentration=Decimal(output.conc) if output.conc else None,
        output_concentration_unit=output.conc_unit or None,
        notes=notes,
        note_id=note_id,
    )


def build_concentrate(
    inputs: list[TransformInputRow],
    outputs: list[TransformOutputRow],
    notes: str | None,
    note_id: str | None,
) -> tuple[str, ConcentrateItemDTO]:
    """Validate and build the concentrate DTO. Returns ``(source_item_id, dto)``."""
    source = next((row for row in inputs if row.is_consumable), None)
    if source is None or not source.qty:
        raise ReflexAppException("Concentrate needs a source consumable item with a quantity")
    if len(outputs) != 1:
        raise ReflexAppException("Concentrate produces exactly one output")
    output = outputs[0]
    validate_concentration_change(
        source.init_conc,
        source.init_conc_unit,
        output.conc,
        output.conc_unit,
        must_increase=True,
        kind_label="Concentrate",
    )

    dto = ConcentrateItemDTO(
        quantity_contributed=Decimal(source.qty),
        unit=source.unit,
        output_quantity=Decimal(output.qty),
        output_unit=output.unit,
        output_concentration=Decimal(output.conc) if output.conc else None,
        output_concentration_unit=output.conc_unit or None,
        dilution_factor=Decimal(output.dilution_factor) if output.dilution_factor else None,
        concentration_method=(
            ConcentrationMethod(output.concentration_method)
            if output.concentration_method
            else None
        ),
        instrument_item_ids=_instrument_ids(inputs),
        output_location_id=output.location_id or None,
        output_label=_require_label(output),
        notes=notes,
        note_id=note_id,
    )
    return source.item_id, dto


def build_dilute(
    inputs: list[TransformInputRow],
    outputs: list[TransformOutputRow],
    notes: str | None,
    note_id: str | None,
) -> tuple[str, DiluteItemDTO]:
    """Validate and build the dilute DTO. Returns ``(target_item_id, dto)``.

    A dilute needs exactly one target, at least one diluent, and exactly one
    output.
    """
    targets = [row for row in inputs if row.role == INPUT_ROLE_TARGET]
    diluents = [row for row in inputs if row.role == INPUT_ROLE_DILUENT]
    if len(targets) != 1 or not targets[0].qty:
        raise ReflexAppException("Dilute needs exactly one target consumable item with a quantity")
    if not diluents:
        raise ReflexAppException("Dilute needs at least one diluent")
    if any(not diluent.qty for diluent in diluents):
        raise ReflexAppException("Each diluent needs a quantity")
    if len(outputs) != 1:
        raise ReflexAppException("Dilute produces exactly one output")
    target = targets[0]
    output = outputs[0]
    validate_concentration_change(
        target.init_conc,
        target.init_conc_unit,
        output.conc,
        output.conc_unit,
        must_increase=False,
        kind_label="Dilute",
    )

    dto = DiluteItemDTO(
        quantity_contributed=Decimal(target.qty),
        unit=target.unit,
        diluents=[
            DiluteDiluentDTO(
                item_id=diluent.item_id,
                quantity_contributed=Decimal(diluent.qty),
                unit=diluent.unit,
            )
            for diluent in diluents
        ],
        output_quantity=Decimal(output.qty),
        output_unit=output.unit,
        output_concentration=Decimal(output.conc) if output.conc else None,
        output_concentration_unit=output.conc_unit or None,
        dilution_factor=Decimal(output.dilution_factor) if output.dilution_factor else None,
        instrument_item_ids=_instrument_ids(inputs),
        output_location_id=output.location_id or None,
        output_label=_require_label(output),
        notes=notes,
        note_id=note_id,
    )
    return target.item_id, dto


def build_custom(
    inputs: list[TransformInputRow],
    outputs: list[TransformOutputRow],
    notes: str | None,
    note_id: str | None,
) -> TransformItemsDTO | None:
    """Build the generic transform DTO, or ``None`` when there is nothing to do."""
    if not inputs or not outputs:
        return None

    input_dtos = [
        TransformInputDTO(
            item_id=row.item_id,
            quantity=Decimal(row.qty) if (row.is_consumable and row.qty) else None,
            unit=row.unit if row.is_consumable else None,
        )
        for row in inputs
    ]
    output_dtos = [
        TransformOutputDTO(
            output_item_sheet_id=row.sheet_id,
            quantity=Decimal(row.qty),
            unit=row.unit,
            location_id=row.location_id or None,
            label=_require_label(row),
            concentration=Decimal(row.conc) if row.conc else None,
            concentration_unit=row.conc_unit or None,
        )
        for row in outputs
    ]
    return TransformItemsDTO(inputs=input_dtos, outputs=output_dtos, notes=notes, note_id=note_id)
