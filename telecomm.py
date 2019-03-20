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
SET_DATE = ":SC%02d/%02d/%02d#" # Set data
SET_DE = ":Sd%s%02d*%02d:%02d#" # Set declinazione target (dd,mm,ss)
SET_LAT = ":St%s%02d*%02d#"     # Set latitudine del luogo (dd, mm)
SET_LON = ":Sg%03d*%02d#"       # Set longitudine del luogo (ddd, mm)
SET_LTIME = ":SL%02d:%02d:%02d#"# Set ora locale: hh, mm, ss
SET_RA = ":Sr%02d:%02d:%02d#"   # Set ascensione retta dell'oggetto target (hh,mm,ss)
SET_TRATE = ":ST%08.5f#"        # Set freq. di tracking (formato da commenti nel codice)
SET_TSID = ":SS%02d:%02d:%02d#" # Set tempo sidereo: hh, mm, ss
SET_UOFF = ":SG%s%04.1f#"       # Set UTC offset (UTC = LocalTime+Offset)

TRACK_ON = ":Te#"               # Abilita tracking
TRACK_OFF = ":Td#"              # Disabilita tracking
ONTRACK = ":To#"                # Abilita "On Track"
TRACKR_ENB = ":Tr#"             # Abilita tracking con rifrazione
TRACKR_DIS = ":Tn#"             # Disabilita tracking con rifrazione
                                # return: 0 failure, 1 success
TRACK_INCR = ":T+#"             # Incr. master sidereal clock di 0.02 Hz (stored in EEPROM)
TRACK_DECR = ":T-#"             # Decr. master sidereal clock di 0.02 Hz (stored in EEPROM)
TRACK_KING = ":TK#"             # Tracking rate = king (include rifrazione)
TRACK_LUNAR = ":TL#"            # Tracking rate = lunar
TRACK_SIDER = ":TQ#"            # Tracking rate = sidereal
TRACK_SOLAR = ":TS#"            # Tracking rate = solar
TRACK_RESET = ":TR#"            # Reset master sidereal clock
                                # return:  None
TRACK_ONE = ":T1#"              # Track singolo asse (Disabilita Dec tracking)
TRACK_TWO = ":T2#"              # Track due assi

                                # Comandi di movimento
MOVE_TO = ":MS#"                # Muovi a target definito
MOVE_DIR = ":M%s#"              # Muovi ad est/ovest/nord/sud
STOP_DIR = ":Q%s#"              # Stop movimento ad est/ovest/nord/sud
STOP = ":Q#"                    # Stop

PULSE_M = "Mg%s%d#"             # Pulse move              < TBD

PARK = ":hP#"                   # Park telescope
STOP = ":Q#"                    # stop telescope
UNPARK = ":hR#"                 # Unpark telescope

SYNC_RADEC = ":CS#"        # Sync with current RA/DEC (no reply)

                           # Comandi informativi
GET_AZ = ":GZ#"            # Get telescope azimuth
GET_ALT = ":GA#"           # Get telescope altitude
GET_CUR_DE = ":GD#"        # Get current declination
GET_CUR_RA = ":GR#"        # Get current right ascension
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


CODICI_STATO = """
    n: non in tracking    N: Non in slewing
    p: Non in park, P: in park  I: in movimento verso partk, F: park fallito
    R: I dati PEC data sono stati registrati
    H: in posizione home
    S: PPS sincronizzato
    G: Modo guida attivo
    f: Errore movimenjto asse
    r: PEC refr abilitato    s: su asse singolo (solo equatoriale)
    t: on-track abilitato    s: su asse singolo (solo equatoriale)
    w: in posizione home     u: Pausa in pos. home abilitata
    z: cicalino abiulitato
    a: Inversione al meridiano automatica
    /: Stato pec: ignora
    ,: Stato pec: prepara disposizione 
    ~: Stato pec: disposizione  in corso
    ;: Stato pec: preparazione alla registrazione
    ^: Stato pec: registrazione in corso
    .: PEC segnala detezione indice dall'ultima chiamata
    E: Montatura equatoriale  tedescsa
    K: Montatura equatoriale a forcella
    k: Montatura altaz a forcella
    A: Montatura altaz
    o: lato braccio ignoto  T: lato est   W: lato ovest
    0-9: Ultimo codice di errore
"""

CODICI_RISPOSTA = """
    0: movimento possibile
    1: oggetto sotto orizzonte
    2: oggetto non selezionato
    4: posizione irraggiungibile (non unparked)
    5: già in movimento
    6: oggetto sopra limite zenith
"""

CODICI_ONSTEP = """
0x: Modello allineamento
  00:  ax1Cor
  01:  ax2Cor
  02:  altCor
  03:  azmCor
  04:  doCor
  05:  pdCor
  06:  ffCor
  07:  dfCor
  08:  tfCor
  09:  Number of stars, reset to first star
  0A:  Star  #n HA
  0B:  Star  #n Dec
  0C:  Mount #n HA
  0D:  Mount #n Dec
  0E:  Mount PierSide (and increment n)

4x: Encoder
  40:  Get formatted absolute Axis1 angle
  41:  Get formatted absolute Axis2 angle 
  42:  Get absolute Axis1 angle in degrees
  43:  Get absolute Axis2 angle in degrees
  49:  Get current tracking rate

8x: Data e ora
  80:  UTC time
  81:  UTC date

9x: Varie
  90:  pulse-guide rate
  91:  pec analog value
  92:  MaxRate
  93:  MaxRate (default)
  94:  pierSide (E, W, N:none)
  95:  autoMeridianFlip
  96:  preferred pier side  (E, W, N:none)
  97:  slew speed
  98:  Rotatror mode (D: derotate, R:rotate, N:no rotator)
  9A:  temperature in deg. C
  9B:  pressure in mb
  9C:  relative humidity in %
  9D:  altitude in meters
  9E:  dew point in deg. C
  9F:  internal MCU temperature in deg. C

Ux: Stato motori step
  U1: ST(Stand Still),  OA(Open Load A), OB(Open Load B), GA(Short to Ground A),
  U2: GB(Short to Ground B), OT(Overtemperature Shutdown 150C),
      PW(Overtemperature Pre-warning 120C)

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
  FE:  DebugE, equatorial coordinates degrees (no division by 15)

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

    def set_de(self, deg):
        "Imposta declinazione oggetto (gradi)"
        if deg >= -90. and deg <= 90.:
            sgn = "+" if deg >= 0 else "-"
            deg = abs(deg)
            cmd = SET_DE%((sgn,)+float2ums(deg))
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
            sgn = "+"
        else:
            sgn = "-"
            deg = -deg
        cmd = SET_LAT%((sgn,)+float2ums(deg)[:2])
        return self.send_command(cmd, 1)

    def set_lon(self, deg):
        "Imposta longitudine locale (gradi)"
        cmd = SET_LON%(float2ums(deg)[:2])
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

    def sync_radec(self):
        "Sync con valore corrente asc.retta e decl."
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
        return self.send_command(STOP_DIR%"", False)

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
        "Leggi altgezza telescopio (gradi)"
        ret = self.send_command(GET_ALT, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_az(self):
        "Leggi azimuth telescopio (gradi)"
        ret = self.send_command(GET_AZ, True)
        return ddmmss_decode(ret)

    def get_current_de(self):
        "Leggi declinazione telescopio (gradi)"
        ret = self.send_command(GET_CUR_DE, True)
        return ddmmss_decode(ret, with_sign=True)

    def get_current_ra(self):
        "Leggi ascensione retta telescopio (ore)"
        ret = self.send_command(GET_CUR_RA, True)
        return ddmmss_decode(ret)

    def get_date(self):
        "Leggi data impostata al telescopio"
        ret = self.send_command(GET_DATE, True)
        return ret

    def get_hlim(self):
        "Leggi limite orizzonte (gradi)"
        ret = self.send_command(GET_HLIM, True)
        return ret

    def get_olim(self):
        "Leggi limite overhead (gradi)"
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
        cmd = GET_OSVALUE.replace("..", value)
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

    def get_status(self):
        "Leggi stato telescopio. Per tabella stati: gst?"

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
        "Metti telescopio in Park"
        return self.send_command(PARK, True)

    def unpark(self):
        "Metti telescope in Unpark"
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

def gos_info():
    "Mostra  tabella dei codici per interrogazioni valori OnStep"
    print("Tabella codici di interrogazione per comando gos")
    print()
    print(CODICI_ONSTEP)
    return ""

def gst_info():
    "Mostra  tabella dei codici di stato"
    print("Tabella codici di stato da comando gst")
    print()
    print(CODICI_STATO)
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
        self.lxcmd = {"gat": (dcom.get_alt, noargs),
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
                      "gos": (dcom.get_onstep_value, getword),
                      "gro": (dcom.get_target_ra, noargs),
                      "grt": (dcom.get_current_ra, noargs),
                      "gsm": (dcom.get_mstat, noargs),
                      "gst": (dcom.get_status, noargs),
                      "gtf": (dcom.get_timefmt, noargs),
                      "gtr": (dcom.get_trate, noargs),
                      "gts": (dcom.get_tsid, noargs),
                      "guo": (dcom.get_utcoffset, noargs),
                      "gzt": (dcom.get_az, noargs),
                      "par": (dcom.park, noargs),
                      "unp": (dcom.unpark, noargs),
                      "pge": (dcom.pulse_guide_est, getint),
                      "pgo": (dcom.pulse_guide_west, getint),
                      "pgn": (dcom.pulse_guide_north, getint),
                      "pgs": (dcom.pulse_guide_south, getint),
                      "mve": (dcom.move_east, noargs),
                      "mvo": (dcom.move_west, noargs),
                      "mvn": (dcom.move_north, noargs),
                      "mvs": (dcom.move_south, noargs),
                      "mvt": (dcom.move_target, noargs),
                      "stp": (dcom.stop, noargs),
                      "ste": (dcom.stop_east, noargs),
                      "sto": (dcom.stop_west, noargs),
                      "stn": (dcom.stop_north, noargs),
                      "sts": (dcom.stop_south, noargs),
                      "srt": (dcom.set_rate, getword),
                      "sda": (dcom.set_date, noargs),
                      "sdo": (dcom.set_de, getddmmss),
                      "slo": (dcom.set_lon, getddmmss),
                      "sro": (dcom.set_ra, getddmmss),
                      "std": (dcom.set_tsid, noargs),
                      "syn": (dcom.sync_radec, noargs),
                      "trs": (dcom.set_trate, getfloat),
                      "sla": (dcom.set_lat, getddmmss),
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
                      "set": (dcom.set_time, noargs),
                     }
        self.hkcmd = {"q": (myexit, noargs),
                      "?": (self.search, getword),
                      "gos?": (gos_info, noargs),
                      "gst?": (gst_info, noargs),
                      "mvt?": (mvt_info, noargs),
                      "ini": (dcom.opc_init, noargs),
                      "cmd": (dcom.gen_cmd, getword),
                      "fmw": (dcom.get_firmware, noargs),
                      "ver": (dcom.set_verbose, noargs),
                     }
    def search(self, word):
        "Cerca comando contenente la parola"
        wsc = word.lower()
        allc = self.lxcmd.copy()
        allc.update(self.hkcmd)
        found = {}
        for key, value in allc.items():
            descr = value[0].__doc__
            if wsc in descr.lower():
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
        if cmd_spec:
            the_arg = cmd_spec[1](cmdw[1:])
            if the_arg is not None:
                ret = cmd_spec[0](the_arg)
            else:
                ret = cmd_spec[0]()
            if ret is None:
                ret = "Nessuna risposta"
        else:
            ret = "Comando sconosciuto!"
        return ret

    def usage(self):
        "Visualizza elenco comandi"
        print("\nComandi per telescopio OPC:")
        _print_cmd(self.lxcmd)
        print("\nComandi aggiuntivi:")
        _print_cmd(self.hkcmd)

TODO = """
Sync. with current target RA/Dec	:CM#	Reply: N/A#

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
        answ = input("\nComando (invio per aiuto): ")
        if answ:
            ret = exe.execute(answ)
            print(ret)
        else:
            exe.usage()

if __name__ == "__main__":
    import readline
    main()
