from enum import Enum


class UnitType(Enum):
    """
    Enum representing the types of units supported for items.

    - VOLUME: Liters (L), milliliters (mL), microliters (uL)
    - MASS: Kilograms (kg), grams (g), milligrams (mg), micrograms (ug)
    - LENGTH: Meters (m), centimeters (cm), millimeters (mm)
    - COUNT: Discrete units (units)
    """

    VOLUME = "volume"
    MASS = "mass"
    LENGTH = "length"
    COUNT = "count"
