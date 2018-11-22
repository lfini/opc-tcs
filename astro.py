"""
Funzioni di tipo astronomico per GUI OPC
"""

# Le funzioni sono implementate direttamente per dimunuire il numero
# di dipendenze del package. Per verificare la correttezza è stato sviluppata
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

# sin(EL) = sin(DEC)sin(LAT)+cos(DEC)*cos(LAT)*cos(HA)
# sin(AZ) = cos(DEC)sin(HA)/cos(EL)
# cos(AZ) = (sin(DEC) - sin(LAT)sin(EL))/cos(LAT)/cos(EL)

# Coordinate Osservatorio Polifunzionale del Chianti
#
# Latitudine: 43g31'24" N   = 43.52333333333333 deg  = 0.7596254681096652 rad
# Longitudine: 11g14'44" E  = 11.245555555555555 deg = 0.19627197066038454 rad
#                           = 0.7497037037037036 hours

from __future__ import print_function

import time
from math import sin, cos, sqrt, asin, acos, pi, fmod

DEG_TO_RAD = 0.017453292519943295   # PI/180.
RAD_TO_DEG = 57.29577951308232      # 180./PI

HOUR_TO_DEG = 15.0
DEG_TO_HOUR = 0.06666666666666667
HOUR_TO_RAD = 0.2617993877991494
RAD_TO_HOUR = 3.8197186342054885
TSEC_TO_RAD = 7.27220521664304e-05  # secondi (tempo) in radianti
RAD_TO_TSEC = 13750.987083139758

TCIV_TO_TSID = 1.0027378956049176  # conv. intervallo tempo civile in sidereo

class OPC:
    "Dati relativi a Osservatorio del Chianti"
    lat_deg = 43.52333333333333
    lat_rad = 0.7596254681096652
    lon_deg = 11.245555555555555
    lon_rad = 0.19627197066038454
    cos_lat = cos(lat_rad)
    sin_lat = sin(lat_rad)

def jul_date(year, mon, day, hour, mnt, sec, utc_offset=0):
    "Calcolo data giuliana per dato tempo civile"
    if mon <= 2:
        year -= 1
        mon += 12
    aaa = int(year/100)
    bbb = 2-aaa+int(aaa/4)
    jd0 = int(365.25*(year+4716))+int(30.6*(mon+1))+day+bbb-1524.5
    hoff = (hour+mnt/60.+sec/3600.-utc_offset)/24.
    return jd0+hoff

#   tsid_grnw usa una formula semplificata con errore 0.1 sec per secolo
#   vedi: http://aa.usno.navy.mil/faq/docs/GAST.php
def tsid_grnw(year, mon, day, hour, mnt, sec, utc_offset=0):
    "Calcolo tempo sidereo medio di Greenwhich"
    jd2000 = jul_date(year, mon, day, hour, mnt, sec, utc_offset)-2451545.0
    gmst = fmod(18.697374558+24.06570982441908*jd2000, 24.)
    if gmst < 0:
        gmst += 24.
    return gmst

def loc_st(year, mon, day, hour, mnt, sec, utc_offset=0, lon_rad=0.0):
    "Calcolo tempo sidereo locale per generico luogo"
    gmst = tsid_grnw(year, mon, day, hour, mnt, sec, utc_offset)
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

def az_coords(ha_rad, dec_rad):
    "Converte coordinate equatoriali in altoazimutali"
    sin_ha = sin(ha_rad)
    sin_el = sin(dec_rad)*OPC.sin_lat+cos(dec_rad)*OPC.cos_lat*cos(ha_rad)
    cos_el = sqrt(1.-sin_el*sin_el)
#   sin_az = cos(dec_rad)*sin_ha/cos_el
    cos_az = (sin(dec_rad)-OPC.sin_lat*sin_el)/OPC.cos_lat/cos_el
    el_rad = asin(sin_el)
    if sin_ha < 0.0:
        az_rad = acos(cos_az)
    else:
        az_rad = 2.*pi-acos(cos_az)
    return az_rad, el_rad

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
    "Convert degrees (float) into radians"
    return deg*DEG_TO_RAD

def ums2float(deg, mnt, sec):
    "Convert units (unit, mnt, sec) into float"
    sign = 1 if deg >= 0 else -1
    deg = abs(deg)
    if mnt < 0 or mnt > 59:
        raise Exception("DMS error")
    if sec < 0 or sec >= 60.0:
        raise Exception("DMS error")
    return sign*(deg+mnt/60.+sec/3600.)

def hms2deg(hour, mnt, sec):
    "Convert hours (hour, mnt, sec) into degrees (float)"
    return ums2float(hour, mnt, sec)*HOUR_TO_DEG

def hms2rad(hour, mnt, sec):
    "Convert hours (hour, mnt, sec) into radians"
    return ums2float(hour, mnt, sec)*HOUR_TO_RAD

def dms2rad(deg, mnt, sec):
    "Convert (deg, mnt, sec) in radians"
    return ums2float(deg, mnt, sec)*DEG_TO_RAD

def rad2deg(rad):
    "Convert radians (float) into degrees (float)"
    return rad*RAD_TO_DEG

def rad2dms(rad):
    "Convert radians (float) into degrees (deg, mnt, sec) sign on deg"
    deg = rad*RAD_TO_DEG
    return float2ums(deg)

def float2ums(value):
    "Convert float value into (units, minutes, seconds) sign on units"
    sign = 1 if value >= 0.0 else -1
    value = abs(value)
    idd = int(value)
    rest = (value-idd)*60.
    mnt = int(rest)
    sec = int((rest-mnt)*60+0.5)
    return (idd*sign, mnt, sec)

TEST_TEXT = """
Per effettuare test di qualità sulle funzioni di questo modulo usare:

astrotest.py
"""

if __name__ == "__main__":
    print(TEST_TEXT)
