"""
Funzioni di tipo astronomico per GUI OPC
"""

# Le funzioni sono implementate direttamente per dimunuire il numero
# di dipendenze del package. Per verificare la correttezza usare
# la procedura: astrotest.py
#

#
# EL:  altezza
# AZ:  azimuth
# DEC: declinazione
# AR:  ascensione retta
# HA:  angolo orario
# LAT: latitudine del luogo

# HA = LTS - AR

# Coordinate Osservatorio Polifunzionale del Chianti
#
# Latitudine: 43g31'24" N   = 43.52333333333333 deg  = 0.7596254681096652 rad
# Longitudine: 11g14'44" E  = 11.245555555555555 deg = 0.19627197066038454 rad
#                           = 0.7497037037037036 hours

from __future__ import print_function

import time
from math import sin, cos, sqrt, asin, atan2, pi, fmod

DEG_TO_RAD = 0.017453292519943295   # PI/180.
RAD_TO_DEG = 57.29577951308232      # 180./PI

HOUR_TO_DEG = 15.0
DEG_TO_HOUR = 0.06666666666666667
HOUR_TO_RAD = 0.2617993877991494
RAD_TO_HOUR = 3.8197186342054885
TSEC_TO_RAD = 7.27220521664304e-05  # secondi (tempo) in radianti
RAD_TO_TSEC = 13750.987083139758

PI2 = 2*pi

TCIV_TO_TSID = 1.0027378956049176  # conv. intervallo tempo civile in sidereo

class OPC:
    "Dati relativi a Osservatorio del Chianti"
    lat_deg = 43.52333333333333
    lat_rad = 0.7596254681096652
    lon_deg = 11.245555555555555
    lon_rad = 0.19627197066038454
    cos_lat = cos(lat_rad)
    sin_lat = sin(lat_rad)

def jul_date(year, mon, day, hour, mins, secs, utc_offset=0):
    "Calcolo data giuliana per dato tempo civile"
    if mon <= 2:
        year -= 1
        mon += 12
    aaa = int(year/100)
    bbb = 2-aaa+int(aaa/4)
    jd0 = int(365.25*(year+4716))+int(30.6*(mon+1))+day+bbb-1524.5
    hoff = (hour+mins/60.+secs/3600.-utc_offset)/24.
    return jd0+hoff

#   tsid_grnw usa una formula semplificata con errore 0.1 sec per secolo
#   vedi: http://aa.usno.navy.mil/faq/docs/GAST.php

def tsid_grnw(year, mon, day, hour, mins, secs, utc_offset=0):
    "Calcolo tempo sidereo medio di Greenwhich"
    jd2000 = jul_date(year, mon, day, hour, mins, secs, utc_offset)-2451545.0
    gmst = fmod(18.697374558+24.06570982441908*jd2000, 24.)
    if gmst < 0:
        gmst += 24.
    return gmst

def loc_st(year, mon, day, hour, mins, secs, utc_offset=0, lon_rad=0.0):
    "Calcolo tempo sidereo locale per generico luogo"
    gmst = tsid_grnw(year, mon, day, hour, mins, secs, utc_offset)
    locst = fmod(gmst+lon_rad*RAD_TO_HOUR, 24.)
    if locst < 0:
        locst += 24.
    return locst

def loc_st_now(lon_rad=OPC.lon_rad):
    "Calcolo tempo sidereo locale qui e ora"
    loct = time.localtime()
    utc_offset = -time.timezone/3600.+loct.tm_isdst
    return loc_st(loct[0], loct[1], loct[2], loct[3],
                  loct[4], loct[5], utc_offset, lon_rad)

# sin(ALT) = sin(DEC)*sin(LAT)+cos(DEC)*cos(LAT)*cos(HA)
# ALT = asin(ALT) 
# cos(ALT) = sqrt(1.-sin(ALT)**2)
# sin(AZ) = cos(DEC)sin(HA)/cos(EL)
# cos(AZ) = (sin(DEC)-sin(LAT)sin(ALT))/(cos(LAT)cos(ALT))
# A = -asin(A) % (2*pi)

def az_coords(ha_rad, de_rad):
    "Converte coordinate equatoriali in altoazimutali (tutto in radianti)"
    sin_de = sin(de_rad)
    sin_el = sin_de*OPC.sin_lat+cos(de_rad)*OPC.cos_lat*cos(ha_rad)
    cos_el = sqrt(1.-sin_el*sin_el)
    sin_ha = sin(ha_rad)
    sin_az = -cos(de_rad)*sin_ha/cos_el
    cos_az = (sin_de-OPC.sin_lat*sin_el)/(OPC.cos_lat*cos_el)
    el_rad = asin(sin_el)
    az_rad = atan2(sin_az, cos_az)%PI2
    return az_rad, el_rad

# sin(DEC) = sin(ALT)sin(LAT)+cos(ALT)cos(LAT)cos(AZ)

# cos(DEC) = sqrt(1-sin(DEC)**2)

# sin(HA) = -cos(ALT)sin(AZ)/cos(DEC)

# cos(HA) = (sin(ALT)-sin(DEC)sin(LAT))/(cos(DEC)cos(LAT)

# DEC = asin(sin(DEC)
# HA  = atan2(sin(HA)/cos(HA))

def eq_coords(az_rad, el_rad):
    "Converte coordinate altoazimutali in equatoriali (tutto in radianti)"
    cos_el = cos(el_rad)
    sin_el = sin(el_rad)
    sin_de = sin_el*OPC.sin_lat+cos_el*OPC.cos_lat*cos(az_rad)
    cos_de = sqrt(1.-sin_de*sin_de)
    sin_ha = -sin(az_rad)*cos_el/cos_de
    cos_ha = (sin_el-sin_de*OPC.sin_lat)/(cos_de*OPC.cos_lat)
    ha_rad = atan2(sin_ha, cos_ha)
    de_rad = asin(sin_de)
    return ha_rad, de_rad

def normalize_angle(angle, pi2):
    "Porta angolo in [0 - pi2)"
    angle = fmod(angle, pi2)
    if angle < 0:
        angle += pi2
    return angle

def find_shortest(pos, target, rad=False):
    """
Trova la via più breve sul cerchio per andare da pos a target

Riporta (delta, sign)
"""
    pi_ = pi if rad else 180.
    pi2 = pi_*2.
    pos = normalize_angle(pos, pi2)
    target = normalize_angle(target, pi2)
    delta = target-pos
    if delta >= pi_:
        delta = pi2-delta
        sign = -1
    elif delta <= -pi_:
        delta = pi2+delta
        sign = 1
    else:
        sign = 1 if delta >= 0 else -1  # Python non ha la funzione sign()!
        delta = abs(delta)
    return delta, sign

def deg2rad(deg):
    "Converte gradi (float) in radianti"
    return deg*DEG_TO_RAD

def ums2float(sign, units, mins, secs):
    "Converte unità sessagesimali (sign, unit, mins, secs) in float"
    if mins < 0 or mins > 59:
        raise Exception("DMS error")
    if secs < 0 or secs >= 60.0:
        raise Exception("DMS error")
    return sign*(units+mins/60.+secs/3600.)

def hms2deg(sign, hour, mins, secs):
    "Converte ore sessagesimali (hour, mins, secs) in gradi (float)"
    return ums2float(sign, hour, mins, secs)*HOUR_TO_DEG

def hms2rad(sign, hour, mins, secs):
    "Convert ore sessagesimali (sign, hour, mins, secs) in radianti"
    return ums2float(sign, hour, mins, secs)*HOUR_TO_RAD

def dms2rad(sign, deg, mins, secs):
    "Converte  gradi sessagesimali (sign, deg, mins, secs) in radianti"
    return ums2float(sign, deg, mins, secs)*DEG_TO_RAD

def rad2deg(rad):
    "Converte radianti (float) in gradi (float)"
    return rad*RAD_TO_DEG

def rad2dms(rad, module=0, precision=0):
    "Converte radianti (float) in gradi sessagesimali (sign, deg, mins, secs)"
    deg = rad*RAD_TO_DEG
    return float2ums(deg, module, precision)

def float2ums(value, module=0, precision=0):
    "Converte valore float in sessagesimale (sign, units, minutes, secs, frac)"
    if module:
        value %= module
    sign = 1 if value >= 0.0 else -1
    value = abs(value)
    units = int(value)
    rest = (value-units)*60.
    mins = int(rest)
    rest = (rest-mins)*60.
    if precision:
        secs = round(rest, precision)
    else:
        secs = int(rest)
        rest = (rest-secs)
        if rest > 0.5:
            secs += 1
    if secs >= 60:
        secs = 0
        mins += 1
        if mins >= 60:
            mins = 0
            units += 1
    return (sign, units, mins, secs)

TEST_TEXT = """
Per effettuare test di qualità sulle funzioni di questo modulo usare:

astrotest.py
"""

if __name__ == "__main__":
    print(TEST_TEXT)
