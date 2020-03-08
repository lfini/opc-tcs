"""
Test funzioni astronomiche per package OPC
"""

import time
from random import random
from astropy.time import Time, TimeDelta
from astropy.coordinates import Angle
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz

import numpy as np

import astro

# Dati per test
#                ha (rad)             dec (rad)            az (rad)            el (rad)
TEST_CONV = ((5.7717980, 0.12952282, 2.376153, 0.79481033),
             (4.8922684, 0.87147974, 0.92943631, 0.65938975),
             (0.99774655, 1.03418370, 5.4968418, 0.91862205),
             (2.8877032, 1.077016, 6.158971, 0.28170778))

#            data / ora / UTC offset
TEST_JD = ([2017, 7, 9, 12, 0, 0, 2],
           [1952, 7, 9, 12, 0, 0, 1],
           [1981, 8, 19, 17, 40, 47, 2],
           [1979, 1, 26, 8, 40, 33, 0])

LON_RAD = (0, 0.19627197066038454)  # in radianti, positiva: est

# Tabella per conversione equatoriale/orizzontale da:
# http://xjubier.free.fr/en/site_pages/astronomy/coordinatesConverter.html
#            RA       DEC     ALT     AZ
TABLE = [("1h10m10s 0d0m0s", 43.08, 152.20),
         ("3h10m10s 0d0m0s", 27.89, 120.04),
         ("7h10m10s 0d0m0s", -14.28, 75.97),
         ("11h10m10s 0d0m0s", -45.45, 14.45),
         ("13h10m10s 0d0m0s", -42.88, 332.29),
         ("17h10m10s 0d0m0s", -7.28, 277.0),
         ("21h10m10s 0d0m0s", 33.77, 230.77),
         ("1h10m10s 20d0m0s", 61.27, 138.24),
         ("5h10m10s 20d0m0s", 20.77, 81.67),
         ("7h10m10s 20d0m0s", 0.14, 62.06),
         ("11h10m10s 20d0m0s", -25.92, 10.54),
         ("15h10m10s 20d0m0s", -11.81, 312.73),
         ("19h10m10s 20d0m0s", 27.88, 271.85),
         ("23h10m10s 20d0m0s", 65.12, 203.02),
         ("1h10m10s -20d0m0s", 24.01, 159.48),
         ("5h10m10s -20d0m0s", -6.63, 111.34),
         ("9h10m10s -20d0m0s", -49.23, 67.91),
         ("13h10m10s -20d0m0s", -61.27, 318.24),
         ("17h10m10s -20d0m0s", -20.77, 261.67),
         ("21h10m10s -20d0m0s", 16.70, 219.17),
         ("23h10m10s -20d0m0s", 25.92, 190.54)]

def get_time(dspec):
    "Generazione oggetto Time"
    tstring = "%4.4d-%2.2d-%2.2dT%2.2d:%2.2d:%2.2d"%tuple(dspec[:6])
    tvero = Time(tstring, format="isot", scale="utc")
    offst = TimeDelta(dspec[6]*3600, format="sec")
    tvero -= offst
    return tvero

def backandforth(value, prec):
    ums = astro.float2ums(value, precision=prec)
    return astro.ums2float(*ums)


print("""Scegli test:
    - 0: Tutti i test
    - 1: Conversione decimale / uu mm ss e viceversa
    - 2: Conversione coordinate equatoriali/altoazimutali e viceversa
    - 3: Data giuliana
    - 4: Tempo sidereo
""")
answ = input("Scelta: ").strip()

done = False
if answ == "0" or answ == "1":
    done = True
    print("\nTest conversione decimale / uu mm ss")
    base = np.linspace(0, 10, 100000)
    func = np.vectorize(lambda x: backandforth(x, 3))
    error = np.abs(func(base)-base)
    print("   Errore max. ums2float(float2ums[0..10]) 3 decimali:",np.max(error))
    func = np.vectorize(lambda x: backandforth(x, 4))
    error = np.abs(func(base)-base)
    print("   Errore max. ums2float(float2ums[0..10]) 4 decimali:",np.max(error))
    func = np.vectorize(lambda x: backandforth(x, 5))
    error = np.abs(func(base)-base)
    print("   Errore max. ums2float(float2ums[0..10]) 5 decimali:",np.max(error))

if answ == "0" or answ == "2":
    done = True
    print("\nTest conversione coordinate equatoriali in altoazimutali e viceversa")
    opc = EarthLocation.from_geodetic(lat=43.5167*u.deg,
                                      lon=11.23333*u.deg,
                                      height=0)
    now = Time("2020-03-08T12:00:00", format="isot", scale="utc", location=opc)
    sidt = now.sidereal_time("mean")

    azerrmax = 0.0
    alterrmax = 0.0
    deerrmax = 0.0
    haerrmax = 0.0
    for dat in TABLE:
        point = SkyCoord(dat[0], unit=(u.hour, u.deg))
        ha = sidt-point.ra
        ha.wrap_at(24*u.hour, inplace=True)
        ha_rad = ha.hour*astro.HOUR_TO_RAD
        azr, altr = astro.az_coords(ha_rad, point.dec.value*astro.DEG_TO_RAD)
        azd = azr*astro.RAD_TO_DEG
        altd = altr*astro.RAD_TO_DEG
        alterr = abs(altd-dat[1])
        azerr = abs(azd-dat[2])
        if azerr > azerrmax:
            azerrmax = azerr
        if alterr > alterrmax: 
            alterrmax = alterr
        ha1, de1 = astro.eq_coords(azr, altr) 
        ha1c = Angle(ha1, unit='rad')
        ha1c.wrap_at(24*u.hour, inplace=True)
        de1c = Angle(de1, unit='rad')
        haerr = abs(ha1c.value-ha_rad)*astro.RAD_TO_DEG
        deerr = abs(de1c.value-point.dec.value*astro.DEG_TO_RAD)*astro.RAD_TO_DEG
        if deerr > deerrmax: deerrmax = deerr
        if haerr > haerrmax: haerrmax = haerr
    print("Errore max. conv. equatoriale/orizzontale (gradi) - ALT: %.4f  AZ: %.4f"%(alterrmax, azerrmax))
    print("Errore max. conv. orizzontale/equatoriale (gradi) - HA: %.4f  DEC: %.4f"%(haerrmax, deerrmax))

if answ == "0" or answ == "3":
    done = True
    print("\nTest data giuliana")
    tm0 = time.time()
    times = [Time(tm0+random()*157680000, format='unix') for x in range(20)]
    maxerr = 0.0
    for tt0 in times:
        tmio = astro.jul_date(*tt0.to_value("ymdhms"))
        error = abs(tt0.jd-tmio)
        if error > maxerr:
            maxerr = error
    print("Errore max data giuliana:", error)

if answ == "0" or answ == "4":
    done = True
    print("\nTest tempo sidereo")
    tm0 = time.time()
    times = [Time(tm0+random()*86400, format='unix') for x in range(20)]
    maxerr = 0.0
    lon = 0.19627197066038454
    for tt0 in times:
        tsidmio = astro.loc_st(*tt0.to_value("ymdhms"), lon_rad=lon)
        slon = "%fh"%(lon*astro.RAD_TO_HOUR)
        tsidref = tt0.sidereal_time("mean", longitude=slon).value
        error = abs(tsidref-tsidmio)
        if error > maxerr:
            maxerr = error
    print("Errore max tempo sidereo (ore):", error)

if not done:
    print("\nScelta errata!")
