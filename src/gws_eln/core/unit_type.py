from enum import Enum


class UnitType(Enum):
    """
    Enum representing the types of units supported for items.

    - VOLUME: Liters (L), milliliters (mL), microliters (µL), nanoliters (nL)
    - MASS: Kilograms (kg), grams (g), milligrams (mg), micrograms (µg), nanograms (ng)
    - LENGTH: Meters (m), centimeters (cm), millimeters (mm), micrometers (µm)
    - MOLE: Amount of substance (mol, mmol, µmol, nmol, pmol)
    - COUNT: Discrete counts (pcs, cells, copies, CFU)
    """

    VOLUME = "volume"
    MASS = "mass"
    LENGTH = "length"
    MOLE = "mole"
    COUNT = "count"
