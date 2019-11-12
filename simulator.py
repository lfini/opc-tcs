#!/usr/bin/python3
"""
Simulatore osservatorio OPC.

Simula movimenti cupola e telescopio

Uso:
      python3 domesimulator.py [-v] [-s] [-t] [-c]

dove:
      -v:  modo verboso: scrive su stdout i comandi e le risposte
      -s:  Start con cupola in posizione "insync"
      -c:  Start solo simulatore cupola
      -t:  Start solo simulatore telescopio

"""

import sys
import socket
import json
from threading import Thread
import random
import time
import math
import pprint

from domecomm import DomeCommands, StatiMovimento, DomeErrors, StatiLuce, StatiVano, StatiSync
import astro

__version__ = "1.3"
__date__ = "Marzo 2019"
__author__ = "Luca Fini"

LINEAR = 0
ROTATOR = 1

VERBOSE = False
CUPOLA = None

MY_PID = None

HELP = """
Comandi:
    h         - Aiuto
    0         - Azzera posizione cupola
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

def dms_star_encode(value, with_sign=True, seconds=True):
    "Converte valore in [s]DD*MM'SS#"
    if seconds:
        ret = "%s%02d*%02d:%02d#"%_convert(value, 360)
    else:
        ret = "%s%02d*%02d#"%_convert(value, 360)[:-1]
    if with_sign:
        return ret
    else:
        if ret[0] == "+":
            return ret[1:]
        else:
            raise ValueError

def hms_colon_encode(value):
    "Converte valore in formato HH:MM:SS#"
    while value < 0.0:
        value += 24.
    return "%02d:%02d:%02d#"%_convert(value, 24)[1:]

def dddmm_star_encode(value, with_sign=True, seconds=True):
    "Converte valore in formato DDD*MM'SS#"
    if seconds:
        ret = "%s%03d*%02d'%02d#"%_convert(value, 360)
    else:
        ret = "%s%03d*%02d#"%_convert(value, 360)[:-1]
    if with_sign:
        return ret
    else:
        if ret[0] == "+":
            return ret[1:]
        else:
            raise ValueError

class Movement(Thread):
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
        if self.movement == 0 and pos < self.limits[1] and pos >= self.limits[0]:
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
        return DomeErrors.OK

    def stop(self):
        "Comando stop"
        self.movement = 0
        self.syncing = 0
        self.going = 0
        return DomeErrors.OK

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

class Target:
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

class LX200(Telescope):
    "LX200 protocol telescope"
    def __init__(self):
        Telescope.__init__(self)
        self.utc_offset = 0
        self.latitude = 0
        self.longitude = 0

        self.rotator = CameraRotator()
        self.focuser1 = Focuser()
        self.focuser2 = Focuser()

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
        return dddmm_star_encode(self.longitude, with_sign=True, seconds=False)

    def get_lat(self):
        "Leggi latitudine"
        return dms_star_encode(self.latitude, with_sign=True, seconds=False)

    def get_target_de(self):
        "Leggi declinazione del target codificata LX200"
        return dms_star_encode(self.target.dec)

    def get_target_ra(self):
        "Leggi ascensione retta del target codificata LX200"
        return hms_colon_encode(self.target.ras)

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

    def execute(self, command):
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
                ddd, mmm = (int(command[3:6]), int(command[7:9]))
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
                    if VERBOSE:
                        print("Errore conversione UTC offset:", command[3:8])
                else:
                    if -12 <= val <= 12:
                        self.utc_offset = val
                        ret = "1"
                    else:
                        if VERBOSE:
                            print("Errore conversione UTC offset:", command[3:8])
                        ret = "0"
            elif command[:3] == b":MS":   # Comando MS - Slew to target
                self.ra_axis.goto(self.target.ras)
                self.de_axis.goto(self.target.dec)
                ret = "0"
            elif command[:3] == b":GA":   # Comando GA - Get telescope altitude
                ret = self.get_current_alt()
            elif command[:3] == b":GC":   # Comando GA - Get telescope date
                ret = self.get_date()
            elif command[:3] == b":GD":   # Comando GD - Get scope declination
                ret = self.get_current_de()
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
            elif command[:3] == b":GR":   # Comando GR - Get scope right ascension
                ret = self.get_current_ra()
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
            if VERBOSE:
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
                    ret = self.execute(command)
                    client.sendall(ret)
                    client.shutdown(socket.SHUT_RDWR)
                    client.close()
                    if VERBOSE:
                        print("Comando telescopio da %s %s#"%(address[0], command.decode("ascii")),
                              "-", ret.decode("ascii"), flush=True)
                    command = b""
                    break
                else:
                    command += achar

class RotazioneCupola(Rotator):
    "Simulatore rotazione cupola"
    SPEED = 2.0      # Gradi al secondo
    TIMESTEP = 0.1   # Tempo aggiornamento (sec)
    def __init__(self, insync=False):
        Rotator.__init__(self, (0.0, 360.0), self.SPEED, self.TIMESTEP, insync)

    def internal_position(self):
        "leggi posizione interna"
        return self.position

    def azimuth(self):
        "leggi azimuth"
        if self.insync:
            return int(self.position+0.5)
        return -1

    def stato_moto(self):
        "Leggi stato movimento dettagliato"
        if self.movement < 0:
            return StatiMovimento.LEFT
        elif self.movement > 0:
            return StatiMovimento.RIGHT
        return StatiMovimento.STOP

    def sync(self):
        "Attiva sincronizzazione posizione"
        if self.movement != 0:
            self.stop()
        self.syncing = 1
        self.movement = -1
        return DomeErrors.OK

    def setz(self, target):
        "Forza posizione interna"
        if target >= 360 or target < 0:
            return DomeErrors.ERR+" azimuth illegale (%d)"%target
        if self.movement != 0:
            self.stop()
        self.position = target
        self.insync = 1
        return DomeErrors.OK

class Vano(Linear):
    "Siimulatore vano osservazione"
    SPEED = 0.1      # m/s
    TIMESTEP = 0.2   # Tempo aggiornamento (sec)
    def __init__(self):
        Linear.__init__(self, (0.0, 1.0), self.SPEED, self.TIMESTEP, True)

    def open(self):
        "Copmando apri vano osservativo"
        ret = self.goto(self.limits[1])
        if ret:
            return DomeErrors.OK
        return DomeErrors.ERR+" "+self.error

    def close(self):
        "Copmando chiudi vano osservativo"
        ret = self.goto(self.limits[0])
        if ret:
            return DomeErrors.OK
        return DomeErrors.ERR+" "+self.error

    def stato(self):
        "Leggi stato vano ossewrvativo"
        if self.position > .97:
            return StatiVano.OPEN
        elif self.position < 0.03:
            return StatiVano.CLOSED
        elif self.movement < 0:
            return StatiVano.CLOSING
        elif self.movement > 0:
            return StatiVano.OPENING
        return StatiVano.ERROR

class Cupola(Thread):
    "Simulatore cupola completa"
    def __init__(self, insync=False):
        Thread.__init__(self, daemon=True)
        self._stato = {"POS": -1,
                       "LP": StatiLuce.ON,
                       "LN": StatiLuce.OFF,
                       "VANO": StatiVano.CLOSED,
                       "SYNC": StatiSync.NOTSYNC,
                       "MOV": StatiMovimento.STOP}

        self.rotazione = RotazioneCupola(insync)
        self.vano = Vano()
        if self.rotazione.insync:
            self._stato["SYNC"] = StatiSync.INSYNC

    def stato(self):
        "Leggi stato complessivo cupola"
        self._stato["VANO"] = self.vano.stato()
        self._stato["MOV"] = self.rotazione.stato_moto()

        self._stato["POS"] = self.rotazione.azimuth()
        if self.rotazione.insync:
            self._stato["SYNC"] = StatiSync.INSYNC
        elif self.rotazione.syncing:
            self._stato["SYNC"] = StatiSync.SYNCING
        else:
            self._stato["SYNC"] = StatiSync.NOTSYNC

        return DomeErrors.OK+json.dumps(self._stato)

    def rotator_position(self):
        "Riporta posizione 'fisica' del rotazione"
        return self.rotazione.internal_position()

    def sync(self):
        "Comando sincronizza posizione cupola"
        return self.rotazione.sync()

    def lpon(self):
        "Comando accendi luce principale"
        if self._stato["LP"]:
            return DomeErrors.WNG
        self._stato["LP"] = 1
        return DomeErrors.OK

    def lpoff(self):
        "Comando spengi luce principale"
        if self._stato["LP"]:
            self._stato["LP"] = 0
            return DomeErrors.OK
        return DomeErrors.WNG

    def lnon(self):
        "Comando accendi luce notturna"
        if self._stato["LN"]:
            return DomeErrors.WNG
        self._stato["LN"] = 1
        return DomeErrors.OK

    def lnoff(self):
        "Comando spengi luce notturna"
        if self._stato["LN"]:
            self._stato["LN"] = 0
            return DomeErrors.OK
        return DomeErrors.WNG

    def left(self):
        "Comando muovi antiorario"
        return self.rotazione.move(-1)

    def right(self):
        "Comando muovi orario"
        return self.rotazione.move(1)

    def stop(self):
        "Comando stop cupola"
        if self._stato["MOV"] == StatiMovimento.STOP:
            return DomeErrors.WNG
        self.rotazione.stop()
        return DomeErrors.OK

    def open(self):
        "Comando apri vano"
        return self.vano.open()

    def close(self):
        "Comando chiudi vano"
        return self.vano.close()

    def goto(self, pos):
        "Vai ad azimunt dato"
        ret = self.rotazione.goto(pos)
        if ret:
            return DomeErrors.OK
        return DomeErrors.ERR+" "+self.rotazione.error

    def setz(self, pos):
        "Forza posizione interna cupola"
        ret = self.rotazione.setz(pos)
        if ret:
            return DomeErrors.OK
        return DomeErrors.ERR+" "+self.rotazione.error

    def execute(self, line):
        "Esecuzione comando cupola"
        command = line[:4]
        if command == DomeCommands.STAT:
            ret = self.stato()
        elif command == DomeCommands.LPON:
            ret = self.lpon()
        elif command == DomeCommands.LPOF:
            ret = self.lpoff()
        elif command == DomeCommands.LNON:
            ret = self.lnon()
        elif command == DomeCommands.LNOF:
            ret = self.lnoff()
        elif command == DomeCommands.LEFT:
            ret = self.left()
        elif command == DomeCommands.RGHT:
            ret = self.right()
        elif command == DomeCommands.SYNC:
            ret = self.sync()
        elif command == DomeCommands.GOTO:
            target = int(line[5:])
            ret = self.goto(target)
        elif command == DomeCommands.STOP:
            ret = self.stop()
        elif command == DomeCommands.OPEN:
            ret = self.open()
        elif command == DomeCommands.CLOS:
            ret = self.close()
        elif command == DomeCommands.SETZ:
            target = int(line[5:])
            ret = self.setz(target)
        else:
            ret = DomeErrors.ERR+" Comando non riconosciuto [%s]"%command
        return ret

    def run(self):
        "Lancio simulatore cupola"
        self.rotazione.start()
        self.vano.start()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 9752))
        sock.listen(5)
        print("Simulatore cupola attivo su port 9752")

        while True:
            (client, address) = sock.accept()
            data = bytes()
            while True:
                ret = client.recv(1024)
                if not ret:
                    break
                data += ret
            line = data.decode("ascii").strip()
            ret = self.execute(line)
            client.sendall((ret+"\n").encode("ascii"))
            client.shutdown(socket.SHUT_RDWR)
            client.close()
            if VERBOSE:
                print("Comando cupola da %s: %s"%(address[0], line), "-", ret, flush=True)

def help_cmd():
    "Aiuto per comandi"
    print(HELP)

def main():
    "Programma principale"
    global VERBOSE
    start_cupola = True
    start_telescopio = True

    if "-h" in sys.argv:
        print(__doc__)
        sys.exit()
    if "-v" in sys.argv:
        VERBOSE = True
    if "-t" in sys.argv:
        start_cupola = False
    if "-c" in sys.argv:
        start_telescopio = False
    if "-s" in sys.argv:
        insync = 1
    else:
        insync = 0
    if start_cupola:
        dome = Cupola(insync)
        dome.start()
    if start_telescopio:
        telescope = LX200()
        telescope.start()
    time.sleep(2)
    while True:
        cmd = input("Comando? [h per help] ").strip()
        if not cmd:
            continue
        cmds = cmd.split()
        if cmds[0][0].lower() == "0":
            dome.setz(0)
        elif cmds[0][0].lower() == "s":
            telescope.set_position(float(cmds[1]), float(cmds[2]))
        elif cmds[0][0].lower() in ("e", "n", "w"):
            telescope.set_brace(cmds[0][0].upper())
        elif cmds[0][0].lower() == "v":
            VERBOSE = not VERBOSE
        elif cmds[0][0].lower() == "t":
            pprint.pprint(telescope.get_status(), indent=4)
        elif cmds[0][0].lower() == "q":
            break
        else:
            help_cmd()

if __name__ == "__main__":
    main()
