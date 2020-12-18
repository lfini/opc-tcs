"""
configure.py. Vers. %s - %s. %s

Lettura e creazione file di configurazione

Uso:
      python configure.py [-s] [-h]

dove:
      -s  Mostra file di configurazione
"""

import sys
import json
import os
import re
import tkinter as tk
import astro
from widgets import WarningMsg, SelectionMsg

__version__ = "1.0"
__date__ = "ottobre 2018"
__author__ = "Luca Fini"

SHOW_CONFIG = """
  File configurazione - {filename}

        Latitudine Osservatorio: {lat} rad.
       Longitudine Osservatorio: {lon} rad.

 Indirizzo IP server telescopio: {tel_ip}
         Port server telescopio: {tel_port}

    Identificatore ASCOM cupola: {dome_ascom}
 Errore max inseguimento cupola: {dome_maxerr} gradi
   Ampiezza zona critica cupola: {dome_critical} gradi
"""

NO_CONFIG = """
  File di configurazione mancante.
"""

HOMEDIR = os.path.expanduser("~")
CONFIG_FILE = ".opc_config"

#  Valori di default dei parametri di configurazione

LAT_OPC_RAD = astro.OPC.lat_rad
LON_OPC_RAD = astro.OPC.lon_rad
TEL_IP = "192.168.0.67"
TEL_PORT = 9999

DOME_ASCOM = "OCS.Dome"
DOME_MAXERR = 0.5
DOME_CRITICAL = 4.0

def get_config():
    "Legge il file di configurazione"
    fname = os.path.join(HOMEDIR, CONFIG_FILE)
    try:
        with open(fname) as fpt:
            config = json.load(fpt)
        config["filename"] = fname
    except FileNotFoundError:
        config = {}
    if "dome_maxerr" in config:   # Forza riconfigurazione se manca item
        return config
    return {}

PUNCT = re.compile("[^0-9.]+")
def str2rad(line):
    "Converte tre numeri (g,m,s) in radianti"
    three = [float(x) for x in PUNCT.split(line)]
    rad = astro.dms2rad(*three)
    return rad

class MakeConfig(tk.Frame):          # pylint: disable=R0901
    "Crea file di configurazione"
    def __init__(self, parent, force=False):
        tk.Frame.__init__(self, parent, padx=10, pady=10)
        cur_conf = get_config()
        self.body = tk.Frame(self)
        tk.Label(self.body,
                 text="Latitudine osservatorio (rad): ").grid(row=0, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Longitudine osservatorio (rad): ").grid(row=1, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Indirizzo IP server telescopio: ").grid(row=4, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Port IP server telescopio: ").grid(row=5, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Identificatore ASCOM cupola: ").grid(row=6, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Errore max inseguimento cupola: ").grid(row=7, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Ampiezza zona critica cupola: ").grid(row=8, column=0, sticky=tk.E)
        self.lat = tk.Entry(self.body)
        the_lat = cur_conf.get("lat", str(LAT_OPC_RAD))
        self.lat.insert(0, the_lat)
        self.lat.grid(row=0, column=1)
        self.lon = tk.Entry(self.body)
        the_lon = cur_conf.get("lon", str(LON_OPC_RAD))
        self.lon.insert(0, the_lon)
        self.lon.grid(row=1, column=1)
        self.tel_ip = tk.Entry(self.body)
        the_tel_ip = cur_conf.get("tel_ip", TEL_IP)
        self.tel_ip.insert(0, the_tel_ip)
        self.tel_ip.grid(row=4, column=1)
        self.tel_port = tk.Entry(self.body)
        the_tel_port = cur_conf.get("tel_port", TEL_PORT)
        the_tel_port = str(the_tel_port) if the_tel_port else ""
        self.tel_port.insert(0, the_tel_port)
        self.tel_port.grid(row=5, column=1)

        self.dome_ascom = tk.Entry(self.body)
        the_dome_ascom = cur_conf.get("dome_ascom", DOME_ASCOM)
        self.dome_ascom.insert(0, the_dome_ascom)
        self.dome_ascom.grid(row=6, column=1)

        self.dome_maxerr = tk.Entry(self.body)
        the_dome_maxerr = cur_conf.get("dome_maxerr", DOME_MAXERR)
        self.dome_maxerr.insert(0, the_dome_maxerr)
        self.dome_maxerr.grid(row=7, column=1)

        self.dome_crit = tk.Entry(self.body)
        the_dome_crit = cur_conf.get("dome_critical", DOME_CRITICAL)
        self.dome_crit.insert(0, the_dome_crit)
        self.dome_crit.grid(row=8, column=1)

        tk.Frame(self.body, border=2, height=3,
                 relief=tk.RIDGE).grid(row=9, column=0, columnspan=2,  sticky=tk.E+tk.W)
        if force:
            tk.Button(self.body, text="Registra", command=self.done).grid(row=10, column=1, sticky=tk.E)
        else:
            tk.Button(self.body, text="Registra", command=self.done).grid(row=10, column=0, sticky=tk.W)
            tk.Button(self.body, text="Esci", command=self.cancel).grid(row=10, column=1, sticky=tk.E)
        self.body.pack()

    def done(self):
        "Salva configurazione ed esci"
        fname = os.path.join(HOMEDIR, CONFIG_FILE)
        try:
            rlat = float(self.lat.get())
            rlon = float(self.lon.get())
            tel_ip = self.tel_ip.get()
            tel_port = int(self.tel_port.get())
            dome_ascom = self.dome_ascom.get()
            dome_maxerr = float(self.dome_maxerr.get())
            dome_crit = float(self.dome_crit.get())
        except Exception as excp:
            msg_text = "\nErrore formato dati: \n\n   %s\n"%str(excp)
        else:
            config = {"lat": rlat, "lon": rlon, "dome_ascom": dome_ascom,
                      "tel_ip": tel_ip, "tel_port": tel_port, "filename": fname,
                      "dome_maxerr": dome_maxerr, "dome_critical": dome_crit}
            try:
                with open(fname, "w") as fpt:
                    json.dump(config, fpt, indent=2)
            except Exception as excp:
                msg_text = "\nErrore configurazione:\n\n   "+str(excp)+"\n"
            else:
                msg_text = SHOW_CONFIG.format_map(config)
        self.body.destroy()
        msg = WarningMsg(self, msg_text)
        msg.pack()

    def cancel(self):
        "Esci senza salvare confiogurazione"
        self.master.destroy()

def main():
    "Lancia GUI per configurazione"
    root = tk.Tk()
    root.title("OPC - Configurazione parametri")
    if "-h" in sys.argv:
        msg = __doc__ % (__version__, __author__, __date__)
        wdg1 = WarningMsg(root, msg)
    else:
        config = get_config()
        if "-s" in sys.argv:
            if config:
                wdg1 = WarningMsg(root, SHOW_CONFIG.format_map(config))
            else:
                wdg1 = WarningMsg(root, NO_CONFIG)
        else:
            if config:
                wdg1 = MakeConfig(root)
            else:
                wdg1 = MakeConfig(root, force=True)
    wdg1.pack()
    root.mainloop()

if __name__ == "__main__":
    main()
