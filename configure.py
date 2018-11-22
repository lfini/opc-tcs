"""
configure.py. Vers. %s - %s. %s

Lettura e creazione file di configurazione

Uso:
      python configure.py [-c] [-h]

dove:
      -c  Crea/modifica file di configurazione
"""

import sys
import json
import os
import re
import tkinter as tk
import astro
from widgets import WarningMsg

__version__ = "1.0"
__date__ = "ottobre 2018"
__author__ = "Luca Fini"

SHOW_CONFIG = """
  File configurazione - {filename}

        Latitudine Osservatorio: {lat} rad.
       Longitudine Osservatorio: {lon} rad.

     Indirizzo IP server cupola: {dome_ip}
             Port server cupola: {dome_port}

 Indirizzo IP server telescopio: {tel_ip}
         Port server telescopio: {tel_port}
"""

NO_CONFIG = """
  File di configurazione non trovato.

  Per crearlo: 

      python configure.py -c

  Per ulteriori informazioni:

      python configure.py -h

  N.B.: È richiesto python3
"""


HOMEDIR = os.path.expanduser("~")
CONFIG_FILE = ".opc_config"

LAT_OPC_RAD = 0.7596254681096652
LON_OPC_RAD = 0.19627197066038454

def get_config():
    "Legge il file di configurazione"
    fname = os.path.join(HOMEDIR, CONFIG_FILE)
    try:
        with open(fname) as fpt:
            config = json.load(fpt)
        config["filename"] = fname
    except Exception:
        config = {}
    return config

def show_config():
    "genera informazione su configurazione"
    config = get_config()
    if config:
        return SHOW_CONFIG.format_map(config)
    return NO_CONFIG

PUNCT = re.compile("[^0-9.]+")
def str2rad(line):
    "Converte tre numeri (g,m,s) in radianti"
    three = [float(x) for x in PUNCT.split(line)]
    rad = astro.dms2rad(*three)
    return rad

class MakeConfig(tk.Frame):
    "Crea file di configurazione"
    def __init__(self, parent):
        tk.Frame.__init__(self, parent, padx=10, pady=10)
        cur_conf = get_config()
        self.body = tk.Frame(self)
        tk.Label(self.body,
                 text="Latitudine osservatorio (rad): ").grid(row=0, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Longitudine osservatorio (rad): ").grid(row=1, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Indirizzo IP server cupola: ").grid(row=2, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Port IP server cupola: ").grid(row=3, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Indirizzo IP server telescopio: ").grid(row=4, column=0, sticky=tk.E)
        tk.Label(self.body,
                 text="Port IP server telescopio: ").grid(row=5, column=0, sticky=tk.E)
        self.lat = tk.Entry(self.body)
        the_lat = cur_conf.get("lat", str(LAT_OPC_RAD))
        self.lat.insert(0, the_lat)
        self.lat.grid(row=0, column=1)
        self.lon = tk.Entry(self.body)
        the_lon = cur_conf.get("lon", str(LON_OPC_RAD))
        self.lon.insert(0, the_lon)
        self.lon.grid(row=1, column=1)
        self.dome_ip = tk.Entry(self.body)
        the_dome_ip = cur_conf.get("dome_ip", "")
        self.dome_ip.insert(0, the_dome_ip)
        self.dome_ip.grid(row=2, column=1)
        self.dome_port = tk.Entry(self.body)
        the_dome_port = cur_conf.get("dome_port")
        the_dome_port = str(the_dome_port) if the_dome_port else ""
        self.dome_port.insert(0, the_dome_port)
        self.dome_port.grid(row=3, column=1)
        self.tel_ip = tk.Entry(self.body)
        the_tel_ip = cur_conf.get("tel_ip", "")
        self.tel_ip.insert(0, the_tel_ip)
        self.tel_ip.grid(row=4, column=1)
        self.tel_port = tk.Entry(self.body)
        the_tel_port = cur_conf.get("tel_port")
        the_tel_port = str(the_tel_port) if the_tel_port else ""
        self.tel_port.insert(0, the_tel_port)
        self.tel_port.grid(row=5, column=1)
        tk.Button(self.body, text="Annulla", command=self.cancel).grid(row=6, column=0, sticky=tk.W)
        tk.Button(self.body, text="Registra", command=self.done).grid(row=6, column=1, sticky=tk.E)
        self.body.pack()

    def done(self):
        "Salva configurazione ed esci"
        fname = os.path.join(HOMEDIR, CONFIG_FILE)
        try:
            rlat = float(self.lat.get())
            rlon = float(self.lon.get())
            dome_ip = self.dome_ip.get()
            dome_port = int(self.dome_port.get())
            tel_ip = self.tel_ip.get()
            tel_port = int(self.tel_port.get())
        except Exception as excp:
            msg_text = "\nErrore formato dati: \n\n   %s\n"%str(excp)
        else:
            config = {"lat": rlat, "lon": rlon, "dome_ip": dome_ip,
                      "dome_port": dome_port, "tel_ip": tel_ip,
                      "tel_port": tel_port, "filename": fname}
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
        self.body.destroy()
        msg = WarningMsg(self, "Operazione annullata")
        msg.pack()

def main():
    "Lancia GUI per configurazione"
    root = tk.Tk()
    root.title("Osservatorio Polifunzionale del Chianti")
    if "-h" in sys.argv:
        msg = __doc__ % (__version__, __author__, __date__)
        wdg1 = WarningMsg(root, msg)
    elif '-c' in sys.argv:
        wdg1 = MakeConfig(root)
    else:
        str_conf = show_config()
        wdg1 = WarningMsg(root, str_conf)
    wdg1.pack()
    root.mainloop()


if __name__ == "__main__":
    main()
