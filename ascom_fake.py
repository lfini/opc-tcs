"""
Simulatore di driver ASCOM per linux
"""
from threading import Thread
import time

import astro

RESOLUTION = 0.4
TIMESTEP = 0.02
PRINT_COUNT = int(1./TIMESTEP)
STEP = RESOLUTION/20.

class GLOB:
    verbose = False

def set_verbose():
    GLOB.verbose = True

class Dispatch(Thread):
    "Emulatore di ASCOM Dispatch"
    def __init__(self, selector):
        super().__init__()
        self.selector = selector
        self.Connected = True
        self.Azimuth = 0
        self._azimuth = 0
        self.Slewing = False
        self.targetaz = 0
        self.stop = False
        self._counter = 0
        self.start()

    def run(self):
        print("Simulatore cupola attivo")
        while True:
            if self.stop:
                break
            delta, sign = astro.find_shortest(self._azimuth, self.targetaz)
            if delta > RESOLUTION:
                if sign > 0:
                    self._azimuth += STEP
                else:
                    self._azimuth -= STEP
                self.Slewing = True
                self._azimuth %= 360.
                self.Azimuth = int(self._azimuth)
            else:
                self.Slewing = False

            if GLOB.verbose and self._counter == 0:
                status = "SLEWING" if self.Slewing else "IDLE    "
                print("AZ: ", self.Azimuth, "-", status)
            self._counter = (self._counter+1)%PRINT_COUNT

            time.sleep(TIMESTEP)
        print("Simulatore cupola terminato")

    def AbortSlew(self):
        "Interrompe movimento"
        print("SC: AbortSlew")
        self.targetaz = self.Azimuth
        self.Slewing = False

    def Dispose(self):
        "Termina loop"
        print("SC: Dispose")
        self.stop = True

    def SlewToAzimuth(self, azh):
        "Movimento cupola"
        print("SC: SlewToAzimuth(%.2f) - current: %.3f"%(azh, self._azimuth))
        self.targetaz = azh%360.

    def FindHome(self):
        "Vai ad home"
        print("SC: FindHome()")
        self.Azimuth = 0.
        self._azimuth = 0.
        self.Slewing = False

    def Park(self):
        "Vai a posizione park"
        print("SC: Park()")
        self.Azimuth = 0.
        self._azimuth = 0.
        self.Slewing = False
