"""Concentration methods for the concentrate activity.

Store-only audit: the method used to concentrate a solution (if any) is recorded
on the CONCENTRATE activity. Optional — a concentrate may be logged without one.
"""

from enum import Enum


class ConcentrationMethod(Enum):
    """The physical method used to concentrate a solution (audit, optional)."""

    EVAPORATION = "evaporation"
    LYOPHILIZATION = "lyophilization"
    SOLVENT_REMOVAL = "solvent_removal"
    OTHER = "other"


# Human-readable labels, in display order.
CONCENTRATION_METHOD_LABELS: dict[ConcentrationMethod, str] = {
    ConcentrationMethod.EVAPORATION: "Evaporation",
    ConcentrationMethod.SOLVENT_REMOVAL: "Solvent removal",
    ConcentrationMethod.LYOPHILIZATION: "Lyophilization",
    ConcentrationMethod.OTHER: "Other",
}


def is_valid_concentration_method(value: str) -> bool:
    """Check if a string is a known concentration method value."""
    return value in {method.value for method in ConcentrationMethod}
