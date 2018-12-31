"""
Funzioni di comunicazione per controllo telescopio OPC

Uso interattivo:

      python telcomm.py [-d] [-v]

Dove:
      -d  Collegamento al simulatore (IP: 127.0.0.1, Port: 9753)
      -v  Modo verboso (visualizza protocollo)
"""

import sys
import re
import socket
import time
import configure as conf

from astro import OPC, float2ums, loc_st_now

__version__ = "1.1"
__date__ = "Novembre 2018"
__author__ = "Luca Fini"

                                   # Comandi definiti
                                   # Comandi di preset
SET_DATE = ":SC%02d/%02d/%02d#"    # Set data
SET_DE = ":Sd%s%02d*%02d:%02d#"    # Set declinazione target (dd,mm,ss)
SET_LAT = ":St%s%02d*%02d#"        # Set latitudine del luogo (dd, mm)
SET_LON = ":Sg%03d*%02d#"          # Set longitudine del luogo (ddd, mm)
SET_LTIME = ":SL%02d:%02d:%02d#"   # Set ora locale: hh, mm, ss
SET_RA = ":Sr%02d:%02d:%02d#"      # Set ascensione retta dell'oggetto target (hh,mm,ss)
SET_TRATE = "ST%.4f#"              # Set freq. di tracking
SET_TSID = ":SS%02d:%02d:%02d#"    # Set tempo sidereo: hh, mm, ss
SET_UOFF = ":SG%s%04.1f#"          # Set UTC offset (UTC = LocalTime+Offset)

TRACK_ON = ":Te#"                  # Abilita tracking
TRACK_OFF = ":Td#"                 # Disabilita tracking

                                   # Comandi di movimento
MOVE_DIR = ":M%s#"                 # Muovi ad est/ovest/nord/sud
STOP_DIR = ":Q%s#"                 # Stop movimento ad est/ovest/nord/sud
STOP = ":Q#"                       # Stop

PULSE_M = "Mg%s%d#"                # Pulse move              < TBD

PARK = ":hP#"                      # Park telescope
SLEW = ":MS#"                      # Slew to target
STOP = ":Q#"                       # stop telescope
UNPARK = ":hR#"                    # Unpark telescope

                                   # Comandi informativi
GET_AZ = ":GZ#"            # Get telescope azimuth
GET_ALT = ":GA#"           # Get telescope altitude
GET_CUR_DE = ":GD#"        # Get current declination
GET_CUR_RA = ":GR#"        # Get current right ascension
GET_DATE = ":GC#"          # Get date
GET_HLIM = ":Gh"           # Get horizont limit
GET_OVER = ":Go"           # Get overhead limit
GET_IDENT = ":GVP#"        # Get telescope identification
GET_LTIME = ":GL#"         # Get local time from telescope
GET_LON = ":Gg#"           # Get telescope longitude
GET_LAT = ":Gt#"           # Get telescope latitude
GET_MSTAT = ":GW#"         # Get telescope mount status
GET_PSIDE = ":Gm#"         # Get pier side
GET_TSID = ":GS#"          # Get Sidereal time
GET_TRATE = ":GT#"         # Get tracking rate
GET_STAT = ":GU#"          # Get global status
                           # N: not slewing     H: at home position
                           # P: parked          p: not parked
                           # F: park failed     I: park in progress
                           # R: PEC recorded    G: Guiding
                           # S: GPS PPS synced
GET_TAR_DE = ":Gd#"        # Get target declination
GET_TAR_RA = ":Gr#"        # Get target right ascension
GET_UOFF = ":GG#"          # Get UTC offset time


DDMMSS_RE = re.compile("[+-]?(\\d{2,3})[*:](\\d{2})[':](\\d{2})")
DDMM_RE = re.compile("[+-]?(\\d{2,3})[*:](\\d{2})")

def ddmmss_decode(the_str, with_sign=False):
    "Decodifica stringa DD.MM.SS. Riporta float"
    if the_str is None:
        return None
    if with_sign:
        sgn = -1 if the_str[0] == "-" else 1
    else:
        sgn = 1
    flds = DDMMSS_RE.match(the_str)
    if not flds:
        return None
    ddd = int(flds.group(1))
    mmm = int(flds.group(2))
    sss = int(flds.group(3))
    return (ddd+mmm/60.+sss/3600.)*sgn

def ddmm_decode(the_str, with_sign=False):
    "Decodifica stringa DD.MM. Riporta float"
    if the_str is None:
        return None
    if with_sign:
        sgn = -1 if the_str[0] == "-" else 1
    else:
        sgn = 1
    flds = DDMM_RE.match(the_str)
    if not flds:
        return None
    ddd = int(flds.group(1))
    mmm = int(flds.group(2))
    return (ddd+mmm/60.)*sgn

def float_decode(the_str):
    "Decodifica stringa x.xxxx"
    try:
        val = float(the_str)
    except ValueError:
        val = float('nan')
    return val

class TeleCommunicator:
    "Gestione comunicazione con server telescopio (LX200)"
    def __init__(self, ipadr, port, timeout=0.5, verbose=False):
        self.connected = False
        self.ipadr = ipadr
        self.port = port
        self.timeout = timeout
        self.verbose = verbose

    def send_command(self, command, expected):
        "Invio comandi. expected == True: prevista risposta"
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.settimeout(self.timeout)
        try:
            skt.connect((self.ipadr, self.port))
        except IOError:
            return None
        cmd = command.encode("ascii")
        if self.verbose:
            print("SND:", cmd)
        try:
            skt.sendall(command.encode("ascii"))
        except socket.timeout:
            skt.close()
            return None
        ret = b""
        repl = None
        if expected:
            try:
                while True:
                    nchr = skt.recv(1)
                    if not nchr:
                        break
                    ret += nchr
                    if nchr == b"#":
                        break
            except (socket.timeout, IOError):
                pass
            finally:
                if self.verbose:
                    print("RCV:", ret)
                skt.close()
                repl = ret.decode("ascii")
                if repl and repl[-1] == "#":
                    repl = repl[:-1]
        return repl

    def set_ra(self, hours):
        "Set target right ascension. Returns True on success"
        if hours < 24. and hours >= 0.:
            cmd = SET_RA % float2ums(hours)
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_de(self, deg):
        "Set target declination; Returns True on success"
        if deg >= -90. and deg <= 90.:
            sgn = "+" if deg >= 0 else "-"
            deg = abs(deg)
            cmd = SET_DE%((sgn,)+float2ums(deg))
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_trate(self, rate):
        "Set tracking rate"
        return self.send_command(SET_TRATE%rate, False)

    def set_lat(self, deg):
        "Set local latitude in degrees"
        if deg >= 0:
            sgn = "+"
        else:
            sgn = "-"
            deg = -deg
        cmd = SET_LAT%((sgn,)+float2ums(deg)[:2])
        return self.send_command(cmd, 1)

    def set_lon(self, deg):
        "Set local longitude in degrees"
        cmd = SET_LON%(float2ums(deg)[:2])
        return self.send_command(cmd, 1)

    def set_date(self):
        "Set data da clock del PC"
        ttt = list(time.localtime())
        ttt[8] = 0                # elimina ora legale
        tt0 = time.mktime(tuple(ttt))
        ttt = time.localtime(tt0)
        cmd = SET_DATE%(ttt[1], ttt[2], ttt[0]-2000)
        return self.send_command(cmd, 1)

    def set_tsid(self):
        "set tempo sidereo da clock PC"
        tsidh = loc_st_now()
        return self.send_command(SET_TSID%float2ums(tsidh), False)

    def set_time(self):
        "Set tempo telescopio da clock del PC"
        tm0 = time.time()
        ltime = time.localtime(tm0)
        if ltime.tm_isdst:
            tm0 -= 3600
            ltime = time.localtime(tm0)
        gmto = time.timezone/3600.
        cmd1 = SET_LTIME%tuple(ltime[3:6])
        if gmto < 0.0:
            sgn = "-"
            gmto = -gmto
        else:
            sgn = "+"
        cmd2 = SET_UOFF%(sgn, gmto)
        ret1 = self.send_command(cmd1, 1)
        ret2 = self.send_command(cmd2, 1)
        try:
            ret = ret1+ret2
        except TypeError:
            ret = None
        return ret

    def move_dir(self, to_dir):
        "Muovi ad in direzione data (to_dir=e,w,n,s)"
        dir_c = to_dir[0].lower()
        if dir_c not in "ewns":
            return None
        return self.send_command(MOVE_DIR%dir_c, False)

    def set_rate(self, rate):
        "set rate: 0-9/GCMS"
        if rate in "GCMS0123456789":
            return self.send_command(SET_TRATE+rate[0], False)
        return None

    def stop_dir(self, to_dir=None):
        "Ferma movimento (se to_dir=e,w,n,s ferma il movimento relativo)"
        if to_dir is None:
            dir_c = ""
        else:
            dir_c = to_dir[0].lower()
            if dir_c not in "ewns":
                return None
        return self.send_command(STOP_DIR%dir_c, False)

    def pulse_guide(self, to_dir, dtime):
        "Movimento ad impulso in direzione data (to_dir=e,w,n,s, dtime=20-16399)"
        if dtime < 20 or dtime > 16399:
            return None
        dir_c = to_dir[0].lower()
        if dir_c not in "ewns":
            return None
        return self.send_command(PULSE_M%(dir_c, dtime), False)

    def get_alt(self):
        "Get telescope altitude (degrees)"
        ret = self.send_command(GET_ALT, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_az(self):
        "Get telescope azimuth (degrees)"
        ret = self.send_command(GET_AZ, True)
        return ddmmss_decode(ret)

    def get_current_de(self):
        "Get current telescope declination (degrees)"
        ret = self.send_command(GET_CUR_DE, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_current_ra(self):
        "Get current telescope right ascension (hours)"
        ret = self.send_command(GET_CUR_RA, True)
        return ddmmss_decode(ret)

    def get_date(self):
        "Get date"
        ret = self.send_command(GET_DATE, True)
        return ret

    def get_hlim(self):
        "Get horizon limit"
        ret = self.send_command(GET_HLIM, True)
        return ret

    def get_olim(self):
        "Get overhead limit"
        ret = self.send_command(GET_OVER, True)
        return ret

    def get_lon(self):
        "Get telescope longitude (degrees)"
        ret = self.send_command(GET_LON, True)
        return ddmm_decode(ret, with_sign=True)

    def get_lat(self):
        "Get telescope latitude (degrees)"
        ret = self.send_command(GET_LAT, True)
        return ddmm_decode(ret, with_sign=True)

    def get_ident(self):
        "Get telescope identification"
        return self.send_command(GET_IDENT, True)

    def get_ltime(self):
        "Get local time from telescope (hours)"
        ret = self.send_command(GET_LTIME, True)
        return ddmmss_decode(ret)

    def get_mstat(self):
        "Get telescope alignment status"
        return self.send_command(GET_MSTAT, True)

    def get_pside(self):
        "Get pier side"
        return self.send_command(GET_PSIDE, True)

    def get_status(self):
        "Get global status"
        return self.send_command(GET_STAT, True)

    def get_target_de(self):
        "Get target object declination"
        ret = self.send_command(GET_TAR_DE, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_target_ra(self):
        "Get target object right ascension"
        ret = self.send_command(GET_TAR_RA, True)
        return ddmmss_decode(ret)

    def get_trate(self):
        "Get tracking rate"
        ret = self.send_command(GET_TRATE, True)
        return float_decode(ret)

    def get_tsid(self):
        "Get sidereal time (hours)"
        ret = self.send_command(GET_TSID, True)
        return ddmmss_decode(ret)

    def get_utcoffset(self):
        "Get UTC offset (hours)"
        ret = self.send_command(GET_UOFF, True)
        try:
            value = float(ret)
        except ValueError:
            value = None
        return value

    def track_on(self):
        "Abilita tracking"
        return self.send_command(TRACK_ON, True)

    def track_off(self):
        "Disabilita tracking"
        return self.send_command(TRACK_OFF, True)

    def slew(self):
        "Send Slew to target command"
        return self.send_command(SLEW, True)

    def park(self):
        "Park telescope"
        return self.send_command(PARK, True)

    def unpark(self):
        "Park telescope"
        return self.send_command(UNPARK, True)

    def text_cmd(self, text):
        "invia comando generico"
        if not text.startswith(":"):
            text = ":"+text
        if not text.endswith("#"):
            text += "#"
        return self.send_command(text, True)

    def opc_init(self):
        "Invia comandi di inizializzazione per telescopio OPC"
        ret1 = self.set_lat(OPC.lat_deg)
        ret2 = self.set_lon(OPC.lon_deg)
        ret3 = self.set_time()
        ret4 = self.set_date()
        try:
            ret = ret1+ret2+ret3+ret4
        except TypeError:
            ret = None
        return ret

########################################################

def getddmmss(args):
    "Converte argomenti (dd [mm [ss]]) in float"
    if not args:
        return None
    value = float(args[0])
    sign = 1 if value >= 0 else -1
    value = abs(value)
    if len(args) >= 2:
        value += float(args[1])/60.
    if len(args) >= 3:
        value += float(args[2])/3600.
    return value*sign

def getint(args):
    "Riporta il primo argomento come intero"
    if args:
        return int(args[0])
    return None

def getfloat(args):
    "Riporta il primo argomento come float"
    if args:
        return float(args[0])
    return None

def getword(args):
    "Riporta il primo argomento come stringa"
    if args:
        return args[0]
    return None

def noargs(*_unused):
    "Tratta chiamate senza argomento"
    return None

class Executor:
    "Esecuzione comandi interattivi"
    def __init__(self, config, verbose):
        dcom = TeleCommunicator(config["tel_ip"], config["tel_port"], verbose=verbose)
#                    codice   descrizione                funzione      convers.argom.
        self.lxcmd = {"GA": ("Leggi altezza telescopio", dcom.get_alt, noargs),
                      "GC": ("Leggi data", dcom.get_date, noargs), 
                      "GD": ("Leggi declinazione telescopio", dcom.get_current_de, noargs),
                      "Gd": ("Leggi declinazione oggetto", dcom.get_target_de, noargs),
                      "GG": ("Leggi offset UTC", dcom.get_utcoffset, noargs),
                      "Gg": ("Leggi longitudine", dcom.get_lon, noargs),
                      "Gh": ("Leggi limite orizzonte", dcom.get_hlim, noargs),
                      "GL": ("Leggi tempo locale da telescopio", dcom.get_ltime, noargs),
                      "Gm": ("Leggi lato braccio", dcom.get_pside, noargs),
                      "Go": ("Leggi limite overhead", dcom.get_olim, noargs),
                      "GR": ("Leggi asc. retta telescopio", dcom.get_current_ra, noargs),
                      "Gr": ("Leggi asc. retta oggetto", dcom.get_target_ra, noargs),
                      "GS": ("Leggi tempo sidereo", dcom.get_tsid, noargs),
                      "GT": ("Leggi tracking rate", dcom.get_trate, noargs),
                      "Gt": ("Leggi latitudine", dcom.get_lat, noargs),
                      "GW": ("Leggi stato montatura", dcom.get_mstat, noargs),
                      "GU": ("Leggi stato globale", dcom.get_status, noargs),
                      "GVP": ("Leggi identificazione telescopio", dcom.get_ident, noargs),
                      "GZ": ("Leggi azimuth telescopio", dcom.get_az, noargs),
                      "hP": ("\"Park\" telescopio", dcom.park, noargs),
                      "hR": ("\"Unpark\" telescopio", dcom.unpark, noargs),
                      "Mge": ("\"pulse guide\" in direzione est", lambda x: dcom.pulse_guide("e", x), getint),
                      "Mgw": ("\"pulse guide\" in direzione ovest", lambda x: dcom.pulse_guide("w", x), getint),
                      "Mgn": ("\"pulse guide\" in direzione nord", lambda x: dcom.pulse_guide("n", x), getint),
                      "Mgs": ("\"pulse guide\" in direzione sud", lambda x: dcom.pulse_guide("s", x), getint),
                      "Me": ("Muovi in direzione est", lambda x="e": dcom.move_dir(x), noargs),
                      "Mw": ("Muovi in direzione ovest", lambda x="w": dcom.move_dir(x), noargs),
                      "Mn": ("Muovi in direzione nord", lambda x="n": dcom.move_dir(x), noargs),
                      "Ms": ("Muovi in direzione sud", lambda x="s": dcom.move_dir(x), noargs),
                      "MS": ("Slew all'oggetto", dcom.slew, noargs),
                      "Q":  ("Stop movimento", dcom.stop_dir, noargs),
                      "Qe": ("Stop mov. in direzione est", lambda x="e": dcom.stop_dir(x), noargs),
                      "Qw": ("Stop mov. in direzione ovest", lambda x="w": dcom.stop_dir(x), noargs),
                      "Qn": ("Stop mov. in direzione nord", lambda x="n": dcom.stop_dir(x), noargs),
                      "Qs": ("Stop mov. in direzione sud", lambda x="s": dcom.stop_dir(x), noargs),
                      "R": ("Imposta rate 0-9GCMS", dcom.set_rate, getword),
                      "SC": ("Imposta data", dcom.set_date, noargs),
                      "Sd": ("Imposta declinazione oggetto (dd mm ss)", dcom.set_de, getddmmss),
#                     "Sh": ("Imposta limite orizzonte", ..., getdd
                      "Sg": ("Imposta longitudine (ddd mm)", dcom.set_lon, getddmmss),
#                     "So": ("Imposta limite overhead", ..., getdd
                      "Sr": ("Imposta asc. retta oggetto (hh mm ss)", dcom.set_ra, getddmmss),
                      "SS": ("Imposta tempo sidereo da clock PC", dcom.set_tsid, noargs),
                      "ST": ("Imposta tracking rate", dcom.set_trate, getfloat),
                      "St": ("Imposta latitudine (dd mm)", dcom.set_lat, getddmmss),
                      "Td": ("Disabilita tracking", dcom.track_off, noargs),
                      "Te": ("Abilita tracking", dcom.track_on, noargs),
                     }
        self.hkcmd = {"in": ("Inizializzazione telescopio per OPC", dcom.opc_init, noargs),
                      "q":  ("Termina procedura", sys.exit, noargs),
                      "s":  ("Cerca comando", self.search, getword),
                      "st":  ("Imposta tempo locale e UTC offset da PC", dcom.set_time, noargs),
                      "t":  ("invia stringa (:,# possono essere omessi)", dcom.text_cmd, getword),
                     }

    def search(self, word):
        "Cerca comando contenente la parola"
        wsc = word.lower()
        allc = self.lxcmd.copy()
        allc.update(self.hkcmd)
        for key, value in allc.items():
            if wsc in value[0].lower():
                print("   %3s: %s"%(key, value[0]))
        return ""

    def execute(self, command):
        "Esegue comando interattivo"
        cmdw = command.split()
        if not cmdw:
            return "Nessun comando"
        clist = self.lxcmd
        cmd_spec = clist.get(cmdw[0])
        if not cmd_spec:
            clist = self.hkcmd
            cmd_spec = clist.get(cmdw[0])
        if cmd_spec:
            the_arg = cmd_spec[2](cmdw[1:])
            if the_arg:
                ret = cmd_spec[1](the_arg)
            else:
                ret = cmd_spec[1]()
            if ret is None:
                ret = "Nessuna risposta"
        else:
            ret = "Comando sconosciuto!"
        return ret

    def usage(self):
        "Visualizza elenco comandi"
        keys = list(self.lxcmd.keys())
        keys.sort(key=str.lower)
        print("\nComandi LX200:")
        for key in keys:
            print("   %3s: %s"%(key, self.lxcmd[key][0]))
        keys = list(self.hkcmd.keys())
        keys.sort(key=str.lower)
        print("\nComandi aggiuntivi:")
        for key in keys:
            print("   %3s: %s"%(key, self.hkcmd[key][0]))

TODO = """
Tracking rate commands
Set sidereal rate RA 	:STdd.ddddd# 	Reply: 0 or 1
Get sidereal rate RA 	:GT# 	Reply: dd.ddddd#
Track sidereal rate RA (default)	:TQ# 	Reply: [none]
Track sidereal rate reset 	:TR# 	Reply: [none]
Track rate increase 0.02Hz 	:T+# 	Reply: [none]
Track rate decrease 0.02Hz 	:T-# 	Reply: [none]
Track solar rate RA 	:TS# 	Reply: [none]
Track lunar rate RA 	:TL# 	Reply: [none]
Track king rate RA 	:TK# 	Reply: [none]
Tracking enable 	:Te# 	Reply: 0 or 1
Tracking disable 	:Td# 	Reply: 0 or 1
Refraction rate tracking 	:Tr# 	Reply: 0 or 1
No refraction rate tracking 	:Tn# 	Reply: 0 or 1

Sync. with current target RA/Dec	:CS#	Reply: [none]
Sync. with current target RA/Dec	:CM#	Reply: N/A#
Note: Sync's that are not allowed fail silently. This can happen due to slews, parking, or exceeded limits.

Library commands
Select catalog no. 	:Lonn# 	Reply: 0 or 1
Move Back in catalog 	:LB# 	Reply: [none]
Move to Next in catalog 	:LN# 	Reply: [none]
Move to catalog item no.	:LCnnnn# 	Reply: [none]
Move to catalog name rec.	:L$# 	Reply: 1
Get catalog item id. 	:LI# 	Reply: name,type#
Read catalog item info.
(also moves forward) 	:LR# 	Reply: name,type,RA,De#

Get statUs returns:
N-Not slewing, H-At Home position,
P-Parked, p-Not parked, F-Park Failed,
I-park In progress, R-PEC Recorded
G-Guiding in progress, S-GPS PPS Synced 	:GU# 	Reply: sss#
"""


def main():
    "Invio comandi da console e test"
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

    verbose = ("-v" in sys.argv)

    exe = Executor(config, verbose)

    while True:
        answ = input("Comando (invio per aiuto): ")
        if answ:
            ret = exe.execute(answ)
            print(ret)
        else:
            exe.usage()

if __name__ == "__main__":
    import readline
    main()
