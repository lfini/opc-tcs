"""
Calcolo azimut cupola per interpolazione tabelle

Le tabelle vengono generate dalla procedura tel_model.py
e sono contenute nei files: dometab_e.p e dometab_w.p
"""

import sys
import os
import pickle

__version__ = "1.1"
__author__ = "Luca Fini"
__date__ = "Dicembre 2020"

class Interpolator:
    """
Interpolatore per posizione cupola

tabdir: Directory per file tabelle
side:   e=est / w=ovest
"""
    def __init__(self, tabdir=None, side="e"):
        "Costruttore. tabdir: directory per file tabelle"
        if tabdir is None:
            self.tabdir = os.path.dirname(__file__)
        else:
            self.tabdir = tabdir
        fname = "dometab_"+side+".p"
        datafile = os.path.join(self.tabdir, fname)
        with open(datafile, "rb") as fpt:
            table = pickle.load(fpt)
        self.data = table["DATA"]
        self.side = table["SIDE"]
        self.ha_step = table["HA_STEP"]
        self.de_min = table["DE_0"]
        self.c_de = 1./table["DE_STEP"]
        self.c_ha = 1./table["HA_STEP"]
        self.ha_grid = tuple(x*self.ha_step for x in range(len(self.data[0])))

    def de_constant(self, de):           # pylint: disable=C0103
        "Fornisce linea a declinazione costante"
        try:
            azl = self.data[int((de-self.de_min)*self.c_de+.5)]
        except IndexError:
            azl = None
        return azl

    def interpolate(self, ha, de):           # pylint: disable=C0103
        "Trova azimut cupola per interpolazione"
        ha %= 24.
        try:
            azl = self.data[int((de-self.de_min)*self.c_de+.5)]
            haix = int(ha*self.c_ha)
            az0 = azl[haix]
            val = (az0+(azl[haix+1]-az0)*self.c_ha*(ha-self.ha_grid[haix]))%360.
        except IndexError:
            val = float("nan")
        return val

def main():
    "Codice di test"
    if "-w" in sys.argv:
        side = "w"
    else:
        side = "e"

    interp = Interpolator(side=side)
    while True:
        answ = input("ha(ore) de(gradi)? ").strip()
        if not answ:
            break
        ha_h, de_d = (float(x) for x in answ.split())
        az_d = interp.interpolate(ha_h, de_d)
        print("Azimuth(gradi):", az_d)

if __name__ == "__main__":
    main()
