"""
Calcolo azimut cupola per interpolazione da tabelle

Uso per test:

    python interpolator.py   Esegue test rapido

    python e/w               Test interattivo est/ovest
"""

import sys
import os
import pickle

__version__ = "1.0"

RAD_2_DEG = 57.29577951308232
HOUR_2_DEG = 15.0

class Interpolator:
    "Interpolatore per posizione cupola"
    def __init__(self, side, de_units="D", ha_units="H"):
        "Costruttore. datadir: directory per file tabelle"
        datadir = os.path.dirname(__file__)
        fname = "dometab_"+side+".p"
        datafile = os.path.join(datadir, "tables", fname)
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

    def interpolate(self, hag, dec):
        "Trova valore azimut per interpolazione"
        try:
            i_ha = self.cvt_ha(hag)
            i_de = self.cvt_de(dec)
            val = self.data[i_de][i_ha]%360
        except Exception:
            val = float("nan")
        return val

def quicktest():
    "Codice di test"
    interp1_e = Interpolator("e")
    interp2_e = Interpolator("e", de_units="R", ha_units="R")
    interp1_w = Interpolator("w")
    interp2_w = Interpolator("w", de_units="R", ha_units="R")
    print('interpolate(0,0) E:', interp1_e.interpolate(0.0, 0.0))
    print('interpolate(0,0, de_units="R", ha_units="R") E:', interp2_e.interpolate(0.0, 0.0))
    print("interpolate(0.5,0) E:", interp1_e.interpolate(0.5, 0.0))
    print('interpolate(0.13,0.0, de_units="R", ha_units="R") E:',
          interp2_e.interpolate(0.1308996938995747, 0.0))
    print("interpolate(0.0,0.0) W:", interp1_w.interpolate(0.0, 0.0))
    print('interpolate(0,0, de_units="R", ha_units="R") W:', interp2_w.interpolate(0.0, 0.0))
    print("interpolate(0.5,0.0) W:", interp1_w.interpolate(0.5, 0.0))
    print('interpolate(0.13,0.0, de_units="R", ha_units="R") E:',
          interp2_w.interpolate(0.1308996938995747, 0.0))
    print('interpolate(-12,0) E:', interp1_e.interpolate(-12, 0.0))

def interactive(side):
    "Test interattivo"
    if side == "e":
        interp = Interpolator("e", de_units="R", ha_units="R")
    else:
        interp = Interpolator("w", de_units="R", ha_units="R")
    while True:
        cmd = input("Coordinate (rad) HA DE: ")
        coords = cmd.split()
        if len(coords) < 2:
            break
        fcoords = tuple(float(x) for x in coords)
        azm = interp.interpolate(*fcoords)
        print("Interpolate(%s, %f, %f) = %f (deg)"%(side, fcoords[0], fcoords[1], azm))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        quicktest()
    elif sys.argv[1][0].lower() == "e":
        interactive("e")
    elif sys.argv[1][0].lower() == "w":
        interactive("w")
    else:
        print(__doc__)
