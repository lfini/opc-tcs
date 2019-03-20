"""
GUI per controllo manuale telescopio OPC. Vers. %s - %s, %s

Uso:
        python3 onstep.py [-h] [-d]

Dove:
       [-d]  Modo debug: si connette al simulatore con IP: 127.0.0.1, Port: 9752
"""


import sys
import time
import tkinter as tk

import configure as conf
from widgets import WarningMsg, Field, Coord, CButton
from telecomm import TeleCommunicator
import astro

__version__ = "1.0"
__date__ = "ottobre 2018"
__author__ = "Luca Fini (luca.fini@gmail.com)"


SLOW_REFRESH_TIME = 4000   # Millisecondi
FAST_REFRESH_TIME = 800    # Millisecondi

class OnStatus(tk.Frame):
    "Widget per visualizzazione dello stato del telescopio"
    def __init__(self, parent):
        self.parent = parent
        self.tel = parent.tel
        tk.Frame.__init__(self, parent, border=1, relief=tk.GROOVE, padx=3, pady=3)
        time_fr = tk.Frame(self)
        self.date = Field(time_fr)
        self.date.pack(side=tk.LEFT)
        self.ut_time = Coord(time_fr, label="UT  ", label_side=tk.E)
        self.ut_time.pack(side=tk.LEFT)
        self.sd_time = Coord(time_fr, label="Tempo sidereo apparente locale ", label_side=tk.E)
        self.sd_time.pack(side=tk.LEFT)
        time_fr.pack()
        self.connected = False
        self.ltime = ""
        self.stime = ""
        self.updatew()

    def _update_on_connect(self):
        "Aggiornamento dei campi fissi"
        self.connected = True

    def _clear_on_disconnect(self):
        "Azzera campi in caso di disconnessione"
        self.connected = False

    def updatew(self):
        "Aggiornamento campi del widget"
        
        sdtime = self.tel.get_tsid()
        utime = None
        ldate = None
        if sdtime:
            utime = self.tel.get_ltime()
        if utime:
            ldate = self.tel.get_date()
        if not (utime and sdtime and ldate):
            self._clear_on_disconnect()
        else:
            if not self.connected:
                self._update_on_connect()
            self.ut_time.set(utime)
            self.sd_time.set(sdtime)
            self.date.set(ldate)

def _fmtlatlon(lat, lon):
    "Format logntudine e latitudine (in radianti)"
    if lon < 0.0:
        eawe = "W"
    elif lon > 0:
        eawe = "E"
    else:
        eawe = " "
    if lat < 0.0:
        noso = "S"
    elif lat > 0:
        noso = "N"
    else:
        noso = " "
    fmtll = "%2.2d:%2.2d:%2.2d"
    stlat = fmtll%astro.rad2dms(lat)
    stlon = fmtll%astro.rad2dms(lon)
    return "Lat: %s %s   Lon: %s %s"%(stlat, noso,
                                      stlon, eawe)

class OnControl(tk.Frame):
    "Widget per setup del telescopio"
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.tel = parent.tel
        tk.Frame.__init__(self, parent, border=1, relief=tk.GROOVE, padx=3, pady=3)
        tk.Label(self, text="Data/ora:").pack(anchor=tk.W)
        self.btime = CButton(self, "btime", color="indianred", text="Set",
                             label="", label_side=tk.E, command=self.set_tel)
        self.btime.pack(anchor=tk.W)
        tk.Label(self, text=" ").pack(anchor=tk.W)
        tk.Label(self, text="Coordinate geografiche:").pack(anchor=tk.W)
        tlabel = _fmtlatlon(config["lat"], config["lon"])
        self.bll = CButton(self, "bll", color="indianred", text="Set",
                           label=tlabel, label_side=tk.E, command=self.set_tel)
        self.bll.pack(anchor=tk.W)
        self.updatew()

    def set_tel(self, bname):
        if bname == "btime":
            self.tel.set_time()
        elif bname == "bll":
            self.tel.set_lon(astro.rad2deg(self.config["lon"]))
            self.tel.set_lat(astro.rad2deg(self.config["lat"]))

    def updatew(self):
        now = time.strftime("%x %X %z")+" (LST: %2.2d:%2.2d:%2.2d)"%astro.float2ums(astro.loc_st_now())
        self.btime.set_label(now)
        self.after(FAST_REFRESH_TIME, self.updatew)

class TCS(tk.Frame):
    "Pannello per controllo telescopio"
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        tk.Frame.__init__(self, parent, border=1, relief=tk.GROOVE, padx=3, pady=3)
        self.tel = TeleCommunicator(config["tel_ip"], config["tel_port"])
        self.status = OnStatus(self)
        self.status.pack(side=tk.LEFT)
        self.control = OnControl(self, config)
        self.control.pack(side=tk.LEFT)

def main():
    "funzione main"
    if '-d' in sys.argv:
        config = {"dome_ip": "127.0.0.1",
                  "dome_port": 9752,
                  "tel_ip": "127.0.0.1",
                  "tel_port": 9753,
                  "lat": astro.OPC.lat_rad,
                  "lon": astro.OPC.lon_rad,
                  "debug": 1,
                  "filename": ""}
    else:
        config = conf.get_config()

    root = tk.Tk()
    root.title("Osservatorio Polifunzionale del Chianti")
    if "-h" in sys.argv:
        msg = __doc__ % (__version__, __author__, __date__)
        wdg1 = WarningMsg(root, msg)
    elif '-i' in sys.argv:
        str_conf = conf.show_config(config)
        wdg1 = WarningMsg(root, str_conf)
    elif not config:
        wdg1 = WarningMsg(root, conf.NO_CONFIG)
    else:
        wdg1 = TCS(root, config)
    wdg1.pack()
    root.mainloop()

if __name__ == "__main__":
    main()


