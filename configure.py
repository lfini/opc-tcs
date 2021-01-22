"""
configure.py. Vers. %s - %s. %s

Gestione file di configurazione

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
from widgets import WarningMsg

__version__ = "1.2"
__date__ = "gennaio 2020"
__author__ = "Luca Fini"

SHOW_CONFIG = """
  File configurazione - {filename}
             Versione - {version}

           Latitudine Osservatorio: {lat} radianti
          Longitudine Osservatorio: {lon} radianti

    Indirizzo IP server telescopio: {tel_ip}
            Port server telescopio: {tel_port}

       Identificatore ASCOM cupola: {dome_ascom}
          Posizione di park cupola: {park_position} gradi
    Errore max inseguimento cupola: {dome_maxerr} gradi
      Ampiezza zona critica cupola: {dome_critical} gradi
Periodo di aggiornamento posizione: {repeat} secondi
"""

NO_CONFIG = """
  File di configurazione mancante.
  o incompleto
"""

NOTA = """
NOTA: la configurazione ha effetto dopo un restart
"""

HOMEDIR = os.path.expanduser("~")
CONFIG_FILE = ".opc_config"

#  Valori di default dei parametri di configurazione

LAT_OPC_RAD = astro.OPC.lat_rad
LON_OPC_RAD = astro.OPC.lon_rad
TEL_IP = "192.168.0.67"
TEL_PORT = 9999

DEF_PARK_POS = 1
DOME_ASCOM = "OCS.Dome"
DOME_MAXERR = 0.5
DOME_CRITICAL = 4.0
REPEAT = 2.0

VERSION = 3

CONFIG_PATH = os.path.join(HOMEDIR, CONFIG_FILE)

SIMUL_CONFIG = {"lat": LAT_OPC_RAD,
                "lon": LON_OPC_RAD,
                "dome_ascom": DOME_ASCOM,
                "tel_ip": "127.0.0.1",
                "tel_port": 9753,
                "filename": CONFIG_PATH,
                "park_position": 1,
                "dome_maxerr": DOME_MAXERR,
                "dome_critical": DOME_CRITICAL,
                "repeat": REPEAT,
                "version": 0
               }

DEFAULT_CONFIG = {"lat": LAT_OPC_RAD,
                  "lon": LON_OPC_RAD,
                  "dome_ascom": DOME_ASCOM,
                  "tel_ip": TEL_IP,
                  "tel_port": TEL_PORT,
                  "filename": CONFIG_PATH,
                  "park_position": 1,
                  "dome_maxerr": DOME_MAXERR,
                  "dome_critical": DOME_CRITICAL,
                  "repeat": REPEAT,
                  "version": VERSION
                 }

def as_string(config):
    "riporta configurazione come stringa stampabile"
    return SHOW_CONFIG.format_map(config)


def store_config(config=None):
    "Salva configurazione"
    if not config:
        config = DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "w") as fpt:
            json.dump(config, fpt, indent=2)
    except Exception as excp:
        msg_text = "\nErrore configurazione:\n\n   "+str(excp)+"\n"
    else:
        msg_text = as_string(config)
        msg_text += NOTA
    return msg_text

def get_config(required_version=VERSION):
    "Legge il file di configurazione"
    if required_version == 0:
        return SIMUL_CONFIG
    fname = os.path.join(HOMEDIR, CONFIG_FILE)
    try:
        with open(fname) as fpt:
            config = json.load(fpt)
    except FileNotFoundError:
        config = {}
    if config.get("version", 0) < required_version:
        return {}
    return config

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
        cur_conf = get_config(VERSION)
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
                 text="Posizione parcheggio cupola (gradi): ").grid(row=7, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Errore max inseguimento cupola (gradi): ").grid(row=8, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Ampiezza zona critica cupola (gradi): ").grid(row=9, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Periodo aggiornamento posizione (sec): ").grid(row=10, column=0, sticky=tk.E)
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

        self.park_pos = tk.Entry(self.body)
        the_park_pos = cur_conf.get("park_position", DEF_PARK_POS)
        self.park_pos.insert(0, the_park_pos)
        self.park_pos.grid(row=7, column=1)

        self.dome_maxerr = tk.Entry(self.body)
        the_dome_maxerr = cur_conf.get("dome_maxerr", DOME_MAXERR)
        self.dome_maxerr.insert(0, the_dome_maxerr)
        self.dome_maxerr.grid(row=8, column=1)

        self.dome_crit = tk.Entry(self.body)
        the_dome_crit = cur_conf.get("dome_critical", DOME_CRITICAL)
        self.dome_crit.insert(0, the_dome_crit)
        self.dome_crit.grid(row=9, column=1)

        self.repeat = tk.Entry(self.body)
        the_repeat = cur_conf.get("repeat", REPEAT)
        self.repeat.insert(0, the_repeat)
        self.repeat.grid(row=10, column=1)

        tk.Frame(self.body, border=2, height=3,
                 relief=tk.RIDGE).grid(row=11, column=0, columnspan=2, sticky=tk.E+tk.W)
        if force:
            tk.Button(self.body, text="Registra",
                      command=self.done).grid(row=12, column=1, sticky=tk.E)
        else:
            tk.Button(self.body, text="Registra",
                      command=self.done).grid(row=12, column=0, sticky=tk.W)
            tk.Button(self.body, text="Esci",
                      command=self.quit).grid(row=12, column=1, sticky=tk.E)
        self.body.pack()

    def done(self):
        "Salva configurazione ed esci"
        try:
            rlat = float(self.lat.get())
            rlon = float(self.lon.get())
            tel_ip = self.tel_ip.get()
            tel_port = int(self.tel_port.get())
            dome_ascom = self.dome_ascom.get()
            park_position = int(self.park_pos.get())
            dome_maxerr = float(self.dome_maxerr.get())
            dome_crit = float(self.dome_crit.get())
            repeat = float(self.repeat.get())
        except Exception as excp:
            msg_text = "\nErrore formato dati: \n\n   %s\n"%str(excp)
        else:
            config = {"lat": rlat, "lon": rlon, "dome_ascom": dome_ascom,
                      "tel_ip": tel_ip, "tel_port": tel_port, "filename": CONFIG_PATH,
                      "dome_maxerr": dome_maxerr, "dome_critical": dome_crit,
                      "repeat": repeat, "park_position": park_position,
                      "version": VERSION}
            msg_text = store_config(config)
        self.body.destroy()
        msg = WarningMsg(self, msg_text)
        msg.pack()

    def quit(self):
        "Esci distruggendo il master"
        self.master.destroy()

def main():
    "Lancia GUI per configurazione"
    root = tk.Tk()
    root.title("OPC - Configurazione parametri")
    if "-h" in sys.argv:
        msg = __doc__ % (__version__, __author__, __date__)
        wdg1 = WarningMsg(root, msg)
    else:
        config = get_config(VERSION)
        if "-s" in sys.argv:
            if config:
                wdg1 = WarningMsg(root, as_string(config))
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
