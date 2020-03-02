"""
Test funzioni astronomiche per package OPC
"""

import time
from astropy.time import Time, TimeDelta
import numpy as np
import matplotlib.pylab as plt

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

def get_time(dspec):
    "Generazione oggetto Time"
    tstring = "%4.4d-%2.2d-%2.2dT%2.2d:%2.2d:%2.2d"%tuple(dspec[:6])
    tvero = Time(tstring, format="isot", scale="utc")
    offst = TimeDelta(dspec[6]*3600, format="sec")
    tvero -= offst
    return tvero

def test_1jd(dspec):
    "Test data giuliana"
    tvero = get_time(dspec)
    tmio = astro.jul_date(*dspec)
    error = abs(tvero.jd-tmio)
    return [tvero.jd, tmio, error]

def test_1tsid(dspec, lon):
    "Test tempo sidereo"
    tvero = get_time(dspec)
    tmio = astro.loc_st(*dspec[:6], utc_offset=dspec[6], lon_rad=lon)
    slon = "%fh"%(lon*astro.RAD_TO_HOUR)
    tvsid = tvero.sidereal_time("mean", longitude=slon).value
    error = abs(tvsid-tmio)
    return [slon, tvsid, tmio, error]

def backandforth(value):
    ums = astro.float2ums(value, 24, 4)
    return astro.ums2float(*ums)

def test_ums():
    "Test conversione decimale / uu mm ss"
    func = np.vectorize(backandforth)
    base = np.linspace(-0.5, 24.5, 2000)
    modbase = np.mod(base, 24)
    error = func(base)-modbase
    plt.plot(error)
    plt.grid()
    plt.show()

def main():
    "Procedura di test"
    print("Test conversione g/m/s:")
    test_ums()
    print("Test data giuliana:")
    print("a,   m,   g,   h,   m,   s, utc_offset, jd.vero,  jd.mio,  errore")
    for dspec in TEST_JD:
        result = test_1jd(dspec)
        print(*(dspec+result))

    print("Test tempo sidereo:")
    print("a,   m,   g,   h,   m,   s, utc_offset, lon(hour), tsid.vero,  tsid.mio,  errore")
    for dspec in TEST_JD:
        for lon in LON_RAD:
            result = test_1tsid(dspec, lon)
            print(*(dspec+result))

    gmtime = time.gmtime()
    gmspec = list(gmtime)[:6]+[0, 0]

    print("Tempo sidereo attuale per Greenwich")
    ret = test_1tsid(gmspec, 0)
    tsidloc = astro.loc_st_now(0)
    error = abs(ret[1]-tsidloc)
    print("   lon, tsid.vero,  tsid.mio,  errore")
    print(" ", ret[0], ret[1], tsidloc, error)

    print("\nTempo sidereo attuale per OPC")
    ret = test_1tsid(gmspec, LON_RAD[1])
    tsidloc = astro.loc_st_now(LON_RAD[1])
    error = abs(ret[1]-tsidloc)
    print("   lon, tsid.vero,  tsid.mio,  errore")
    print(" ", ret[0], ret[1], tsidloc, error)

if __name__ == "__main__":
    main()
