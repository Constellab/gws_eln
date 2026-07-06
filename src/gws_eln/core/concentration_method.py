"""Concentration methods for the concentrate activity.

Store-only audit: the method used to concentrate a solution (if any) is recorded
on the CONCENTRATE activity. Optional — a concentrate may be logged without one.
"""

from enum import Enum


class ConcentrationMethod(Enum):
    """The physical method used to concentrate a solution (audit, optional)."""

    EVAPORATION = "evaporation"
    ULTRAFILTRATION = "ultrafiltration"
    LYOPHILIZATION = "lyophilization"
    PRECIPITATION = "precipitation"
    CENTRIFUGAL_CONCENTRATION = "centrifugal_concentration"


# Human-readable labels, in display order.
CONCENTRATION_METHOD_LABELS: dict[ConcentrationMethod, str] = {
    ConcentrationMethod.EVAPORATION: "Evaporation",
    ConcentrationMethod.ULTRAFILTRATION: "Ultrafiltration",
    ConcentrationMethod.LYOPHILIZATION: "Lyophilization",
    ConcentrationMethod.PRECIPITATION: "Precipitation",
    ConcentrationMethod.CENTRIFUGAL_CONCENTRATION: "Centrifugal concentration",
}


def is_valid_concentration_method(value: str) -> bool:
    """Check if a string is a known concentration method value."""
    return value in {method.value for method in ConcentrationMethod}
