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
from widgets import WarningMsg, Field, Number, Coord, CButton, MButton, HSpacer
from telecomm import TeleCommunicator
import astro

__version__ = "1.0"
__date__ = "ottobre 2018"
__author__ = "Luca Fini (luca.fini@gmail.com)"


SLOW_REFRESH_TIME = 4000   # Millisecondi
FAST_REFRESH_TIME = 800    # Millisecondi

TSID_DIFF = 3./3600  # Ore di differenza sul tempo sidereo per warning

class LABELS:
    "Testi per labels"
    check = "Verifica t.sid. "
    conn = "Connessione "
    iniz = "Inizalizzazione "
    lat = "    Latitudine"
    lon = "Longitudine"
    title = "Controllo telescopio OPC"
    trackf = "Freq. Tracking "
    tracking = "Tracking "
    tsid = "Tempo sidereo "
    utm = "UT    "

class OnStatus(tk.Frame):
    "Widget per visualizzazione dello stato del telescopio"
    def __init__(self, parent):
        self.parent = parent
        self.tel = parent.tel
        tk.Frame.__init__(self, parent, border=2, relief=tk.GROOVE, padx=5, pady=5)
        conn_fr = tk.Frame(self)    # Linea per stato connessione
        self.w_conn = MButton(conn_fr, "", "circle", 32, label=LABELS.conn)
        self.w_conn.pack(side=tk.LEFT)
        conn_fr.pack(anchor=tk.E)

        time_fr = tk.Frame(self, pady=5)    # Linea per data/ora t.sidereo
        self.w_date = Field(time_fr)
        self.w_date.pack(side=tk.LEFT)
        self.w_ut = Coord(time_fr, label=LABELS.utm, label_side=tk.E)
        self.w_ut.pack(side=tk.LEFT)
        self.w_st = Coord(time_fr, label=LABELS.tsid, label_side=tk.E)
        self.w_st.pack(side=tk.LEFT)
        time_fr.pack()

        loc_fr = tk.Frame(self, pady=5)     # Linea per latitudine e longitudine
        self.w_lon = Coord(loc_fr, label=LABELS.lon, label_side=tk.W)
        self.w_lon.pack(side=tk.LEFT)
        self.w_lat = Coord(loc_fr, label=LABELS.lat, label_side=tk.W)
        self.w_lat.pack(side=tk.LEFT)
        loc_fr.pack(anchor=tk.W)

        stat_fr = tk.Frame(self, pady=5)    # Linea per indicatori di stato
        self.w_init = MButton(stat_fr, "", "circle", 32, label=LABELS.iniz)
        self.w_init.pack(side=tk.LEFT)
        HSpacer(stat_fr, 10)
        self.w_check = MButton(stat_fr, "", "circle", 32, label=LABELS.check)
        self.w_check.pack(side=tk.LEFT)
        stat_fr.pack(anchor=tk.E)

        trak_fr = tk.Frame(self, pady=5)    # Linea per stato tracking
        self.w_trak = MButton(trak_fr, "", "circle", 32, label=LABELS.tracking)
        self.w_trak.pack(side=tk.LEFT)
        HSpacer(trak_fr, 5)
        self.w_trakf = Number(trak_fr, label=LABELS.trackf, _format="%.4f")
        self.w_trakf.pack(side=tk.LEFT)
        trak_fr.pack(anchor=tk.W)
        self.connected = False
        self.ltime = ""
        self.stime = ""
        self.updatew()

    def _is_connected(self):
        "Aggiornamento dei campi fissi"
        if not self.connected:
            self.connected = True
            self.w_conn.set(1)
            if self.tel.opc_init():      # Inizializza con dati OPC
                self.w_init.set(1)
                self.init_static_data()
            else:
                self.w_init.set(3)


    def _is_disconnected(self):
        "Azzera campi in caso di disconnessione"
        if self.connected:
            self.w_init.set(0)
            self.w_conn.set(3)
            self.w_check.set(0)
            self.clear_all()
        self.connected = False

    def updatew(self):
        "Aggiornamento campi del widget"
        sdtime = self.tel.get_tsid()
        tsid = astro.loc_st_now()
        utime = None
        ldate = None
        status = ""
        if sdtime:
            utime = self.tel.get_ltime()
        if utime:
            ldate = self.tel.get_date()
        if ldate:
            status = self.tel.get_status()
        if not (utime and sdtime and ldate and status):
            self._is_disconnected()
        else:
            self._is_connected()
            self.decode_status(status)
            self.w_ut.set(utime)
            self.w_st.set(sdtime)
            self.w_date.set(ldate)
            if abs(sdtime-tsid) > TSID_DIFF:
                self.w_check.set(3)
            else:
                self.w_check.set(1)
        self.after(SLOW_REFRESH_TIME, self.updatew)

    def init_static_data(self):
        "Inizializza campi per dati statici dopo connessione"
        lat = self.tel.get_lat()
        lon = self.tel.get_lon()
        self.w_lat.set(lat)
        self.w_lon.set(lon)

    def clear_all(self):
        "Cancella campi dopo disconnessione"
        self.w_lat.clear()
        self.w_lon.clear()
        self.w_ut.clear()
        self.w_st.clear()
        self.w_date.clear()
        self.w_trak.set(0)
        self.w_trakf.clear()

    def decode_status(self, status):
        "Interpreta stringa di stato"
        if "n" not in status:
            self.w_trak.set(1)
            trate = self.tel.get_trate()
            self.w_trakf.set(trate)
        else:
            self.w_trak.set(0)
            self.w_trakf.clear()

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
#       self.control = OnControl(self, config)
#       self.control.pack(side=tk.LEFT)

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
    root.title(LABELS.title)
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
