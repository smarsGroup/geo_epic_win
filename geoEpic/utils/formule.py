import numpy as np

def rh_dewpt(dewpt, tmax, tmin):
    '''
    Computes relative humidity using dew point.
    Args:
    dewpt: Dew point temperature in °C.
    tmax: Maximum air temperature in °C.
    tmin: Minimum air temperature in °C.
    '''
    T = (tmax + tmin) / 2
    rh = np.exp((17.625 * dewpt) / (243.04 + dewpt)) / np.exp((17.625 * T) / (243.04 + T))
    return rh

def rh_vappr(vappr, tmax, tmin):
    '''
    Computes relative humidity using vapor pressure.
    Args:
    vappr: Actual vapor pressure in Pa.
    tmax: Maximum air temperature in °C.
    tmin: Minimum air temperature in °C.
    '''
    T = (tmax + tmin) / 2
    a, b, c = 611, 17.502, 240.97 
    es_T = a * np.exp(b * T / (T + c))
    rh = vappr / es_T
    return rh

def windspd(uw, vw):
    '''
    Computes wind speed from its components.
    '''
    ws = np.sqrt(uw ** 2 + vw ** 2)
    return np.round(ws, 2)
