#!/usr/bin/python3
"""
OPC - Asservimento cupola [%s]

Uso:
        python3 dtracker.pyw [-s] [-h]

Dove:
       -h  Mostra questa pagina ed esce
       -s  Si connette al simulatore con IP: 127.0.0.1, Port: 9752
"""
import sys
import time
import math

import tkinter as tk
from widgets import WarningMsg, Field, Number, Coord, CButton, H4_FONT, BD_FONT

from telecomm import TeleCommunicator
import astro
import configure
from interpolator import Interpolator

__author__ = "Luca Fini"
__version__ = "1.0"
__date__ = "Ottobre 2020"

try:
    import win32com.client as wcl
    from pywintypes import com_error as COM_ERROR
    SIMULATED = False
except ModuleNotFoundError:
    import ascom_fake as wcl
    COM_ERROR = Exception("Fake exception")
    print("Using ASCOM_FAKE !!!")
    SIMULATED = True

UPDATE_PERIOD_MS = 2000   # Periodo aggiornamento (millisec)
BR_EAST = "E"
BR_WEST = "W"
SIDES = "EW"

INTERP_E = Interpolator("e")
INTERP_W = Interpolator("w")

DOME_POS_ERROR = 1.0  # Max Errore inseguimento cupola (gradi)

class GLOB:           # pylint: disable=R0903
    "globals senza usare global"
    config = {}
    goon = False
    error = ""
    dome = None

def get_tel(telcom):
    "Legge posizione telescopio"
    ha_h = telcom.get_current_ha()
    de_d = telcom.get_current_de()
    side = telcom.get_pside()
    if ha_h is None or de_d is None or side is None:
        time.sleep(0.3)
        if ha_h is None:
            ha_h = telcom.get_current_ha()
        elif de_d is None:
            de_d = telcom.get_current_de()
        elif side is None:
            side = telcom.get_pside()
    if ha_h is None or de_d is None or side is None:
        return None
    return ha_h, de_d, side[0]

def dome_azimuth(ha_h, de_d, side):
    "Calcola azimuth cupola da coordinate telescopio"
    GLOB.error = ""
    if side == BR_EAST:
        az_deg = INTERP_E.interpolate(ha_h, de_d)
    elif side == BR_WEST:
        az_deg = INTERP_W.interpolate(ha_h, de_d)
    else:
        GLOB.error = "ERR: Pier side (%s)"%side
        return None
    if math.isnan(az_deg):
        GLOB.error = "ERR: Interpolazione (ha:%.2f, de:%.2f)"%(ha_h, de_d)
        az_deg = None
    return az_deg

def move_dome(dome, target):
    "Movimento cupola"
    azm = dome.Azimuth
    slw = dome.Slewing
    if target is None:
        return azm, slw
    if abs(target-azm) > DOME_POS_ERROR:
        if slw:
            return azm, slw
        target = int(target)
        dome.SlewToAzimuth(target)
        slw = True
    return azm, slw

class DTracker(tk.Frame):            # pylint: disable=R0901,R0902
    "Widget per asservimento cupola"
    def __init__(self, parent):
        super().__init__(parent)
        self.tel = TeleCommunicator(GLOB.config["tel_ip"], GLOB.config["tel_port"])
        top_fr = tk.Frame(self)
        tk.Label(top_fr, text="  Telescope ", font=H4_FONT).grid(row=1, column=1)
        tel_info = tk.Frame(top_fr)
        tk.Label(tel_info, text="  HA(h): ").pack(side=tk.LEFT)
        self.tel_ha = Coord(tel_info)
        self.tel_ha.pack(side=tk.LEFT)
        tk.Label(tel_info, text="  DE(d): ").pack(side=tk.LEFT)
        self.tel_de = Coord(tel_info)
        self.tel_de.pack(side=tk.LEFT)
        tk.Label(tel_info, text="  side: ").pack(side=tk.LEFT)
        self.tside = tk.Label(tel_info, text="", width=3, bg="black", fg="lightgreen", font=BD_FONT)
        self.tside.pack(side=tk.LEFT)
        tk.Label(tel_info, text="  ").pack(side=tk.LEFT)
        tel_info.grid(row=1, column=2)
        self.tel_led = CButton(top_fr, "", color="red")
        self.tel_led.grid(row=1, column=3)
        tk.Label(top_fr, text="  Dome ", font=H4_FONT).grid(row=3, column=1, sticky=tk.E)
        dom_info = tk.Frame(top_fr)
        tk.Label(dom_info, text="  Az(d): ").pack(side=tk.LEFT)
        self.dome_az = Number(dom_info, width=4)
        self.dome_az.pack(side=tk.LEFT)
        tk.Label(dom_info, text="  Mov: ").pack(side=tk.LEFT)
        self.dome_mov = Field(dom_info, width=6)
        self.dome_mov.pack(side=tk.LEFT)
        tk.Label(dom_info, text="  Tgt(d): ").pack(side=tk.LEFT)
        self.trgt_az = Number(dom_info, width=4)
        self.trgt_az.pack(side=tk.LEFT)
        dom_info.grid(row=3, column=2, sticky=tk.W)
        self.dome_led = CButton(top_fr, "", color="red")
        self.dome_led.grid(row=3, column=3)
        tk.Label(top_fr, text="  ").grid(row=1, column=4)
        tk.Frame(top_fr, border=3, relief=tk.RIDGE, bg="black").grid(row=2, column=1,
                                                                     columnspan=4, sticky=tk.W+tk.E)
        top_fr.pack()
        self.stline = tk.Label(self, text="", border=2, relief=tk.RIDGE, bg="white")
        self.stline.pack(expand=1, fill=tk.X)
        self.target_az = None
        self.update()

    def update(self):
        "Aggiornamento stato del widget"
        telrep = get_tel(self.tel)
        if telrep is None:
            self.tel_led.clear()
            self.tel_ha.clear()
            self.tel_de.clear()
            self.setinfo("Attesa comunicazione con telescopio")
            self.tside.configure(text="")
        else:
            self.tel_led.set("green")
            self.tel_ha.set(telrep[0])
            self.tel_de.set(telrep[1])
            fgc = "lightgreen" if telrep[2] in SIDES else "hotpink"
            self.tside.configure(text=telrep[2], fg=fgc)
            self.target_az = dome_azimuth(*telrep)
            self.trgt_az.set(self.target_az)
            if self.target_az is None:
                self.setinfo(GLOB.error)
            else:
                self.setinfo("")
        azm = None
        try:
            azm, slw = move_dome(GLOB.dome, self.target_az)
        except COM_ERROR:
            self.setinfo("ERR: comunicazione con cupola interrotta")
            self.dome_mov.clear()
            self.dome_az.clear()
            self.dome_led.clear()
        else:
            self.dome_led.set("green")
            self.dome_az.set(azm)
            if slw:
                self.dome_mov.set("SLEW", fg="orange")
            else:
                self.dome_mov.set("IDLE", fg="lightgreen")
        self.after(UPDATE_PERIOD_MS, self.update)

    def setinfo(self, info):
        "Scrive in linea di stato"
        self.stline.config(text=info)

def do_quit(root, wdgt):
    "Termina appicazione"
    wdgt.setinfo("Termina applicazione")
    if SIMULATED:
        GLOB.dome.Dispose()
    root.destroy()

def main():
    "funzione main"
    root = tk.Tk()

    if '-s' in sys.argv:
        GLOB.config = {"tel_ip": "127.0.0.1",
                       "tel_port": 9753,
                       "lat": astro.OPC.lat_rad,
                       "lon": astro.OPC.lon_rad,
                       "debug": 1,
                       "dome_ascom": "OCS.Dome",
                       "filename": ""}
        mode = " [Simulatore telescopio]"
    else:
        GLOB.config = configure.get_config()
        mode = ""

    if SIMULATED:
        mode += " [No WIN]"
    root.title("OPC - Asservimento cupola"+mode)

    if "-h" in sys.argv:
        vinfo = "Vers. %s - %s, %s"%(__version__, __author__, __date__)
        msg = __doc__%vinfo
        wdg = WarningMsg(root, msg)
    else:
        GLOB.dome = wcl.Dispatch(GLOB.config["dome_ascom"])
        if not GLOB.dome.Connected:
            msg = "Errore comunicazione con cupola"
            wdg = WarningMsg(root, msg)
        else:
            wdg = DTracker(root)
            root.protocol("WM_DELETE_WINDOW", lambda r=root, w=wdg: do_quit(r, w))
    wdg.pack()
    root.mainloop()

if __name__ == "__main__":
    main()
