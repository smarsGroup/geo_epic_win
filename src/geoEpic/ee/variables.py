"""What EPIC needs from a daily weather collection, and how to recognise it.

Used when a user points GeoEPIC or Q-EPIC at an arbitrary ImageCollection. The
aliases are evidence that a band is a *candidate* for a variable - never proof
of its units, scaling, or completeness. Every caller must keep saying so.

Dependency-light: standard library only.
"""

#: Canonical EPIC daily weather variables, in the order EPIC expects them,
#: mapped to band names seen across the common public collections.
EPIC_VARIABLES = {
    "maximum air temperature": ["tmax", "tmmx", "tasmax", "temperature_2m_max",
                                "maximum_2m_air_temperature", "Temperature_Air_2m_Max_24h"],
    "minimum air temperature": ["tmin", "tmmn", "tasmin", "temperature_2m_min",
                                "minimum_2m_air_temperature", "Temperature_Air_2m_Min_24h"],
    "precipitation": ["prcp", "pr", "precipitation", "total_precipitation",
                      "total_precipitation_sum", "Precipitation_Flux"],
    "solar radiation": ["srad", "rsds", "surface_solar_radiation_downwards",
                        "surface_solar_radiation_downwards_sum", "Solar_Radiation_Flux"],
    "humidity": ["rh", "hurs", "rmax", "rmin", "relative_humidity", "vp", "vapor_pressure",
                 "dewpoint_temperature_2m", "Vapour_Pressure_Mean_24h",
                 "Relative_Humidity_2m_06h"],
    "wind speed": ["ws", "vs", "sfcWind", "wind_speed", "Wind_Speed_10m_Mean",
                   "Wind_Speed_10m_Mean_24h"],
}

#: Pairs that can stand in for a variable only after further computation.
DERIVABLE = {
    "wind speed": (("u_component_of_wind_10m", "v_component_of_wind_10m"),
                   "10 m u/v components (vector magnitude required)"),
}


def recognise(bands, interval_hours=None):
    """Match band names to EPIC variables, case-insensitively.

    Returns ``(found, missing)`` where ``found`` maps each canonical variable to
    the band that could supply it, or None.
    """
    available = {str(band).casefold() for band in bands}
    found = {}
    for variable, aliases in EPIC_VARIABLES.items():
        found[variable] = next((alias for alias in aliases if alias.casefold() in available), None)

    # A sub-daily instantaneous temperature can yield daily extrema.
    if interval_hours is not None and interval_hours < 24 and "temperature_2m" in available:
        for variable in ("maximum air temperature", "minimum air temperature"):
            if not found[variable]:
                found[variable] = "temperature_2m (daily extrema required)"

    for variable, (components, label) in DERIVABLE.items():
        if not found.get(variable) and {c.casefold() for c in components} <= available:
            found[variable] = label

    missing = [variable for variable, band in found.items() if not band]
    return found, missing


def looks_meteorological(found):
    """Whether anything at all was recognised, i.e. this might be weather data."""
    return any(found.values())
