#!/usr/bin/python3
"""
Simulatore telescopio

Uso:
      python3 telsimulator.py [-v]

dove:
      -v:  modo verboso: scrive su stdout i comandi e le risposte

"""

import sys
import socket
from threading import Thread
import random
import time
import math
import pprint

import astro

__version__ = "1.0"
__date__ = "Ottobre 2020"
__author__ = "Luca Fini"

LINEAR = 0
ROTATOR = 1

class GLOB:          # pylint: disable=R0903
    verbose = False

MY_PID = None

HELP = """
Comandi:
    h         - Aiuto
    e/w/n     - Set posizione braccio
    s dec ra  - Set posizione telescopio
    t         - Mostra stato telescopio
    v         - Abilita/disabilita modo verboso

    q         - Termina
"""

def _convert(value, maxval):
    "Converte valore in xxx:mm:ss"
    sgn = "+" if value >= 0. else "-"
    value = abs(value)
    if value > maxval:
        raise ValueError
    if value == maxval:
        value = 0.0
    ddd = int(value)
    sss = (value-ddd)*3600
    mmm = sss//60
    sss = sss%60
    return (sgn, ddd, mmm, sss)

def _inrange(val, limit):
    "test val in [0, limit)"
    return 0 <= val < limit

def dms_star_encode(value, with_sign=True, precision="S"):
    "Converte valore in [s]DD*MM'SS#"
    select = precision[0].upper()
    sign, degs, mins, secs = _convert(value, 360)
    if select == "S":
        ret = "%s%02d*%02d'%02d#"%(sign, degs, mins, secs)
    elif select == "M":
        ret = "%s%02d*%02d#"%(sign, degs, mins)
    else:
        sign, degs, mins, secs = _convert(value, 360)
        isec = int(secs)
        frac = int((secs-isec)*1000)
        ret = "%s%02d*%02d:%02d.%03d#"%(sign, degs, mins, isec, frac)
    if with_sign:
        return ret
    if ret[0] == "+":
        return ret[1:]
    raise ValueError

def hms_colon_encode(value, precision="S"):
    "Converte valore in formato HH:MM:SS#"
    while value < 0.0:
        value += 24.
    hrs, mins, secs = _convert(value, 24)[1:]
    if precision == "S":
        return "%02d:%02d:%02d#"%(hrs, mins, secs)
    isec = int(secs)
    frac = int((secs-isec)*1000)
    return "%02d:%02d:%02d.%03d#"%(hrs, mins, isec, frac)


def dddmm_star_encode(value, with_sign=True, precision="S"):
    "Converte valore in formato DDD*MM'SS#"
    sel = precision[0].upper()
    if sel == "S":
        ret = "%s%03d*%02d'%02d#"%_convert(value, 360)
    else:
        ret = "%s%03d*%02d#"%_convert(value, 360)[:-1]
    if with_sign:
        return ret
    if ret[0] == "+":
        return ret[1:]
    raise ValueError

class Movement(Thread):          # pylint: disable=R0902
    "Simulatore di asse mobile"
    def __init__(self, limits, maxspeed=1.0, timestep=1.0, insync=False):
        Thread.__init__(self, daemon=True)
        self.limits = limits
        self.maxspeed = maxspeed
        self.timestep = timestep
        self.setspeed(maxspeed)
        self.insync = insync
        if insync:
            self.position = 0
        else:
            self.position = limits[0]+(limits[1]-limits[0])*random.random()
        self.movement = 0
        self.syncing = 0
        self.going = 0
        self.target = 0
        self.error = ""

    def set(self, pos):
        "Imposta posizione"
        if self.movement == 0 and self.limits[0] <= pos <= self.limits[1]:
            self.position = pos

    def setspeed(self, speed):
        "Imposta velocità moto"
        speed = min(self.maxspeed, speed)
        self.speed = max(0., speed)
        self.xstep = self.timestep*self.speed
        self.pos_err = 1.5*self.xstep

    def move(self, direction):
        "Comando movimento"
        if self.movement != 0 and self.movement != direction:
            self.stop()
        self.movement = direction

    def stop(self):
        "Comando stop"
        self.movement = 0
        self.syncing = 0
        self.going = 0

    def run(self):
        "Metodo da implementare nei discendenti"
        raise NotImplementedError

    def goto(self, target):
        "Metodo da implementare nei discendenti"
        raise NotImplementedError

class Linear(Movement):
    "Simulatore di asse lineare"
    def goto(self, target):
        if not self.insync:
            self.error = "Posizione ignota"
            return False
        if target > self.limits[1] or target < self.limits[0]:
            self.error = "posizione illegale (%d)"%target
            return False
        delta = target-self.position
        sign = int(math.copysign(1.0, delta))
        self.target = target
        self.move(sign)
        self.going = 1
        self.error = ""
        return True

    def run(self):
        "Lancia simulatore lineare"
        while True:
            time.sleep(self.timestep)
            if self.movement < 0:
                self.position -= self.xstep
                if self.position <= self.limits[0]:
                    self.position = self.limits[0]
                    self.movement = 0
            elif self.movement > 0:
                self.position += self.xstep
                if self.position >= self.limits[1]:
                    self.position = self.limits[1]
                    self.movement = 0
            if self.going:
                delta = abs(self.target-self.position)
                if delta < self.pos_err:
                    self.going = 0
                    self.movement = 0

class Rotator(Movement):
    "Simulatore di asse di rotazione"
    def goto(self, target):
        if not self.insync:
            self.error = "Posizione ignota"
            return False
        if target == self.limits[1]:
            target = self.limits[0]
        elif target > self.limits[1] or target < self.limits[0]:
            self.error = "Posizione illegale (%d)"%target
            return False
        sign = astro.find_shortest(self.position, target)[1]
        self.move(sign)
        self.going = 1
        self.target = target
        return True

    def run(self):
        "lancia rotatore"
        while True:
            time.sleep(self.timestep)
            if self.movement < 0:
                self.position -= self.xstep
                if self.position < self.limits[0]:
                    self.position += self.limits[1]-self.limits[0]
            elif self.movement > 0:
                self.position += self.xstep
                if self.position >= self.limits[1]:
                    self.position += self.limits[0]-self.limits[1]
            if (self.position-self.limits[0] < self.pos_err) \
               or (self.limits[1]-self.position < self.pos_err):
                self.insync = 1
            if self.syncing:
                if self.insync:
                    self.movement = 0
                    self.syncing = 0
            elif self.going:
                delta = astro.find_shortest(self.position, self.target)[0]
                if delta < self.pos_err:
                    self.going = 0
                    self.movement = 0

class TelescopeRA(Rotator):
    "Simulatore asse ascensione retta del telescopio"
    MAXSPEED = 0.0666666666667           # Ore/sec
    TIMESTEP = 0.2
    def __init__(self):
        Rotator.__init__(self, (0., 24.), self.MAXSPEED, self.TIMESTEP, True)

class TelescopeDE(Linear):
    "Simulatore asse declinazione del telescopio"
    MAXSPEED = 1.0              # Gradi/sec
    TIMESTEP = 0.2
    def __init__(self):
        Linear.__init__(self, (-40., 90.), self.MAXSPEED, self.TIMESTEP, True)

class Focuser(Linear):
    "Simulatore di Fuocheggiatore"
    MAXSPEED = 1.0    # cm al secondo
    TIMESTEP = 0.2
    def __init__(self):
        Linear.__init__(self, (-5, 5.), self.MAXSPEED, self.TIMESTEP, True)

class CameraRotator(Rotator):
    "Simulatore di rotatore"
    MAXSPEED = 3.0    # gradi al secondo
    TIMESTEP = 0.2
    def __init__(self):
        Rotator.__init__(self, (-180, 180.), self.MAXSPEED, self.TIMESTEP, True)

class Target:                  # pylint: disable=R0903
    "Definizione del target"
    def __init__(self, ras=0.0, dec=0.0):
        self.ras = ras
        self.dec = dec

class Telescope(Thread):
    "Simulatore movimenti telescopio"
    def __init__(self):
        Thread.__init__(self, daemon=True)
        self.ra_axis = TelescopeRA()
        self.de_axis = TelescopeDE()
        self.target = Target()
        self.brace = "N"

    def run(self):
        "Metodo da implementare nei discendenti"
        raise NotImplementedError

    def set_position(self, dec, ras):
        "Imposta posizione"
        self.de_axis.set(dec)
        self.ra_axis.set(ras)

    def set_brace(self, bpos):
        "Imposta posizione braccio"
        if bpos in ("N", "W", "E"):
            self.brace = bpos

    def get_status(self):
        "Riporta stato telescopio"
        return {"tel_de": self.de_axis.position,
                "tel_ra": self.ra_axis.position,
                "brace": self.brace,
                "target_de": self.target.dec,
                "target_ra": self.target.ras}

class LX200(Telescope):         # pylint: disable=R0904
    "LX200 protocol telescope"
    def __init__(self):
        Telescope.__init__(self)
        self.utc_offset = 0
        self.latitude = 0
        self.longitude = 0

        self.rotator = CameraRotator()
        self.focuser1 = Focuser()
        self.focuser2 = Focuser()

    def get_current_deh(self):
        "Leggi declinazione del telescopio codificata LX200 (alta precisione)"
        return dms_star_encode(self.de_axis.position, precision="h")

    def get_current_de(self):
        "Leggi declinazione del telescopio codificata LX200"
        return dms_star_encode(self.de_axis.position)

    def _get_altaz(self):
        "riporta coordinate az, alt (rad) del telescopio"
        de_rad = self.de_axis.position*astro.DEG_TO_RAD
        ltime = tuple(time.localtime()[:6])
        ra_rad = self.ra_axis.position*astro.HOUR_TO_RAD
        if self.longitude > 180.:
            lon_rad = (180.-self.longitude)*astro.DEG_TO_RAD
        else:
            lon_rad = self.longitude*astro.DEG_TO_RAD
        tsid_rad = astro.loc_st(*ltime, self.utc_offset, lon_rad)*astro.HOUR_TO_RAD
        ha_rad = tsid_rad-ra_rad
        return astro.az_coords(ha_rad, de_rad)

    def get_current_rah(self):
        "Leggi ascensione retta del telescopio codificata LX200 (alta precisione)"
        return hms_colon_encode(self.ra_axis.position, precision="h")

    def get_current_ra(self):
        "Leggi ascensione retta del telescopio codificata LX200"
        return hms_colon_encode(self.ra_axis.position)

    def get_current_az(self):
        "Leggi azimuth telescopio"
        azalt = self._get_altaz()
        az_deg = astro.RAD_TO_DEG*azalt[0]
        return dddmm_star_encode(az_deg, with_sign=False)

    def get_current_alt(self):
        "Leggi altezza telescopio"
        azalt = self._get_altaz()
        alt_deg = astro.RAD_TO_DEG*azalt[1]
        return dms_star_encode(alt_deg, with_sign=True)

    def get_date(self):
        "Leggi data locale"
        ltime = time.localtime()
        return "%d:%02d:%02d"%(ltime[2], ltime[1], ltime[0])

    def get_ltime(self):
        "Leggi local time"
        ltime = time.localtime()
        return "%02d:%02d:%02d"%tuple(ltime[3:6])

    def get_lon(self):
        "Leggi longitudine"
        return dddmm_star_encode(self.longitude, with_sign=True, precision="M")

    def get_lat(self):
        "Leggi latitudine"
        return dms_star_encode(self.latitude, with_sign=True, precision="M")

    def get_target_de(self):
        "Leggi declinazione del target codificata LX200"
        return dms_star_encode(self.target.dec)

    def get_target_deh(self):
        "Leggi declinazione del target codificata LX200 alta prec."
        return dms_star_encode(self.target.dec, precision="h")

    def get_target_ra(self):
        "Leggi ascensione retta del target codificata LX200"
        return hms_colon_encode(self.target.ras)

    def get_target_rah(self):
        "Leggi ascensione retta del target codificata LX200 alta prec."
        return hms_colon_encode(self.target.ras, precision="h")

    def get_tsid(self):
        "Riporta tempo siderale"
        hou, mnt, sec = _convert(astro.loc_st_now(), 24)[1:]
        return "%02d:%02d:%02d#"%(hou, mnt, sec)

    def get_pier_side(self):
        "Riporta lato braccio (N, E, W)"
        return self.brace+"#"

    def get_uoff(self):
        "Leggi UTC offset"
        sgn = "+" if self.utc_offset >= 0 else "-"
        return sgn+"%04.1f#"%abs(self.utc_offset)

    def move_dir(self, _unused):
        "Muovi in direzione data"
        return ""

    def stop_dir(self, _unused):
        "Interrompi movimento in direzione data"
        return ""

    def pulse_guide(self, _dirc, _time):
        "Comando pulse-guide TBD"
        return ""

    def execute(self, command):           # pylint: disable=R0912
        "Esecuzione comando telescopio"
        try:
            if command[:3] == b":Sr":    # Comando SrHH:MM:SS - set target RA
                hhh, mmm, sss = (int(command[3:5]), int(command[6:8]), int(command[9:11]))
                if _inrange(hhh, 24) and _inrange(mmm, 60) and _inrange(sss, 60):
                    self.target.ras = hhh+mmm/60.+sss/3600.
                    ret = "1"
                else:
                    ret = "0"
            elif command[:3] == b":Sd": # Comando SdsDD*MM:SS - Set target DE
                sgn, ddd, mmm, sss = (command[3], int(command[4:6]),
                                      int(command[7:9]), int(command[10:12]))
                if _inrange(ddd, 90) and _inrange(mmm, 60) and _inrange(sss, 60):
                    mult = 1 if sgn == ord(b"+") else -1
                    self.target.dec = mult*(ddd+mmm/60.+sss/3600.)
                    ret = "1"
                else:
                    ret = "0"
            elif command[:3] == b":St": # Comando StsDD*MM - Set Latitude
                sgn, ddd, mmm = (command[3], int(command[4:6]), int(command[7:9]))
                if _inrange(ddd, 90) and _inrange(mmm, 60):
                    mult = 1 if sgn == ord(b"+") else -1
                    self.latitude = mult*(ddd+mmm/60.)
                    ret = "1"
                else:
                    ret = "0"
            elif command[:3] == b":Sg": # Comando SgDDD*MM - Set Longitude
                print(command[3:7], command[8:10])
                ddd, mmm = (int(command[3:7]), int(command[8:10]))
                if _inrange(ddd, 360) and _inrange(mmm, 60):
                    self.longitude = ddd+mmm/60.
                    ret = "1"
                else:
                    ret = "0"
            elif command[:3] == b":SG": # Comando SGsHHH.H - Set UTC offset
                try:
                    val = float(command[3:8])
                except:
                    ret = "0"
                    if GLOB.verbose:
                        print("Errore conversione UTC offset:", command[3:8])
                else:
                    if -12 <= val <= 12:
                        self.utc_offset = val
                        ret = "1"
                    else:
                        if GLOB.verbose:
                            print("Errore conversione UTC offset:", command[3:8])
                        ret = "0"
            elif command[:2] == b":M":    # Comandi di movimento
                if command[2] == b"S":    # Comando MS - Slew to target
                    self.ra_axis.goto(self.target.ras)
                    self.de_axis.goto(self.target.dec)
                    ret = ""
                elif command[2] in b"snew":   # Comando Msd - Muovi in direzione data
                    ret = self.move_dir(command[2])
            elif command[:2] == b":Q":    # Comandi stop
                if len(command) > 2:
                    drc = command[2]
                else:
                    drc = None
                ret = self.stop_dir(drc)
            elif command[:3] == b":Mg":   # Comando Mgdnnn - Pulse-guide
                ret = self.pulse_guide(command[3], int(command[4:]))
            elif command[:3] == b":GA":   # Comando GA - Get telescope altitude
                ret = self.get_current_alt()
            elif command[:3] == b":GC":   # Comando GA - Get telescope date
                ret = self.get_date()
            elif command[:4] == b":GDA":   # Comando GDA - Get scope declination (alta prec.)
                ret = self.get_current_deh()
            elif command[:3] == b":GD":   # Comando GD - Get scope declination
                ret = self.get_current_de()
            elif command[:4] == b":Gda":   # Comando Gd - Get target declination
                ret = self.get_target_deh()
            elif command[:3] == b":Gd":   # Comando Gd - Get target declination
                ret = self.get_target_de()
            elif command[:3] == b":GG":   # Comando GG - Get UTC offset
                ret = self.get_uoff()
            elif command[:3] == b":Gg":   # Comando Gg - Get longitude
                ret = self.get_lon()
            elif command[:3] == b":GL":   # Comando GL - Get local time
                ret = self.get_ltime()
            elif command[:3] == b":Gm":   # Comando Gm - Get pier side
                ret = self.get_pier_side()
            elif command[:4] == b":GRA":   # Comando GR - Get scope right ascension
                ret = self.get_current_rah()
            elif command[:3] == b":GR":   # Comando GR - Get scope right ascension
                ret = self.get_current_ra()
            elif command[:4] == b":Gra":   # Comando Gr - Get target right ascension
                ret = self.get_target_rah()
            elif command[:3] == b":Gr":   # Comando Gr - Get target right ascension
                ret = self.get_target_ra()
            elif command[:3] == b":GS":   # Comando GS - Get sidereal time
                ret = self.get_tsid()
            elif command[:3] == b":Gt":   # Comando Gt - Get latitude
                ret = self.get_lat()
            elif command[:3] == b":GU":   # Comando GU - Get global status
                ret = "Hp#"
            elif command[:4] == b":GVP":   # Comando GVP - Get product name
                ret = "Simulatore-"+__version__+"#"
            elif command[:4] == b":GW":   # Comando GW - Get Mount status
                ret = "GT2#"
            elif command[:3] == b":GZ":   # Comando GZ - Get telescope azimuth
                ret = self.get_current_az()
            elif command[:3] == b":r+":   # Comando r+ - Abilita rotatore
                ret = "0"
            elif command[:3] == b":r-":   # Comando r- - Disabilita rotatore
                ret = "0"
            elif command[:3] == b":rP":   # Comando rP - Muovi rotatore ad angolo parallattico
                ret = "0"
            elif command[:3] == b":rR":   # Comando rR - Inverte direzione rotatore
                ret = "0"
            elif command[:3] == b":rF":   # Comando rF - Reset rotatore a pos. home
                ret = "0"
            elif command[:3] == b":rC":   # Comando rC - Muovi rotatore a pos. home
                ret = "0"
            elif command[:3] == b":r>":   # Comando r> - Muove rotatore in senso orario
                ret = "0"
            elif command[:3] == b":r<":   # Comando r< - Muove rotatore in senso antiorario
                ret = "0"
            elif command[:3] == b":r1":   # Comando r1 - Imposta incremento rotatore
                ret = "0"
            elif command[:3] == b":r2":   # Comando r2 - Imposta incremento rotatore
                ret = "0"
            elif command[:3] == b":r3":   # Comando r3 - Imposta incremento rotatore
                ret = "0"
            elif command[:3] == b":rS":   # Comando rS - Imposta posizione rotatore
                ret = "0"
            elif command[:3] == b":rG":   # Comando rG - Leggi posizione rotatore
                ret = "0"
            elif command[:3] == b":r+":   # Comando r+ - Abilita rotatore
                ret = "0"
            else:
                ret = "0"
        except Exception as excp:
            if GLOB.verbose:
                print("Tel Exception:", str(excp))
            ret = "0"
        return ret.encode("ascii")

    def run(self):
        "Lancia simulatore telescopio"
        self.ra_axis.start()
        self.de_axis.start()
        self.rotator.start()
        self.focuser1.start()
        self.focuser2.start()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 9753))
        print("Simulatore telescopio attivo su port 9753", flush=True)
        sock.listen(5)

        while True:
            (client, address) = sock.accept()
            command = b""
            while True:
                achar = client.recv(1)
                if not achar:
                    break
                if achar == b"#":
                    if GLOB.verbose:
                        print("Comando telescopio da %s %s#"%(address[0],
                                                              command.decode("ascii")), end=" ")
                    ret = self.execute(command)
                    client.sendall(ret)
                    client.shutdown(socket.SHUT_RDWR)
                    client.close()
                    if GLOB.verbose:
                        print("-", ret.decode("ascii"), flush=True)
                    command = b""
                    break
                command += achar

def help_cmd():
    "Aiuto per comandi"
    print(HELP)

def main():
    "Programma principale"

    if "-h" in sys.argv:
        print(__doc__)
        sys.exit()
    if "-v" in sys.argv:
        GLOB.verbose = True
    telescope = LX200()
    telescope.start()
    time.sleep(2)

    while True:
        cmd = input("Comando? [h per help] ").strip()
        if not cmd:
            continue
        cmds = cmd.split()
        if cmds[0][0].lower() == "s":
            telescope.set_position(float(cmds[1]), float(cmds[2]))
        elif cmds[0][0].lower() in ("e", "n", "w"):
            telescope.set_brace(cmds[0][0].upper())
        elif cmds[0][0].lower() == "v":
            GLOB.verbose = not GLOB.verbose
        elif cmds[0][0].lower() == "t":
            pprint.pprint(telescope.get_status(), indent=4)
        elif cmds[0][0].lower() == "q":
            break
        else:
            help_cmd()

if __name__ == "__main__":
    main()
