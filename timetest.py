"""
Test di temporizzazione comunicazione con telescopio

Misura i tempi di risposta ai comandi più comuni (interrogazioni posizione)

Uso:
      python timetest.py [-d] [rip]

dove:
      -d  Collegamento al simulatore (IP: 127.0.0.1, Port: 9753)
      rip  Intervallo ripetizione interrogazioni (default: 1 sec)

NOTA: il test dura 5 minuti e può essere interrotto con CTRL-C
"""

import sys
import time
import configure as conf
from telecomm import TeleCommunicator

def timeme(func):
    tm0 = time.time()
    ret = func()
    tm1 = time.time()
    print(ret, "   -- delay: %.3f s"%(tm1-tm0))

if '-h' in sys.argv:
    print(__doc__)
    sys.exit()

if '-d' in sys.argv:
    config = {"tel_ip": "127.0.0.1",
              "tel_port": 9753,
              "debug": 1}
else:
    config = conf.get_config()
if not config:
    print("File di configurazione inesistente!")
    print("occorre definirlo con:")
    print()
    print("   python cupola.py -c")
    sys.exit()

try:
    rep = float(sys.argv[-1])
except ValueError:
    rep = 1.0

tlc = TeleCommunicator(config["tel_ip"], config["tel_port"], timeout=2.0)

time0 = time.time()
final_time = time0+300
while time0 < final_time:
    time.sleep(rep)
    print("Leggi azimuth", end=" ", flush=True); timeme(tlc.get_az)
    time.sleep(rep)
    print("Leggi declin.", end=" ", flush=True); timeme(tlc.get_current_de)
    time.sleep(rep)
    print("Leggi asc.retta.", end=" ", flush=True); timeme(tlc.get_current_ra)
    time.sleep(rep)
    print("Leggi t.sid.", end=" ", flush=True); timeme(tlc.get_tsid)
    time0 = time.time()
