"""
telsampels.py - Campiona posizioni del telescopio a intervalli regolari

Uso:
    python telsample.py [-d] [nnn]

Dove:
    -d   Modo debug: si connette al simulatore con IP: 127.0.0.1, Port: 9752
    nnn  Intervallo di campionamento in millisecondi (default: 1000)

Nota
    Si interrompe con CTRL-C
"""

import sys
import os
import time
import signal
from telecomm import TeleCommunicator
import configure as conf
import astro

def ctrlc(*_unused):
    "Received CTRL-C"
    print("Interrupted...")
    sys.exit()

def main():
    "funzione main"
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit()
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
    try:
        delay = int(sys.argv[-1])
    except:
        delay = 1000

    delay = float(delay)/1000
    signal.signal(signal.SIGINT, ctrlc)
    telcom = TeleCommunicator(config["tel_ip"], config["tel_port"])

    fname = time.strftime("%Y%m%d_%H%M%S")+".dat"
    with open(fname, "w") as fpt:
        print()
        print("Dati in:", os.path.abspath(fname))
        print("Termina con CTRL-C")
        tt0 = time.time()
        while 1:
            now = time.time()
            art = telcom.get_current_ra()
            dec = telcom.get_current_de()
            nnn = "%.2f" % (now-tt0)
            print(" ", nnn, dec, art, file=fpt)
            print(" ", nnn, dec, art)
            after = time.time()
            ddl = delay-after+now
            if ddl > 0.0:
                time.sleep(ddl)

if __name__ == "__main__":
    main()
