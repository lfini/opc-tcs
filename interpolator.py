"""
Calcolo azimut cupola per interpolazione tabelle
"""

import sys
import os
import pickle

__version__ = "1.1"

RAD_2_DEG = 57.29577951308232
HOUR_2_DEG = 15.0

class Interpolator:
    "Interpolatore per posizione cupola"
    def __init__(self, side, de_units="D", ha_units="H"):
        "Costruttore. side=e/w"
        datadir = os.path.dirname(__file__)
        fname = "dometab_"+side+".p"
        datafile = os.path.join(datadir, fname)
        with open(datafile, "rb") as fpt:
            table = pickle.load(fpt)
        self.__doc__ = table["DOC"]
        self.data = table["DATA"]
        self.side = table["SIDE"]
        de_0 = table["DE_0"]
        ha_0 = table["HA_0"]*HOUR_2_DEG
        if de_units == "R":
            self.cvt_de = lambda de: int(de*RAD_2_DEG-de_0)
        else:
            self.cvt_de = lambda de: int(de-de_0)
        if ha_units == "H":
            self.cvt_ha = lambda ha: int(ha*HOUR_2_DEG-ha_0)
        elif ha_units == "R":
            self.cvt_ha = lambda ha: int(ha*RAD_2_DEG-ha_0)
        else:
            self.cvt_ha = lambda ha: int(ha-ha_0)

    def interpolate(self, hra, dec):
        "Trova valore azimut per interpolazione"
        try:
            i_ha = self.cvt_ha(hra)
            i_de = self.cvt_de(dec)
            val = self.data[i_de][i_ha]%360
        except:
            val = float("nan")
        return val

def main():
    "Codice di test"
    if "-w" in sys.argv:
        side = "w"
    else:
        side = "e"

    interp = Interpolator(side)
    while True:
        answ = input("ha(ore) de(gradi)? ").strip()
        if not answ:
            break
        ha_h, de_d = (float(x) for x in answ.split())
        az_d = interp.interpolate(ha_h, de_d)
        print("Azimuth(gradi):", az_d)

if __name__ == "__main__":
    main()
