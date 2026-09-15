"""Turn a SoilGrids/HiHydroSoil sample into EPIC layers, without pandas or HTTP.

The conversions match ``geoEpic.spatial.isric.SoilGrids.fetch``: composition
comes from ISRIC, hydraulics from HiHydroSoil, hydrologic group from
HiHydroSoil's single image, and albedo is the same 0.15 default. Spec
expressions already apply the unit scaling, so values arriving here are in
EPIC units.

Nulls are refused rather than zeroed. Water and rock are real gaps on both
grids; inventing a profile would be worse than skipping the cell.
"""
import hashlib

from geoEpic.epicfiles.sol import LAYER_PROPERTIES

class SoilGridsError(ValueError):
    pass


#: Bottom of each SoilGrids depth interval, in metres, as isric.py writes.
DEPTHS = (
    ("0_5", 0.05),
    ("5_15", 0.15),
    ("15_30", 0.30),
    ("30_60", 0.60),
    ("60_100", 1.00),
    ("100_200", 2.00),
)

#: ~250 m in degrees; the same snap ``SoilGrids.generate_soil_id`` uses.
GRID_STEP_DEG = 0.0025

DEFAULT_ALBEDO = 0.15

#: Properties the .SOL cannot be built without. Texture, density and the
#: three hydraulic fields EPIC actually runs on; the rest may be absent.
REQUIRED_STEMS = (
    "bulk_density", "sand", "silt",
    "field_capacity", "wilting_capacity", "saturated_conductivity",
)


def pixel_id(latitude, longitude):
    """Stable 8-digit id for the 250 m cell containing a point.

    Byte-identical to ``geoEpic.spatial.isric.SoilGrids.generate_soil_id``.
    """
    row = int(round(float(latitude) / GRID_STEP_DEG))
    column = int(round(float(longitude) / GRID_STEP_DEG))
    digest = hashlib.blake2s("{},{}".format(row, column).encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % 100_000_000


def _value(sample, name):
    if hasattr(sample, "get"):
        return sample.get(name)
    return sample[name] if name in sample else None


def hydgrp_from(sample):
    """HiHydroSoil stores 1=A 2=B 3=C 4=D; C when the cell has no group."""
    value = _value(sample, "hydrologic_soil_group")
    if isinstance(value, (int, float)) and value == value:
        try:
            return {1: "A", 2: "B", 3: "C", 4: "D"}.get(int(value), "C")
        except (TypeError, ValueError):
            return "C"
    if isinstance(value, str) and value.strip():
        letter = value.strip()[0].upper()
        if letter in {"A", "B", "C", "D"}:
            return letter
    return "C"


def required_names():
    names = []
    for stem in REQUIRED_STEMS:
        for suffix, _depth in DEPTHS:
            names.append("{}_{}".format(stem, suffix))
    return names


def layers_from_sample(sample):
    """Six EPIC layers from one Sample, or SoilGridsError if a required value is missing."""
    missing = [name for name in required_names() if _value(sample, name) is None]
    if missing:
        raise SoilGridsError(
            "No soil at this location (missing {}). Water and rock cells are "
            "left empty rather than filled with zeros.".format(", ".join(missing[:6])))

    layers = []
    for suffix, depth in DEPTHS:
        def take(stem, suffix=suffix):
            return float(_value(sample, "{}_{}".format(stem, suffix)))

        nitrogen = _value(sample, "nitrogen_{}".format(suffix))
        ph = _value(sample, "ph_{}".format(suffix))
        organic = _value(sample, "organic_carbon_{}".format(suffix))
        cec = _value(sample, "cec_{}".format(suffix))
        fragments = _value(sample, "coarse_fragments_{}".format(suffix))
        density = take("bulk_density")
        layers.append({
            "Layer_depth": depth,
            "Bulk_Density": density,
            "Wilting_capacity": take("wilting_capacity"),
            "Field_Capacity": take("field_capacity"),
            "Sand_content": take("sand"),
            "Silt_content": take("silt"),
            "N_concen": 0.0 if nitrogen is None else float(nitrogen),
            "pH": 0.0 if ph is None else float(ph),
            "Sum_Bases": 0.0,
            "Organic_Carbon": 0.0 if organic is None else float(organic),
            "Calcium_Carbonate": 0.0,
            "Cation_exchange": 0.0 if cec is None else float(cec),
            "Course_Fragment": 0.0 if fragments is None else float(fragments),
            "cnds": 0.0, "pkrz": 0.0, "rsd": 0.0,
            "Bulk_density_dry": density,
            "psp": 0.0,
            "Saturated_conductivity": take("saturated_conductivity"),
        })
        extra = set(layers[-1]) - set(LAYER_PROPERTIES)
        if extra:
            raise SoilGridsError("Unexpected layer keys: {}".format(sorted(extra)))
    return layers


def profile_from_sample(sample):
    """The dict ``epicfiles.sol.write`` needs, matching isric.py's SOL object."""
    return {
        "albedo": DEFAULT_ALBEDO,
        "hydgrp": hydgrp_from(sample),
        "layers": layers_from_sample(sample),
    }
