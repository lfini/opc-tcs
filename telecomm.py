"""
Funzioni di comunicazione per controllo telescopio OPC

Implementa i codici LX200 specifici per OnStep

Uso interattivo:

      python telcomm.py [-dhvV]

Dove:
      -d  Collegamento al simulatore (IP: 127.0.0.1, Port: 9753)
      -v  Modo verboso (visualizza protocollo)
      -V  Mostra versione ed esci
"""

import sys
import re
import socket
import time
import configure as conf

from astro import OPC, float2ums, loc_st_now

__version__ = "1.12"
__date__ = "Febbraio 2019"
__author__ = "Luca Fini"

                                # Comandi definiti
                                 # Comandi di preset
SET_ALTP = ":Sa+%02d*%02d'%02d#" # Set altezza target (+dd,mm,ss)
SET_ALTN = ":Sa-%02d*%02d'%02d#" # Set altezza target (-dd,mm,ss)
SET_AZ = ":Sz%03d*%02d"          # Set azimuth target (ddd,mm)
SET_DATE = ":SC%02d/%02d/%02d#"  # Set data
SET_DECP = ":Sd+%02d*%02d:%02d#" # Set declinazione target (+dd,mm,ss)
SET_DECN = ":Sd-%02d*%02d:%02d#" # Set declinazione target (-dd,mm,ss)
SET_LATP = ":St+%02d*%02d#"      # Set latitudine del luogo (+dd, mm)
SET_LATN = ":St-%02d*%02d#"      # Set latitudine del luogo (-dd, mm)
SET_LONP = ":Sg+%03d*%02d#"      # Set longitudine del luogo (+ddd, mm)
SET_LONN = ":Sg-%03d*%02d#"      # Set longitudine del luogo (-ddd, mm)
SET_MNAP = ":Sh+%02d#"           # Set minima altezza raggiungibile (+dd)
SET_MNAN = ":Sh-%02d#"           # Set minima altezza raggiungibile (-dd)
SET_MAXA = ":So%02d#"            # Set massima altezza raggiungibile (dd)
SET_LTIME = ":SL%02d:%02d:%02d#" # Set ora locale: hh, mm, ss
SET_ONSTEP_V = ":SX%s,%s#"       # Set valore OnStep
SET_RA = ":Sr%02d:%02d:%02d#"    # Set ascensione retta dell'oggetto target (hh,mm,ss)
SET_TRATE = ":ST%08.5f#"         # Set freq. di tracking (formato da commenti nel codice)
SET_TSID = ":SS%02d:%02d:%02d#"  # Set tempo sidereo: hh, mm, ss
SET_UOFF = ":SG%s%04.1f#"        # Set UTC offset (UTC = LocalTime+Offset)

TRACK_ON = ":Te#"                # Abilita tracking
TRACK_OFF = ":Td#"               # Disabilita tracking
ONTRACK = ":To#"                 # Abilita "On Track"
TRACKR_ENB = ":Tr#"              # Abilita tracking con rifrazione
TRACKR_DIS = ":Tn#"              # Disabilita tracking con rifrazione
                                 # return: 0 failure, 1 success
TRACK_INCR = ":T+#"              # Incr. master sidereal clock di 0.02 Hz (stored in EEPROM)
TRACK_DECR = ":T-#"              # Decr. master sidereal clock di 0.02 Hz (stored in EEPROM)
TRACK_KING = ":TK#"              # Tracking rate = king (include rifrazione)
TRACK_LUNAR = ":TL#"             # Tracking rate = lunar
TRACK_SIDER = ":TQ#"             # Tracking rate = sidereal
TRACK_SOLAR = ":TS#"             # Tracking rate = solar
TRACK_RESET = ":TR#"             # Reset master sidereal clock
                                 # return:  None
TRACK_ONE = ":T1#"               # Track singolo asse (Disabilita Dec tracking)
TRACK_TWO = ":T2#"               # Track due assi

                                 # Comandi di movimento
MOVE_TO = ":MS#"                 # Muovi a target definito
MOVE_DIR = ":M%s#"               # Muovi ad est/ovest/nord/sud
STOP_DIR = ":Q%s#"               # Stop movimento ad est/ovest/nord/sud
STOP = ":Q#"                     # Stop telescopio

PULSE_M = ":Mg%s%d#"              # Pulse move              < TBD

SET_HOME = ":hF#"                # Reset telescope at Home position.
GOTO_HOME = ":hC#"               # Move telescope to Home position.
PARK = ":hP#"                    # Park telescope
SET_PARK = ":hQ#"                # Park telescope
UNPARK = ":hR#"                  # Unpark telescope

SYNC_RADEC = ":CS#"        # Sync with current RA/DEC (no reply)

#Comandi set/get antibacklash

SET_ANTIB_DEC = ":$BD%03d#"   # Set Dec Antibacklash
SET_ANTIB_RA = ":$BR%03d#"    # Set RA Antibacklash

GET_ANTIB_DEC = ":%BD#"       # Get Dec Antibacklash
GET_ANTIB_RA = ":%BR#"        # Get RA Antibacklash


                           # Comandi informativi
GET_AZ = ":GZ#"            # Get telescope azimuth
GET_ALT = ":GA#"           # Get telescope altitude
GET_CUR_DE = ":GD#"        # Get current declination
GET_CUR_RA = ":GR#"        # Get current right ascension
GET_DB = ":D#"             # Get distance bar
GET_DATE = ":GC#"          # Get date
GET_HLIM = ":Gh"           # Get horizont limit
GET_OVER = ":Go"           # Get overhead limit
GET_FMWNAME = ":GVP#"      # Get Firmware name
GET_FMWDATE = ":GVD#"      # Get Firmware Date (mmm dd yyyy)
GET_GENMSG = ":GVM#"       # Get general message (aaaaa)
GET_FMWNUMB = ":GVN#"      # Get Firmware version (d.dc)
GET_FMWTIME = ":GVT#"      # Get Firmware time (hh:mm:ss)
GET_OSVALUE = ":GX..#"     # Get OnStep Value
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
GET_TFMT = ":Gc#"          # Get current time format (ret: 24#)
GET_UOFF = ":GG#"          # Get UTC offset time

GET_NTEMP = ":ZTn#"        # Get number of temperature sensors
GET_TEMP = ":ZT%d#"        # Get temperature from sensor n (return nn.n)

# Comandi fuocheggatore.
# Nota: gli stessi commandi valgono per il
#       fuocheggiatore 1 se iniziano per "F"
#       e il fuocheggiatore 2 se iniziano per "f"

FOC_SELECT = ":%sA%s#" # Seleziona fuocheggiatore (1/2)

FOC_MOVEIN = ":%s+#"   # Muovi fuocheggiatore verso obiettivo
FOC_MOVEOUT = ":%s-#"  # Muovi fuocheggiatore via da obiettivo
FOC_STOP = ":%sQ#"     # Stop movimento fuocheggiatore
FOC_ZERO = ":%sZ#"     # Muovi in posizione zero
FOC_FAST = ":%sF#"     # Imposta movimento veloce
FOC_SETR = ":%sR%04d#" # Imposta posizione relativa (micron)
FOC_SLOW = ":%sS#"     # Imposta movimento lento
FOC_SETA = ":%sS%04d#" # Imposta posizione assoluta (micron)
FOC_RATE = ":%s%1d"    # Imposta velocità (1,2,3,4)

GET_FOC_ACT = ":%sA#"  # Fuocheggiatore attivo (ret: 0/1)
GET_FOC_POS = ":%sG#"  # Leggi posizione corrente (+-ddd)
GET_FOC_MIN = ":%sI#"  # Leggi posizione minima
GET_FOC_MAX = ":%sM#"  # Leggi posizione minima
GET_FOC_STAT = ":%sT#" # Leggi stato corrente (M: moving, S: stop)

ROT_ENABLE = ":r+#"    # Abilita rotatore
ROT_DISABLE = ":r-#"   # Disabilita rotatore
ROT_TOPAR = ":rP#"     # Muovi rotatore ad angolo parallattico
ROT_REVERS = ":rR#"    # Inverte direzione rotatore
ROT_SETHOME = ":rF#"   # Reset rotatore a posizione home
ROT_GOHOME = ":rC#"    # Muovi rotatore a posizione home
ROT_CLKWISE = ":r>#"   # Muovi rotatore in senso orario come da comando
ROT_CCLKWISE = ":r<#"  # Muovi rotatore in senso antiorario come da incremento
ROT_SETINCR = ":r%d"   # Preset incremento per movimento rotatore (1,2,3)
ROT_SETPOSP = ":rS+%03d*%02d'%02d" # Set posizione rotatore (+gradi)
ROT_SETPOSN = ":rS-%03d*%02d'%02d" # Set posizione rotatore (-gradi)

ROT_GET = ":rG#"       # Legge posizione rotatore (gradi)


TRACKING_INFO = """
Variabili relative alle frequenze di Tracking:

#define StepsPerDegreeAxis1  56000.0                               Config.Classic.h
#define StepsPerSecondAxis1  ((double)StepsPerDegreeAxis1/240.0)   Globals.h
long siderealInterval       = 15956313L;  >>> EE_siderealInterval  Globals.h
     Number of 16MHz clocks in one sidereal second
long masterSiderealInterval = siderealInterval;                    Globals.h
long SiderealRate = siderealInterval/StepsPerSecondAxis1           Globals.h
     This is the time between steps for sidereal tracking
"""

ERRCODE = "Codice di errore"

CODICI_STATO = {
    "n": "non in tracking",
    "N": "Non in slewing",
    "p": "Non in park, ",
    "P": "in park  ",
    "I": "in movimento verso park, ",
    "F": "park fallito",
    "R": "I dati PEC data sono stati registrati",
    "H": "in posizione home",
    "S": "PPS sincronizzato",
    "G": "Modo guida attivo",
    "f": "Errore movimento asse",
    "r": "PEC refr abilitato    ",
    "s": "su asse singolo (solo equatoriale)",
    "t": "on-track abilitato    ",
    "w": "in posizione home     ",
    "u": "Pausa in pos. home abilitata",
    "z": "cicalino abilitato",
    "a": "Inversione al meridiano automatica",
    "/": "Stato pec: ignora",
    ",": "Stato pec: prepara disposizione ",
    "~": "Stato pec: disposizione  in corso",
    ";": "Stato pec: preparazione alla registrazione",
    "^": "Stato pec: registrazione in corso",
    ".": "PEC segnala detezione indice dall'ultima chiamata",
    "E": "Montatura equatoriale  tedesca",
    "K": "Montatura equatoriale a forcella",
    "k": "Montatura altaz a forcella",
    "A": "Montatura altaz",
    "o": "lato braccio ignoto",
    "T": "lato est",
    "W": "lato ovest",
    "0": "Nessun errore",
    "1": ERRCODE,
    "2": ERRCODE,
    "3": ERRCODE,
    "4": ERRCODE,
    "5": ERRCODE,
    "6": ERRCODE,
    "7": ERRCODE,
    "8": ERRCODE,
    "9": ERRCODE}

CODICI_RISPOSTA = """
    0: movimento possibile
    1: oggetto sotto orizzonte
    2: oggetto non selezionato
    3: controller in standby
    4: telescopio in park
    5: movimento in atto
    6: superati limiti (MaxDec, MinDec, UnderPoleLimit, MeridianLimit)
    7: errore hardware
    8: movimento in atto
    9: errore non specificato
"""

CODICI_TABELLE_ONSTEP = """
0: Modello di allineamento     8: Data e ora
9: Varie                       E: Parametri configurazione
F: Debug                       G: Ausiliari (??)
U: Stato motori step
"""

CODICI_ONSTEP_0X = """
0x: Modello allineamento
  00:  indexAxis1  (x 3600.)
  01:  indexAxis2  (x 3600.)
  02:  altCor      (x 3600.)
  03:  azmCor      (x 3600.)
  04:  doCor       (x 3600.)
  05:  pdCor       (x 3600.)
  06:  ffCor       (x 3600.)
  07:  dfCor       (x 3600.)
  08:  tfCor       (x 3600.)
  09:  Number of stars, reset to first star
  0A:  Star  #n HA   (hms)
  0B:  Star  #n Dec  (dms)
  0C:  Mount #n HA   (hms)
  0D:  Mount #n Dec  (dms)
  0E:  Mount PierSide (and increment n)
"""

CODICI_ONSTEP_8X = """
8x: Data e ora
  80:  UTC time
  81:  UTC date
"""

CODICI_ONSTEP_9X = """
9x: Varie
  90:  pulse-guide rate
  91:  pec analog value
  92:  MaxRate
  93:  MaxRate (default)
  94:  pierSide (E, W, N:none)
  95:  autoMeridianFlip
  96:  preferred pier side  (E, W, N:none)
  97:  slew speed
  98:  Rotator mode (D: derotate, R:rotate, N:no rotator)
  9A:  temperature in deg. C
  9B:  pressure in mb
  9C:  relative humidity in %
  9D:  altitude in meters
  9E:  dew point in deg. C
  9F:  internal MCU temperature in deg. C
"""

CODICI_ONSTEP_UX = """
Ux: Stato motori step
  U1: ST(Stand Still),  OA(Open Load A), OB(Open Load B), GA(Short to Ground A),
  U2: GB(Short to Ground B), OT(Overtemperature Shutdown 150C),
      PW(Overtemperature Pre-warning 120C)
"""

CODICI_ONSTEP_EX = """
Ex: Parametri configurazione
  E1: MaxRate
  E2: DegreesForAcceleration
  E3: BacklashTakeupRate
  E4: PerDegreeAxis1
  E5: StepsPerDegreeAxis2
  E6: StepsPerSecondAxis1
  E7: StepsPerWormRotationAxis1
  E8: PECBufferSize
  E9: minutesPastMeridianE
  EA: minutesPastMeridianW
  EB: UnderPoleLimit
  EC: Dec
  ED: MaxDec
"""

CODICI_ONSTEP_FX = """
Fn: Debug
  F0:  Debug0, true vs. target RA position
  F1:  Debug1, true vs. target Dec position
  F2:  Debug2, trackingState
  F3:  Debug3, RA refraction tracking rate
  F4:  Debug4, Dec refraction tracking rate
  F6:  Debug6, HA target position
  F7:  Debug7, Dec target position
  F8:  Debug8, HA motor position
  F9:  Debug9, Dec motor position
  FA:  DebugA, Workload
  FB:  DebugB, trackingTimerRateAxis1
  FC:  DebugC, sidereal interval  (L.F.)
  FD:  DebugD, sidereal rate  (L.F.)
"""
CODICI_ONSTEP_GX = """
  G0:   valueAux0/2.55
  G1:   valueAux1/2.55
  G2:   valueAux2/2.55
  G3:   valueAux3/2.55
  G4:   valueAux4/2.55
  G5:   valueAux5/2.55
  G6:   valueAux6/2.55
  G7:   valueAux7/2.55
  G8:   valueAux8/2.55
  G9:   valueAux9/2.55
  GA:   valueAux10/2.5
  GB:   valueAux11/2.55
  GC:   valueAux12/2.55
  GD:   valueAux13/2.55
  GE:   valueAux14/2.55
  GF:   valueAux15/2.55
"""

def get_version():
    "Riporta informazioni su versione"
    return "telecomm.py - Vers. %s. %s %s"%(__version__, __author__, __date__)

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
        """
Invio comandi. expected == True: prevista risposta.

Possibili valori di ritorno:
    '':      nessuna risposta attesa
    'xxxx':  Stringa di ritorno da OnStep
    1/0:     Successo/fallimento da OnStep
    None:    Risposta prevista ma non ricevuta"""
        if self.verbose:
            print("CMD-", command)
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.settimeout(self.timeout)
        try:
            skt.connect((self.ipadr, self.port))
        except IOError:
            if self.verbose:
                print("Tel. non connesso")
            return None
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
                    print("RET-", ret)
                skt.close()
                repl = ret.decode("ascii")
                if repl and repl[-1] == "#":
                    repl = repl[:-1]
        else:
            repl = ""
        return repl

    def set_verbose(self):
        "Abilita/disabilita modo verboso"
        self.verbose = not self.verbose
        if self.verbose:
            ret = "Abilitato modo verboso"
        else:
            ret = "Disbilitato modo verboso"
        return ret

    def set_ra(self, hours):
        "Imposta ascensione retta oggetto (ore)"
        if hours < 24. and hours >= 0.:
            cmd = SET_RA % float2ums(hours)
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_alt(self, deg):
        "Imposta altezza oggetto (gradi)"
        if deg >= -90. and deg <= 90.:
            if deg >= 0:
                cmd = SET_ALTP%(float2ums(deg))
            else:
                cmd = SET_ALTN%(float2ums(-deg))
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_az(self, deg):
        "Imposta azimut oggetto (0..360 gradi)"
        if deg >= -0. and deg <= 360.:
            cmd = SET_AZ%float2ums(deg)[:2]
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_de(self, deg):
        "Imposta declinazione oggetto (gradi)"
        if deg >= -90. and deg <= 90.:
            if deg >= 0:
                cmd = SET_DECP%(float2ums(deg))
            else:
                cmd = SET_DECN%(float2ums(-deg))
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_max_alt(self, deg):
        "Imposta altezza massima raggiungibile (60..90 gradi)"
        if deg >= 60 and deg <= 90:
            cmd = SET_MAXA%deg
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_min_alt(self, deg):
        "Imposta altezza minima raggiungibile (-30..30 gradi)"
        if deg >= -30 and deg <= 30:
            if deg >= 0:
                cmd = SET_MNAP%(deg)
            else:
                cmd = SET_MNAN%(-deg)
            ret = self.send_command(cmd, 1)
        else:
            raise ValueError
        return ret

    def set_trate(self, rate):
        "Imposta tracking rate (Hz)"
        return self.send_command(SET_TRATE%rate, True)

    def set_lat(self, deg):
        "Imposta latitudine locale (gradi)"
        if deg >= 0:
            cmd = SET_LATP%(float2ums(deg)[:2])
        else:
            deg = -deg
            cmd = SET_LATN%(float2ums(deg)[:2])
        return self.send_command(cmd, 1)

    def set_lon(self, deg):
        "Imposta longitudine locale (gradi)"
        if deg >= 0:
            cmd = SET_LONP%(float2ums(deg)[:2])
        else:
            deg = -deg
            cmd = SET_LONN%(float2ums(deg)[:2])
        return self.send_command(cmd, 1)

    def set_date(self):
        "Imposta data da clock del PC"
        ttt = list(time.localtime())
        ttt[8] = 0                # elimina ora legale
        tt0 = time.mktime(tuple(ttt))
        ttt = time.localtime(tt0)
        cmd = SET_DATE%(ttt[1], ttt[2], ttt[0]-2000)
        return self.send_command(cmd, 1)

    def set_tsid(self):
        "Imposta tempo sidereo da clock PC"
        tsidh = loc_st_now()
        return self.send_command(SET_TSID%float2ums(tsidh), False)

    def set_time(self):
        "Imposta tempo telescopio da clock del PC"
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

    def _set_onstep_par(self, code, str_val):
        "Imposta parametro on step generico"
        cmd = SET_ONSTEP_V%(code, str_val)
        return self.send_command(cmd, True)

    def set_onstep_00(self, value):
        "Imposta OnStep indexAxis1 [integer]"
        return self._set_onstep_par("00", "%d"%value)

    def set_onstep_01(self, value):
        "Imposta OnStep indexAxis2 [integer]"
        return self._set_onstep_par("01", "%d"%value)

    def set_onstep_02(self, value):
        "Imposta OnStep altCor [integer]"
        return self._set_onstep_par("02", "%d"%value)

    def set_onstep_03(self, value):
        "Imposta OnStep azmCor [integer]"
        return self._set_onstep_par("03", "%d"%value)

    def set_onstep_04(self, value):
        "Imposta OnStep doCor [integer]"
        return self._set_onstep_par("04", "%d"%value)

    def set_onstep_05(self, value):
        "Imposta OnStep pdCor [integer]"
        return self._set_onstep_par("05", "%d"%value)

    def set_onstep_06(self, value):
        "Imposta OnStep dfCor [integer]"
        return self._set_onstep_par("06", "%d"%value)

    def set_onstep_07(self, value):
        "Imposta OnStep ffCor (inutilizz. per montatura equ) [integer]"
        return self._set_onstep_par("07", "%d"%value)

    def set_onstep_08(self, value):
        "Imposta OnStep tfCor [integer]"
        return self._set_onstep_par("08", "%d"%value)

    def set_onstep_92(self, value):
        "Imposta OnStep MaxRate (max. accelerazione) [integer]"
        return self._set_onstep_par("92", "%d"%value)

    def set_onstep_93(self, value):
        "Imposta OnStep MaxRate preset (max. accelerazione) [1-5: 200%,150%,100%,75%,50%]"
        if  0 < value < 6:
            return self._set_onstep_par("93", "%d"%value)
        return "0"

    def set_onstep_95(self, value):
        "Imposta OnStep autoMeridianFlip [0: disabilita, 1: abilita]"
        if value not in (0, 1):
            return "0"
        return self._set_onstep_par("95", "%d"%value)

    def set_onstep_96(self, value):
        "Imposta OnStep preferredPierSide [E, W, B (best)]"
        try:
            value = value.upper()
        except:
            return "0"
        if value not in ("E", "W", "B"):
            return "0"
        return self._set_onstep_par("96", value)

    def set_onstep_97(self, value):
        "Imposta OnStep cicalino [0: disabilita, 1: abilita]"
        if value not in (0, 1):
            return "0"
        return self._set_onstep_par("97", "%d"%value)

    def set_onstep_98(self, value):
        "Imposta OnStep pausa a HOME all'inversione meridiano [0: disabilita, 1: abilita]"
        if value not in (0, 1):
            return "0"
        return self._set_onstep_par("98", "%d"%value)

    def set_onstep_99(self, value):
        "Imposta OnStep continua dopo pausa a HOME [0: disabilita, 1: abilita]"
        if value not in (0, 1):
            return "0"
        return self._set_onstep_par("99", "%d"%value)

    def set_onstep_e9(self, value):
        "Imposta OnStep minuti dopo il meridiano EST [integer]"
        return self._set_onstep_par("E9", "%d"%value)

    def set_onstep_ea(self, value):
        "Imposta OnStep minuti dopo il meridiano OVEST [integer]"
        return self._set_onstep_par("EA", "%d"%value)

    def sync_radec(self):
        "Sync con valore corrente asc.retta e decl. [No risp.]"
        return self.send_command(SYNC_RADEC, False)

    def move_target(self):
        "Muovi telescopio al target definito. Risposta: vedi mvt?"
        return self.send_command(MOVE_TO, True)

    def move_east(self):
        "Muovi telescopio direz. est"
        return self.send_command(MOVE_DIR%"e", False)

    def move_west(self):
        "Muovi telescopio direz. ovest"
        return self.send_command(MOVE_DIR%"w", False)

    def move_north(self):
        "Muovi telescopio direz. nord"
        return self.send_command(MOVE_DIR%"n", False)

    def move_south(self):
        "Muovi telescopio direz. sud"
        return self.send_command(MOVE_DIR%"s", False)

    def set_rate(self, rate):
        "Imposta rate a Guide, C?, Move, Slew o 0-9"
        rrt = rate[0].upper()
        if rrt in "GCMS0123456789":
            return self.send_command(SET_TRATE+rrt, False)
        return None

    def stop(self):
        "Ferma movimento telescopio"
        return self.send_command(STOP, False)

    def stop_east(self):
        "Ferma movimento in direzione est"
        return self.send_command(STOP_DIR%"e", False)

    def stop_west(self):
        "Ferma movimento in direzione ovest"
        return self.send_command(STOP_DIR%"w", False)

    def stop_north(self):
        "Ferma movimento in direzione nord"
        return self.send_command(STOP_DIR%"n", False)

    def stop_south(self):
        "Ferma movimento in direzione sud"
        return self.send_command(STOP_DIR%"s", False)

    def pulse_guide_est(self, dtime):
        "Movimento ad impulso in direzione est (dtime=20-16399)"
        if dtime < 20 or dtime > 16399:
            return None
        return self.send_command(PULSE_M%("e", dtime), False)

    def pulse_guide_west(self, dtime):
        "Movimento ad impulso in direzione ovest (dtime=20-16399)"
        if dtime < 20 or dtime > 16399:
            return None
        return self.send_command(PULSE_M%("w", dtime), False)

    def pulse_guide_south(self, dtime):
        "Movimento ad impulso in direzione sud (dtime=20-16399)"
        if dtime < 20 or dtime > 16399:
            return None
        return self.send_command(PULSE_M%("s", dtime), False)

    def pulse_guide_north(self, dtime):
        "Movimento ad impulso in direzione nord (dtime=20-16399)"
        if dtime < 20 or dtime > 16399:
            return None
        return self.send_command(PULSE_M%("n", dtime), False)

    def get_alt(self):
        "Leggi altezza telescopio (gradi)"
        ret = self.send_command(GET_ALT, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_antib_dec(self):
        "Leggi valore antibacklash declinazione (steps/arcsec)"
        ret = self.send_command(GET_ANTIB_DEC, True)
        if ret:
            return int(ret)
        return None

    def get_antib_ra(self):
        "Leggi valore antibacklash ascensione retta (steps/arcsec)"
        ret = self.send_command(GET_ANTIB_RA, True)
        if ret:
            return int(ret)
        return None

    def get_az(self):
        "Leggi azimuth telescopio (gradi)"
        ret = self.send_command(GET_AZ, True)
        return ddmmss_decode(ret)

    def get_current_de(self):
        "Leggi declinazione telescopio (gradi)"
        ret = self.send_command(GET_CUR_DE, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_current_ha(self):
        "Calcola angolo orario telescopio (ore)"
        ret = self.send_command(GET_CUR_RA, True)
        rah = ddmmss_decode(ret)
        if rah is None:
            return None
        return loc_st_now()-rah

    def get_current_ra(self):
        "Leggi ascensione retta telescopio (ore)"
        ret = self.send_command(GET_CUR_RA, True)
        return ddmmss_decode(ret)

    def get_date(self):
        "Leggi data impostata al telescopio"
        return self.send_command(GET_DATE, True)

    def get_db(self):
        "Legge stato movimento (riporta '0x7f' se in moto)"
        return self.send_command(GET_DB, True)

    def get_foc1_act(self):
        "Fuocheggiatore 1 attivo?"
        cmd = GET_FOC_ACT%"F"
        return self.send_command(cmd, True)

    def get_foc2_act(self):
        "Fuocheggiatore 2 attivo?"
        cmd = GET_FOC_ACT%"f"
        return self.send_command(cmd, True)

    def _get_foc_min(self, focuser):
        "Legge posizione minima fuocheggiatore 1/2 (micron)"
        cmd = GET_FOC_MIN%focuser
        ret = self.send_command(cmd, True)
        if ret:
            return int(ret)
        return None

    def get_foc1_min(self):
        "Legge posizione minima fuocheggiatore 1 (micron)"
        return self._get_foc_min("F")

    def get_foc2_min(self):
        "Legge posizione minima fuocheggiatore 2 (micron)"
        return self._get_foc_min("f")

    def _get_foc_max(self, focuser):
        "Legge posizione massima fuocheggiatore 1/2 (micron)"
        cmd = GET_FOC_MAX%focuser
        ret = self.send_command(cmd, True)
        if ret:
            return int(ret)
        return None

    def get_foc1_max(self):
        "Legge posizione massima fuocheggiatore 1 (micron)"
        return self._get_foc_max("F")

    def get_foc2_max(self):
        "Legge posizione massima fuocheggiatore 2 (micron)"
        return self._get_foc_max("f")

    def _get_foc_pos(self, focuser):
        "Legge posizione corrente fuocheggiatore 1/2 (micron)"
        cmd = GET_FOC_POS%focuser
        ret = self.send_command(cmd, True)
        if ret:
            return int(ret)
        return None

    def get_foc1_pos(self):
        "Legge posizione corrente fuocheggiatore 1 (micron)"
        return self._get_foc_pos("F")

    def get_foc2_pos(self):
        "Legge posizione corrente fuocheggiatore 2 (micron)"
        return self._get_foc_pos("f")

    def get_foc1_stat(self):
        "Legge stato fuocheggiatore 1 (M: in movimento, S: fermo)"
        cmd = GET_FOC_STAT%"F"
        return self.send_command(cmd, True)

    def get_foc2_stat(self):
        "Legge stato fuocheggiatore 2 (M: in movimento, S: fermo)"
        cmd = GET_FOC_STAT%"f"
        return self.send_command(cmd, True)

    def get_hlim(self):
        "Leggi minima altezza sull'orizzonte (gradi)"
        ret = self.send_command(GET_HLIM, True)
        return ret

    def get_olim(self):
        "Leggi massima altezza sull'orizzonte (gradi)"
        ret = self.send_command(GET_OVER, True)
        return ret

    def get_lon(self):
        "Leggi longitudine del sito (gradi)"
        ret = self.send_command(GET_LON, True)
        return ddmm_decode(ret, with_sign=True)

    def get_lat(self):
        "Leggi latitudine del sito (gradi)"
        ret = self.send_command(GET_LAT, True)
        return ddmm_decode(ret, with_sign=True)

    def get_fmwname(self):
        "Leggi nome firmware"
        return self.send_command(GET_FMWNAME, True)

    def get_fmwdate(self):
        "Leggi data firmware"
        return self.send_command(GET_FMWDATE, True)

    def get_genmsg(self):
        "Leggi messaggio generico"
        return self.send_command(GET_GENMSG, True)

    def get_fmwnumb(self):
        "Leggi versione firmware"
        return self.send_command(GET_FMWNUMB, True)

    def get_fmwtime(self):
        "Leggi ora firmware"
        return self.send_command(GET_FMWTIME, True)

    def get_firmware(self):
        "Leggi informazioni complete su firmware"
        return (self.send_command(GET_FMWNAME, True),
                self.send_command(GET_FMWNUMB, True),
                self.send_command(GET_FMWDATE, True),
                self.send_command(GET_FMWTIME, True))

    def get_onstep_value(self, value):
        "Leggi valore parametro OnStep (per tabella: gos?)"
        cmd = GET_OSVALUE.replace("..", value[:2].upper())
        ret = self.send_command(cmd, True)
        return ret

    def get_ltime(self):
        "Leggi tempo locale (ore)"
        ret = self.send_command(GET_LTIME, True)
        return ddmmss_decode(ret)

    def get_mstat(self):
        "Leggi stato allineamento montatura"
        return self.send_command(GET_MSTAT, True)

    def get_pside(self):
        "Leggi lato di posizione del braccio (E,W, N:non.disp.)"
        return self.send_command(GET_PSIDE, True)

    def gst_print(self):
        "Stampa stato telescopio. Per tabella stati: gst?"
        stat = self.send_command(GET_STAT, True)
        if stat:
            for stchr in stat:
                print(" %s: %s"%(stchr, CODICI_STATO.get(stchr, "???")))
        return stat

    def get_status(self):
        "Leggi stato telescopio. Per tabella stati: gst?"
        ret = self.send_command(GET_STAT, True)
        return ret

    def get_target_de(self):
        "Leggi declinazione oggetto (gradi)"
        ret = self.send_command(GET_TAR_DE, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_target_ra(self):
        "Leggi ascensione retta oggetto (ore)"
        ret = self.send_command(GET_TAR_RA, True)
        return ddmmss_decode(ret)

    def get_timefmt(self):
        "Leggi formato ora"
        return self.send_command(GET_TFMT, True)

    def get_trate(self):
        "Leggi tracking rate (Hz)"
        ret = self.send_command(GET_TRATE, True)
        return float_decode(ret)

    def get_tsid(self):
        "Leggi tempo sidereo (ore)"
        ret = self.send_command(GET_TSID, True)
        return ddmmss_decode(ret)

    def get_utcoffset(self):
        "Leggi offset UTC (ore)"
        ret = self.send_command(GET_UOFF, True)
        try:
            value = float(ret)
        except ValueError:
            value = None
        return value

    def get_ntemp(self):
        "Leggi numero di sensori di temperatura"
        ret = self.send_command(GET_NTEMP, True)
        return int(ret)

    def get_temp(self, num):
        "Leggi sensore temperatura n"
        if num >= 0 and num <= 9:
            cmd = GET_TEMP%num
            ret = self.send_command(cmd, True)
            try:
                value = float(ret)
            except ValueError:
                value = None
        else:
            value = None
        return value

    def _foc_sel(self, num, focuser):
        "seleziona fuocheggiatore 1/2"
        if num not in (1, 2):
            return None
        cmd = FOC_SELECT%(focuser, num)
        return self.send_command(cmd, False)

    def foc1_sel(self, num):
        "Seleziona fuocheggiatore 1"
        return self._foc_sel(num, "F")

    def foc2_sel(self, num):
        "Seleziona fuocheggiatore 2"
        return self._foc_sel(num, "f")

    def move_foc1_in(self):
        "Muovi fuocheggiatore 1 verso obiettivo"
        cmd = FOC_MOVEIN%"F"
        return self.send_command(cmd, False)

    def move_foc2_in(self):
        "Muovi fuocheggiatore 2 verso obiettivo"
        cmd = FOC_MOVEIN%"f"
        return self.send_command(cmd, False)

    def move_foc1_out(self):
        "Muovi fuocheggiatore 1 via da obiettivo"
        cmd = FOC_MOVEOUT%"F"
        return self.send_command(cmd, False)

    def move_foc2_out(self):
        "Muovi fuocheggiatore 2 via da obiettivo"
        cmd = FOC_MOVEOUT%"f"
        return self.send_command(cmd, False)

    def stop_foc1(self):
        "Ferma movimento fuocheggiatore 1"
        cmd = FOC_STOP%"F"
        return self.send_command(cmd, False)

    def stop_foc2(self):
        "Ferma movimento fuocheggiatore 2"
        cmd = FOC_STOP%"f"
        return self.send_command(cmd, False)

    def move_foc1_zero(self):
        "Muovi fuocheggiatore 1 in posizione zero"
        cmd = FOC_ZERO%"F"
        return self.send_command(cmd, False)

    def move_foc2_zero(self):
        "Muovi fuocheggiatore 2 in posizione zero"
        cmd = FOC_ZERO%"f"
        return self.send_command(cmd, False)

    def set_foc1_fast(self):
        "Imposta velocità alta fuocheggiatore 1"
        cmd = FOC_FAST%"F"
        return self.send_command(cmd, False)

    def set_foc2_fast(self):
        "Imposta velocità alta fuocheggiatore 2"
        cmd = FOC_FAST%"f"
        return self.send_command(cmd, False)

    def set_foc1_slow(self):
        "Imposta velocità bassa fuocheggiatore 1"
        cmd = FOC_SLOW%"F"
        return self.send_command(cmd, False)

    def set_foc2_slow(self):
        "Imposta velocità bassa fuocheggiatore 2"
        cmd = FOC_SLOW%"f"
        return self.send_command(cmd, False)

    def _set_foc_speed(self, rate, focuser):
        "Imposta velocità (1,2,3,4) fuocheggiatore 1/2"
        if rate > 4:
            rate = 4
        elif rate < 1:
            rate = 1
        cmd = FOC_RATE%(focuser, rate)
        return self.send_command(cmd, False)

    def set_foc1_speed(self, rate):
        "Imposta velocità (1,2,3,4) fuocheggiatore 1"
        return self._set_foc_speed(rate, "F")

    def set_foc2_speed(self, rate):
        "Imposta velocità (1,2,3,4) fuocheggiatore 2"
        return self._set_foc_speed(rate, "f")

    def set_foc1_rel(self, pos):
        "Imposta posizione relativa fuocheggiatore 1 (micron)"
        cmd = FOC_SETR%("F", pos)
        return self.send_command(cmd, False)

    def set_foc2_rel(self, pos):
        "Imposta posizione relativa fuocheggiatore 2 (micron)"
        cmd = FOC_SETR%("f", pos)
        return self.send_command(cmd, False)

    def set_foc1_abs(self, pos):
        "Imposta posizione assoluta fuocheggiatore 1 (micron)"
        cmd = FOC_SETA%("F", pos)
        return self.send_command(cmd, False)

    def set_foc2_abs(self, pos):
        "Imposta posizione assoulta fuocheggiatore 2 (micron)"
        cmd = FOC_SETA%("f", pos)
        return self.send_command(cmd, False)

    def rot_disable(self):
        "Disabilita rotatore"
        return self.send_command(ROT_DISABLE, False)

    def rot_enable(self):
        "Abilita rotatore"
        return self.send_command(ROT_ENABLE, False)

    def rot_topar(self):
        "Muovi rotatore ad angolo parallattico"
        return self.send_command(ROT_TOPAR, False)

    def rot_reverse(self):
        "Inverte direzione movimento rotatore"
        return self.send_command(ROT_REVERS, False)

    def rot_sethome(self):
        "Imposta posizione corrente rotatore come HOME"
        return self.send_command(ROT_SETHOME, False)

    def rot_gohome(self):
        "Muovi rotatore a posizione home"
        return self.send_command(ROT_GOHOME, False)

    def rot_clkwise(self):
        "Muovi rotatore in senso orario (incremento prefissato)"
        return self.send_command(ROT_CLKWISE, False)

    def rot_cclkwise(self):
        "Muovi rotatore in senso antiorario (incremento prefissato)"
        return self.send_command(ROT_CCLKWISE, False)

    def rot_setincr(self, incr):
        "Imposta incremento per movimento rotatore (1:1 grado, 2:5 gradi, 3: 10 gradi)"
        if incr < 1:
            incr = 1
        elif incr > 3:
            incr = 3
        cmd = ROT_SETINCR%incr
        return self.send_command(cmd, False)

    def rot_setpos(self, deg):
        "Imposta posizione rotatore (gradi)"
        if deg >= 0:
            cmd = ROT_SETPOSP%(float2ums(deg))
        else:
            cmd = ROT_SETPOSN%(float2ums(deg))
        return self.send_command(cmd, 1)

    def rot_getpos(self):
        "Legge posizione rotatore (gradi)"
        ret = self.send_command(ROT_GET, True)
        return ddmmss_decode(ret)

    def set_antib_dec(self, stpar):
        "Imposta valore anti backlash declinazione (steps per arcsec)"
        return self.send_command(SET_ANTIB_DEC%stpar, True)

    def set_antib_ra(self, stpar):
        "Imposta valore anti backlash ascensione retta (steps per arcsec)"
        return self.send_command(SET_ANTIB_RA%stpar, True)

    def track_on(self):
        "Abilita tracking"
        return self.send_command(TRACK_ON, True)

    def track_off(self):
        "Disabilita tracking"
        return self.send_command(TRACK_OFF, True)

    def ontrack(self):
        "Abilita modo On Track"
        return self.send_command(ONTRACK, True)

    def track_rifraz_on(self):
        "Abilita correzione per rifrazione su tracking"
        return self.send_command(TRACKR_ENB, True)

    def track_rifraz_off(self):
        "Disabilita correzione per rifrazione su tracking"
        return self.send_command(TRACKR_DIS, True)

    def track_incr(self):
        "Incrementa tracking rate di 0.02 Hz"
        return self.send_command(TRACK_INCR, False)

    def track_decr(self):
        "Decrementa tracking rate di 0.02 Hz"
        return self.send_command(TRACK_DECR, False)

    def track_king(self):
        "Imposta tracking rate king"
        return self.send_command(TRACK_KING, False)

    def track_lunar(self):
        "Imposta tracking rate lunare"
        return self.send_command(TRACK_LUNAR, False)

    def track_sidereal(self):
        "Imposta tracking rate sidereo"
        return self.send_command(TRACK_SIDER, False)

    def track_solar(self):
        "Imposta tracking rate solare"
        return self.send_command(TRACK_SOLAR, False)

    def track_one(self):
        "Imposta tracking su singolo asse (disab. DEC tracking)"
        return self.send_command(TRACK_ONE, False)

    def track_two(self):
        "Imposta tracking sui due assi"
        return self.send_command(TRACK_TWO, False)

    def track_reset(self):
        "Riporta tracking rate sidereo a valore calcolato"
        return self.send_command(TRACK_RESET, False)

    def park(self):
        "Metti telescopio in stato PARK"
        return self.send_command(PARK, True)

    def reset_home(self):
        "Imposta posizione HOME"
        return self.send_command(SET_HOME, False)

    def goto_home(self):
        "Muovi telescopio a posizione HOME"
        return self.send_command(GOTO_HOME, False)

    def set_park(self):
        "Imposta posizione PARK"
        return self.send_command(SET_PARK, False)

    def unpark(self):
        "Metti telescopio operativo (UNPARK)"
        return self.send_command(UNPARK, True)

    def gen_cmd(self, text):
        "Invia comando generico (:, # possono essere omessi)"
        if not text.startswith(":"):
            text = ":"+text
        if not text.endswith("#"):
            text += "#"
        return self.send_command(text, True)

    def opc_init(self):
        "Invia comandi di inizializzazione per telescopio OPC"
        ret1 = self.set_lat(OPC.lat_deg)
        ret2 = self.set_lon(-OPC.lon_deg)  # Convenzione OnStep !!!
        ret3 = self.set_time()
        ret4 = self.set_date()
        try:
            ret = ret1+ret2+ret3+ret4
        except TypeError:
            ret = None
        return ret

########################################################

def getddmmss(args):
    "[dd [mm [ss]]]"
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
    "[nnnn]"
    if args:
        return int(args[0])
    return None

def getfloat(args):
    "[n.nnn]"
    if args:
        return float(args[0])
    return None

def getword(args):
    "[aaaa]"
    if args:
        return args[0]
    return None

def noargs(*_unused):
    " "
    return None

def _print_cmd(cmdict):
    "Visualizza comandi in elenco"
    keys = list(cmdict.keys())
    keys.sort()
    for key in keys:
        print("   %3s: %s %s"%(key, cmdict[key][0].__doc__, cmdict[key][1].__doc__))

def myexit():
    "Termina programma"
    sys.exit()

def gos_info(cset=""):
    "Mostra  tabella dei codici per interrogazioni valori OnStep"
    cset = cset.upper()
    if cset == "0":
        print(CODICI_ONSTEP_0X)
    elif cset == "8":
        print(CODICI_ONSTEP_8X)
    elif cset == "9":
        print(CODICI_ONSTEP_9X)
    elif cset == "E":
        print(CODICI_ONSTEP_EX)
    elif cset == "F":
        print(CODICI_ONSTEP_FX)
    elif cset == "G":
        print(CODICI_ONSTEP_GX)
    elif cset == "U":
        print(CODICI_ONSTEP_UX)
    else:
        print("Seleziona tabella specifica:")
        print(CODICI_TABELLE_ONSTEP)
    return ""

def trk_info():
    "Informazioni sulle variabili concernenti il tracking"
    print(TRACKING_INFO)
    return ""

def gst_info():
    "Mostra  tabella dei codici di stato"
    print("Tabella codici di stato da comando gst")
    print()
    for schr, text in CODICI_STATO.items():
        print(" %s: %s"%(schr, text))
    return ""

def mvt_info():
    "Mostra  codici risposta da comando move to target"
    print("Tabella codici di risposta da comando move to")
    print()
    print(CODICI_RISPOSTA)
    return ""

class Executor:
    "Esecuzione comandi interattivi"
    def __init__(self, config, verbose):
        dcom = TeleCommunicator(config["tel_ip"], config["tel_port"], verbose=verbose)
#                    codice   funzione      convers.argom.
        self.lxcmd = {"f1+": (dcom.move_foc1_in, noargs),
                      "f2+": (dcom.move_foc2_in, noargs),
                      "f1-": (dcom.move_foc1_out, noargs),
                      "f2-": (dcom.move_foc2_out, noargs),
                      "f1a": (dcom.get_foc1_act, noargs),
                      "f2a": (dcom.get_foc2_act, noargs),
                      "f1b": (dcom.set_foc1_abs, getint),
                      "f2b": (dcom.set_foc2_abs, getint),
                      "f1f": (dcom.set_foc1_fast, noargs),
                      "f2f": (dcom.set_foc2_fast, noargs),
                      "f1i": (dcom.get_foc1_min, noargs),
                      "f2i": (dcom.get_foc2_min, noargs),
                      "f1l": (dcom.set_foc1_slow, noargs),
                      "f2l": (dcom.set_foc2_slow, noargs),
                      "f1m": (dcom.get_foc1_max, noargs),
                      "f2m": (dcom.get_foc2_max, noargs),
                      "f1p": (dcom.get_foc1_pos, noargs),
                      "f2p": (dcom.get_foc2_pos, noargs),
                      "f1q": (dcom.stop_foc1, noargs),
                      "f2q": (dcom.stop_foc2, noargs),
                      "f1r": (dcom.set_foc1_rel, getint),
                      "f2r": (dcom.set_foc2_rel, getint),
                      "f1s": (dcom.foc1_sel, getint),
                      "f2s": (dcom.foc2_sel, getint),
                      "f1t": (dcom.get_foc1_stat, noargs),
                      "f2t": (dcom.get_foc2_stat, noargs),
                      "f1v": (dcom.set_foc1_speed, getint),
                      "f2v": (dcom.set_foc2_speed, getint),
                      "f1z": (dcom.move_foc1_zero, noargs),
                      "f2z": (dcom.move_foc2_zero, noargs),
                      "gad": (dcom.get_antib_dec, noargs),
                      "gar": (dcom.get_antib_ra, noargs),
                      "gat": (dcom.get_alt, noargs),
                      "gda": (dcom.get_date, noargs),
                      "gdt": (dcom.get_current_de, noargs),
                      "gdo": (dcom.get_target_de, noargs),
                      "gfd": (dcom.get_fmwdate, noargs),
                      "gfi": (dcom.get_fmwnumb, noargs),
                      "gfn": (dcom.get_fmwname, noargs),
                      "gft": (dcom.get_fmwtime, noargs),
                      "ggm": (dcom.get_genmsg, noargs),
                      "gla": (dcom.get_lat, noargs),
                      "gli": (dcom.get_hlim, noargs),
                      "glo": (dcom.get_lon, noargs),
                      "glt": (dcom.get_ltime, noargs),
                      "glb": (dcom.get_pside, noargs),
                      "glh": (dcom.get_olim, noargs),
                      "gmo": (dcom.get_db, noargs),
                      "gro": (dcom.get_target_ra, noargs),
                      "grt": (dcom.get_current_ra, noargs),
                      "gsm": (dcom.get_mstat, noargs),
                      "gst": (dcom.gst_print, noargs),
                      "gte": (dcom.get_temp, getint),
                      "gtf": (dcom.get_timefmt, noargs),
                      "gtn": (dcom.get_ntemp, noargs),
                      "gtr": (dcom.get_trate, noargs),
                      "gts": (dcom.get_tsid, noargs),
                      "guo": (dcom.get_utcoffset, noargs),
                      "gzt": (dcom.get_az, noargs),
                      "hom": (dcom.goto_home, noargs),
                      "mve": (dcom.move_east, noargs),
                      "mvo": (dcom.move_west, noargs),
                      "mvn": (dcom.move_north, noargs),
                      "mvs": (dcom.move_south, noargs),
                      "mvt": (dcom.move_target, noargs),
                      "par": (dcom.park, noargs),
                      "pge": (dcom.pulse_guide_est, getint),
                      "pgo": (dcom.pulse_guide_west, getint),
                      "pgn": (dcom.pulse_guide_north, getint),
                      "pgs": (dcom.pulse_guide_south, getint),
                      "ren": (dcom.rot_enable, noargs),
                      "rdi": (dcom.rot_disable, noargs),
                      "rpa": (dcom.rot_topar, noargs),
                      "rrv": (dcom.rot_reverse, noargs),
                      "rsh": (dcom.rot_sethome, noargs),
                      "rho": (dcom.rot_gohome, noargs),
                      "rcw": (dcom.rot_clkwise, noargs),
                      "rcc": (dcom.rot_cclkwise, noargs),
                      "rsi": (dcom.rot_setincr, getint),
                      "rsp": (dcom.rot_setpos, getddmmss),
                      "rge": (dcom.rot_getpos, noargs),
                      "sad": (dcom.set_antib_dec, getint),
                      "sar": (dcom.set_antib_ra, getint),
                      "sho": (dcom.reset_home, noargs),
                      "sla": (dcom.set_lat, getddmmss),
                      "spa": (dcom.set_park, noargs),
                      "stp": (dcom.stop, noargs),
                      "ste": (dcom.stop_east, noargs),
                      "sti": (dcom.set_time, noargs),
                      "sto": (dcom.stop_west, noargs),
                      "stn": (dcom.stop_north, noargs),
                      "sts": (dcom.stop_south, noargs),
                      "srt": (dcom.set_rate, getword),
                      "sda": (dcom.set_date, noargs),
                      "sdo": (dcom.set_de, getddmmss),
                      "sal": (dcom.set_alt, getddmmss),
                      "saz": (dcom.set_az, getddmmss),
                      "smn": (dcom.set_min_alt, getint),
                      "smx": (dcom.set_max_alt, getint),
                      "slo": (dcom.set_lon, getddmmss),
                      "sro": (dcom.set_ra, getddmmss),
                      "std": (dcom.set_tsid, noargs),
                      "syn": (dcom.sync_radec, noargs),
                      "trs": (dcom.set_trate, getfloat),
                      "tof": (dcom.track_off, noargs),
                      "ton": (dcom.track_on, noargs),
                      "tot": (dcom.ontrack, noargs),
                      "trn": (dcom.track_rifraz_on, noargs),
                      "trf": (dcom.track_rifraz_off, noargs),
                      "t+":  (dcom.track_incr, noargs),
                      "t-":  (dcom.track_decr, noargs),
                      "tki": (dcom.track_king, noargs),
                      "tlu": (dcom.track_lunar, noargs),
                      "tsi": (dcom.track_sidereal, noargs),
                      "tso": (dcom.track_solar, noargs),
                      "tr1": (dcom.track_one, noargs),
                      "tr2": (dcom.track_two, noargs),
                      "tre": (dcom.track_reset, noargs),
                      "unp": (dcom.unpark, noargs),
                     }
        self.spcmd = {"gos": (dcom.get_onstep_value, getword),
                      "x00": (dcom.set_onstep_00, getint),
                      "x01": (dcom.set_onstep_01, getint),
                      "x02": (dcom.set_onstep_02, getint),
                      "x03": (dcom.set_onstep_03, getint),
                      "x04": (dcom.set_onstep_04, getint),
                      "x05": (dcom.set_onstep_05, getint),
                      "x06": (dcom.set_onstep_06, getint),
                      "x07": (dcom.set_onstep_07, getint),
                      "x08": (dcom.set_onstep_08, getint),
                      "x92": (dcom.set_onstep_92, getint),
                      "x93": (dcom.set_onstep_93, getint),
                      "x95": (dcom.set_onstep_95, getint),
                      "x96": (dcom.set_onstep_96, getword),
                      "x97": (dcom.set_onstep_97, getint),
                      "x98": (dcom.set_onstep_98, getint),
                      "x99": (dcom.set_onstep_99, getint),
                      "xe9": (dcom.set_onstep_e9, getint),
                      "xea": (dcom.set_onstep_ea, getint),
                     }
        self.hkcmd = {"q": (myexit, noargs),
                      "?": (self.search, getword),
                      "gos?": (gos_info, getword),
                      "gha": (dcom.get_current_ha, noargs),
                      "gst?": (gst_info, noargs),
                      "mvt?": (mvt_info, noargs),
                      "ini": (dcom.opc_init, noargs),
                      "cmd": (dcom.gen_cmd, getword),
                      "fmw": (dcom.get_firmware, noargs),
                      "ver": (dcom.set_verbose, noargs),
                     }
    def search(self, word=""):
        "Cerca comando contenente la parola"
        wsc = word.lower()
        allc = self.lxcmd.copy()
        allc.update(self.hkcmd)
        allc.update(self.spcmd)
        found = {}
        for key, value in allc.items():
            descr = value[0].__doc__
            if descr and wsc in descr.lower():
                found[key] = value
        _print_cmd(found)
        return ""

    def execute(self, command):
        "Esegue comando interattivo"
        cmdw = command.split()
        if not cmdw:
            return "Nessun comando"
        cmd0 = cmdw[0][:4].lower()
        clist = self.lxcmd
        cmd_spec = clist.get(cmd0)
        if not cmd_spec:
            clist = self.hkcmd
            cmd_spec = clist.get(cmd0)
        if not cmd_spec:
            clist = self.spcmd
            cmd_spec = clist.get(cmd0)
        if cmd_spec:
            the_arg = cmd_spec[1](cmdw[1:])
            if the_arg is not None:
                ret = cmd_spec[0](the_arg)
            else:
                try:
                    ret = cmd_spec[0]()
                except TypeError:
                    ret = "Argomento mancante"
            if ret is None:
                ret = "Nessuna risposta"
        else:
            ret = "Comando sconosciuto!"
        return ret

    def usage(self):
        "Visualizza elenco comandi"
        print("\nComandi LX200 standard:")
        _print_cmd(self.lxcmd)
        print("\nComandi speciali:")
        _print_cmd(self.spcmd)
        print("\nComandi aggiuntivi:")
        _print_cmd(self.hkcmd)

def main():
    "Invio comandi da console e test"
    if '-h' in sys.argv:
        print(get_version())
        print(__doc__)
        sys.exit()

    if '-V' in sys.argv:
        print(get_version())
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
        answ = input("\nComando (invio per aiuto): ")
        if answ:
            ret = exe.execute(answ)
            print(ret)
        else:
            exe.usage()

if __name__ == "__main__":
    import readline
    main()
