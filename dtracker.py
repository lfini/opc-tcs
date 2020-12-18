#!/usr/bin/python3
"""
OPC - Asservimento cupola [%s]

Uso:
        python3 dtracker.py [-s] [-h] [-v]

Dove:
       -h  Mostra questa pagina ed esce
       -s  Si connette al simulatore con IP: 127.0.0.1, Port: 9752
       -v  Scrive numero di versione
"""
import sys
import os.path
import time
import math

from tkinter import Tk, Button, Entry, Frame, Label, Checkbutton, IntVar, PhotoImage
from tkinter import DISABLED, E, END, LEFT, NORMAL, RIDGE, W, X
from widgets import WarningMsg, Field, Number, Coord, Led, ToolTip
from widgets import HSpacer, Controller, BD_FONT, H3_FONT

from telecomm import TeleCommunicator
import configure
from interpolator import Interpolator

__author__ = "Luca Fini"
__version__ = "1.2"
__date__ = "Dicembre 2020"

try:
    import win32com.client as wcl
    from pywintypes import com_error as COM_ERROR
    SIMULATED_ASCOM = False
except ModuleNotFoundError:
    import ascom_fake as wcl
    COM_ERROR = Exception("Fake exception")
    print("Using ASCOM_FAKE !!!", file=sys.stderr)
    SIMULATED_ASCOM = True

UPDATE_TRACKER = 2000   # Periodo aggiornamento in modo tracker (ms)

BG_SUSPEND = "cyan"
BG_SUSPEND_ACT = "cyan3"
BG_RESUME = "yellow"
BG_RESUME_ACT = "yellow3"

BR_EAST = "E"
BR_WEST = "W"
SIDES = "EW"

FLOAT_NAN = float("nan")

NO_CONFIG = """
  File di configurazione mancante

  Può essere creato con "configure.py"
"""

INTERP_E = Interpolator(side="e")
INTERP_W = Interpolator(side="w")

LEFT_ARROW_DATA = """
R0lGODdhFAAUAOeeAAAAAAABAQEBAAABBQABBgMEBgAFDAMFCAUHCAEJFAYJDgcLEgMMGQsNEAEQ
IgoPFgoQGQITKAUTJwQUKA4WHg8YJAoZLRIcKBUcJRQdJw0fNxAlQRgmORsmMx4qOiAtPiUwPR0y
TiQzSCM3Tyo4SyI6Wiw+VC1EZDVEWDdHXjxMYTdOajdRcj1TbT1Wd0dac01edUtjgVJid2RkZGZm
ZlNphWdnZ2pqalNukVVukFxwiVtzkWNzhnV1dWl3iml5jmR6lHl5eXt7e3x8fH19fX5+fn9/f4CA
gG2Dn3CDmoGBgYKCgnqGloWFhXKIpHWKpX+JmHiLon6MnYuLi4GQpIKSqISYsoyZqo+ZpZCbqY2c
sJScpZGerZOfrpChtJ2jq5qksJylr6GmrZ+otKCptKKqtaWqsqarsaastKysrK2trauusayusKmv
tqyvsqyvs6+wsq2xt6+xtLCxs62yuLGysrGys7KysrOysrKztLOzsrOzs7SzsrSzs7G0t7S0tLW0
srS0tbW0s7O1tre1s7a2tbe2s7e2tLi2tLi3tbm3tLi4uLy5try6uL+/v8DAwMHBwcLCwsPDw8jI
yM3Nzc7Ozs/Pz9HR0dra2tvb29zc3N3d3d7e3t/f3///////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////ywAAAAAFAAUAAAIqwAxbRpI
sKBBgos2TVrIsKHDhYuKcHJ0p6LFixjvbJFIMSPGPV/6aOTo8aIYGyAKjZxY8k6aIBAAdFC5kWVG
OE08ANg5c2VHi3WmkNhJtGfNn3m2qCDK1CjJO19mFGDalOZTpQGoFrVq846dKSi0yuT6syJOEFSd
dr3IRkiGrT5bnulhYGzcllBnqC1bcs8WkUfxZqwJZ4vhw4gTb5lSpNERJZAjS56s5EiPgAA7
"""

HOMEDIR = os.path.expanduser("~")
class GLOB:           # pylint: disable=R0903
    "globals senza usare global"
    config = {}
    goon = False
    error = ""
    dome = None
    root = None
    dome_pos_error = None
    dome_crit = None

def get_tel(telcom):
    "Legge posizione telescopio"
    ha_h = telcom.get_current_ha()
    de_d = telcom.get_current_de()
    side = telcom.get_pside()
    if ha_h is None or de_d is None or side is None:
        time.sleep(0.3)
        if ha_h is None:
            ha_h = telcom.get_current_ha()
        elif de_d is None:
            de_d = telcom.get_current_de()
        elif side is None:
            side = telcom.get_pside()
    if ha_h is None or de_d is None or side is None:
        return None
    return ha_h, de_d, side[0]

def dome_azimuth(ha_h, de_d, side):
    "Calcola azimuth cupola da coordinate telescopio"
    GLOB.error = ""
    if side == BR_EAST:
        az_deg = INTERP_E.interpolate(ha_h, de_d)
    elif side == BR_WEST:
        az_deg = INTERP_W.interpolate(ha_h, de_d)
    else:
        GLOB.error = "ERR: Pier side (%s)"%side
        return None
    if math.isnan(az_deg):
        GLOB.error = "ERR: Interpolazione (ha:%.2f, de:%.2f)"%(ha_h, de_d)
        az_deg = None
    return az_deg

class DTracker(Frame):            # pylint: disable=R0901,R0902
    "Widget per asservimento cupola"
    def __init__(self, parent, logging=False):
        super().__init__(parent)
        self._leftarrow = PhotoImage(data=LEFT_ARROW_DATA)
        self.tel = TeleCommunicator(GLOB.config["tel_ip"], GLOB.config["tel_port"])
        top_fr = Frame(self, pady=4)
        Label(top_fr, text="  Telescopio ", font=H3_FONT).grid(row=1, column=1)
        tel_fr = Frame(top_fr)
        Label(tel_fr, text=" HA(h): ").pack(side=LEFT)
        self.tel_ha = Coord(tel_fr)
        self.tel_ha.pack(side=LEFT)
        self.tel_ha.widget.config(font=BD_FONT)
        Label(tel_fr, text="   DE(d): ").pack(side=LEFT)
        self.tel_de = Coord(tel_fr)
        self.tel_de.pack(side=LEFT)
        self.tel_de.widget.config(font=BD_FONT)
        Label(tel_fr, text="   Lato: ").pack(side=LEFT)
        self.tside = Label(tel_fr, text="", width=3, bg="black", fg="lightgreen", font=BD_FONT)
        self.tside.pack(side=LEFT)
        HSpacer(tel_fr, 3).pack(side=LEFT)
        ins_fr = Frame(tel_fr, border=2, relief=RIDGE)
        Label(ins_fr, text=" Insegui: ", font=BD_FONT).pack(side=LEFT)
        self._slave = IntVar(self)
        Checkbutton(ins_fr, variable=self._slave, command=self.tog_slave).pack(side=LEFT)
        ins_fr.pack(side=LEFT)
        ToolTip(ins_fr, text="Seleziona per attivare inseguimento")
        self._slave = 0
        HSpacer(tel_fr, 1).pack(side=LEFT)
        tel_fr.grid(row=1, column=2, ipady=4, sticky=W)
        self.tel_led = Led(top_fr, size=20)
        self.tel_led.grid(row=1, column=3)
        ToolTip(self.tel_led, text="Comunicazione con telescopio")
        Label(top_fr, text="  Cupola ", font=H3_FONT).grid(row=3, column=1, sticky=E)
        dome_fr = Frame(top_fr)
        Label(dome_fr, text="  Az(d): ").pack(side=LEFT)
        self.dome_az = Number(dome_fr, fmt="%.1f", width=6)
        self.dome_az.pack(side=LEFT)
        self.dome_az.widget.config(font=BD_FONT)
        Label(dome_fr, text="   Mov: ").pack(side=LEFT)
        self.dome_mov = Field(dome_fr, width=6)
        self.dome_mov.pack(side=LEFT)
        Label(dome_fr, text="   Tgt(d): ").pack(side=LEFT)
        self.trgt_az = Number(dome_fr, width=6, fmt="%.1f")
        self.trgt_az.pack(side=LEFT)
        self.trgt_az.widget.config(font=BD_FONT)
        Led(dome_fr, border=0, size=4).pack(side=LEFT)  # solo un piccolo spazio
        self.attgt_led = Led(dome_fr, size=15)
        self.attgt_led.pack(side=LEFT)
        ToolTip(self.attgt_led, text="Posizione raggiunta")
        HSpacer(dome_fr, 2).pack(side=LEFT)
        self.arrowb = Button(dome_fr, image=self._leftarrow, padx=0, pady=0,
                             border=0, command=self.set_target)
        self.arrowb.pack(side=LEFT)
        ToolTip(self.arrowb, text="Imposta azimuth")
        self.val_target = Entry(dome_fr, width=6)
        self.val_target.pack(side=LEFT)
        self.offset = Controller(dome_fr, label="   Ofs:", lower=-5, upper=5, label_font=BD_FONT,
                                 step=0.5, width=3, fmt="%.1f", mode="plus")
        self.offset.pack(side=LEFT)
        ToolTip(self.offset, text="Offset posizione cupola")
        HSpacer(dome_fr).pack(side=LEFT)
        dome_fr.grid(row=3, column=2, sticky=W+E, ipady=4)
        self.dome_led = Led(top_fr, size=20)
        self.dome_led.grid(row=3, column=3)
        ToolTip(self.dome_led, text="Comunicazione con cupola")
        Label(top_fr, text=" ").grid(row=1, column=4)
        Frame(top_fr, border=3, relief=RIDGE, bg="black").grid(row=2, column=1,
                                                               columnspan=4, sticky=W+E)
        top_fr.pack()
        self.stline = Label(self, text="", border=2, relief=RIDGE, bg="white")
        self.stline.pack(expand=1, fill=X)
        bot_fr = Frame(self)
        self.log_stat = IntVar(self)
        log_fr = Frame(bot_fr, border=2, relief=RIDGE)
        Label(log_fr, text=" Logging: ").pack(side=LEFT)
        Checkbutton(log_fr, variable=self.log_stat, command=self.tog_logger).pack(side=LEFT)
        log_fr.pack(side=LEFT)
        ToolTip(log_fr, text="Abilita/disabilita logging")
        HSpacer(bot_fr).pack(side=LEFT)
        self.parkb = Button(bot_fr, text="Park", width=5, command=self.park)
        self.parkb.pack(side=LEFT)
        self.homeb = Button(bot_fr, text="Home", width=5, command=self.findhome)
        self.homeb.pack(side=LEFT)
        HSpacer(bot_fr, 3).pack(side=LEFT)
        self.syncb = Button(bot_fr, text="Sync", width=5, command=self.sync)
        self.syncb.pack(side=LEFT)
        self.sync_val = Entry(bot_fr, width=5)
        self.sync_val.pack(side=LEFT)
        HSpacer(bot_fr, 1).pack(side=LEFT)
        bot_fr.pack(expand=1, fill=X, ipady=4)
        self.target_az = None
        self.at_target = False
        self.logfile = None
        self.set_manual_butts(True)
        if logging:
            self.start_logger()
        else:
            self.stop_logger()
        self.update()

    def move_dome(self, target):
        "Movimento cupola"
        azm = GLOB.dome.Azimuth
        slw = GLOB.dome.Slewing
        if (target is None) or slw:
            return azm, slw
        dist = target-azm
        if dist > 180.:
            dist -= 360.
        elif dist < -180.:
            dist += 360.
        adist = abs(dist)
        self.at_target = False
        if adist > GLOB.dome_maxerr:
            if adist < GLOB.dome_crit:
                mod_target = (target-adist/2) if dist > 0 else (target+adist/2)
                mod_target %= 360
            else:
                mod_target = target
            self.log_mark("CMD SlewToAzimuth(%.2f)"%mod_target)
            GLOB.dome.SlewToAzimuth(mod_target)
        else:
            self.at_target = True
        return azm, slw

    def set_target(self):
        "Imposta posizione target"
        fld = self.val_target.get()
        self.offset.set(0)
        if fld:
            self.log_mark("GOTO "+fld)
            self.target_az = float(fld)
        else:
            self.target_az = None
            self.log_mark("Annulla goto")
        self.val_target.delete(0, END)

    def log_mark(self, text):
        "Inserisce un commento nel logfile"
        if self.logfile is None:
            return
        print("# %.2f -"%time.time(), text, file=self.logfile)

    def tog_logger(self):
        "Server per bottone logon/logoff"
        if self.logfile:
            self.stop_logger()
        else:
            self.start_logger()

    def start_logger(self):
        "Abilita logging dei dati"
        logname = os.path.join(HOMEDIR, time.strftime("%Y-%m-%d-dtracker.log"))
        self.logfile = open(logname, "a")
        self.log_mark("Log attivato - "+time.strftime("%Y-%m-%d %H:%M:%S"))
        self.log_mark("Periodo aggiornamento: %d (ms)"%UPDATE_TRACKER)
        self.log_mark("Max errore di tracking: %.2f (gradi)"%GLOB.dome_maxerr)
        self.log_mark("Zona critica tracking %.2f (gradi)"%GLOB.dome_crit)
        self.log_mark("tempo slewing posizione obiettivo   HA    DEC   lato")
        self.log_stat.set(1)

    def stop_logger(self):
        "disabilita logging dei dati"
        if self.logfile is not None:
            self.log_mark("Log disattivato - "+time.strftime("%Y-%m-%d %H:%M:%S"))
            self.logfile.close()
        self.logfile = None
        self.log_stat.set(0)

    def set_manual_butts(self, enable):
        "Abilita/disabilita comandi manuali"
        if enable:
            self.arrowb.config(state=NORMAL)
            self.val_target.config(state=NORMAL)
            self.parkb.config(state=NORMAL)
            self.homeb.config(state=NORMAL)
            self.syncb.config(state=NORMAL)
            self.offset.config(state=DISABLED)
        else:
            self.arrowb.config(state=DISABLED)
            self.val_target.config(state=DISABLED)
            self.parkb.config(state=DISABLED)
            self.homeb.config(state=DISABLED)
            self.syncb.config(state=DISABLED)
            self.offset.config(state=NORMAL)

    def set_slave(self, enable):
        "Attiva/disattiva inseguimento telescopio"
        self.target_az = None
        if enable:
            self.log_mark("START inseguimento")
            self._slave = 1
            self.setinfo("Inseguimento attivo")
            self.set_manual_butts(False)
        else:
            self.log_mark("STOP inseguimento")
            self._slave = 0
            self.log_mark("CMD AbortSlew")
            GLOB.dome.AbortSlew()
            self.setinfo("Inseguimento sospeso")
            self.set_manual_butts(True)

    def _log(self, slw, azm, tgtz, telrep):
        "data logger"
        if self.logfile is None:
            return
        sslw = 1 if slw else 0
        if telrep is None:
            telrep = (FLOAT_NAN, FLOAT_NAN, "_")
        hang, dec, side = telrep
        try:
            print("%.2f %d %.2f %.2f %f %f %s"%(time.time(), sslw, azm,
                                                tgtz, hang, dec, side), file=self.logfile)
        except TypeError as excp:
            self.log_mark("ERROR: "+str(excp))

    def tog_slave(self):
        "Sospende/riattiva inseguimento telescopio"
        if self._slave:
            self.set_slave(False)
        else:
            self.set_slave(True)

    def findhome(self):
        "Ritorna in posizione home"
        if self._slave:
            return
        self.target_az = None
        self.trgt_az.set(None)
        self.log_mark("CMD AbortSlew")
        GLOB.dome.AbortSlew()
        self.log_mark("CMD FindHome")
        GLOB.dome.FindHome()

    def park(self):
        "Ritorna in posizione park"
        if self._slave:
            return
        self.target_az = None
        self.trgt_az.set(None)
        self.log_mark("CMD AbortSlew")
        GLOB.dome.AbortSlew()
        self.log_mark("CMD Park")
        GLOB.dome.Park()

    def sync(self):
        "Sincronizza posizione cupola"
        if self._slave:
            return
        self.target_az = None
        self.trgt_az.set(None)
        self.log_mark("CMD AbortSlew")
        GLOB.dome.AbortSlew()
        val = self.sync_val.get()
        try:
            syncv = float(val)
        except ValueError as excp:
            self.log_mark("ERR: comando Sync - "+str(excp))
            self.setinfo("Devi specificare il valore in gradi!!")
        else:
            self.log_mark("CMD SyncToAzimuth(%.2f)"%syncv)
            GLOB.dome.SyncToAzimuth(syncv)

    def termina(self):
        "Termina procedura"
        self.log_mark("CMD AbortSlew")
        GLOB.dome.AbortSlew()
        if SIMULATED_ASCOM:
            GLOB.dome.Dispose()
        self.setinfo("Termina applicazione")
        self.stop_logger()
        GLOB.root.destroy()

    def update(self):
        "Aggiornamento stato del widget"
        telrep = get_tel(self.tel)
        if telrep is None:
            self.tel_led.set("gray")
            self.tel_ha.clear()
            self.tel_de.clear()
            self.setinfo("Attesa comunicazione con telescopio")
            self.tside.config(text="")
        else:
            self.tel_led.set("green")
            self.tel_ha.set(telrep[0])
            self.tel_de.set(telrep[1])
            fgc = "lightgreen" if telrep[2] in SIDES else "hotpink"
            self.tside.configure(text=telrep[2], fg=fgc)
            if self._slave:
                self.target_az = dome_azimuth(*telrep)
                if self.target_az is None:
                    self.setinfo(GLOB.error)
                    self.log_mark(GLOB.error)
                else:
                    self.target_az += self.offset.get()
                    self.setinfo("")
        self.trgt_az.set(self.target_az)
        try:
            azm, slw = self.move_dome(self.target_az)
        except COM_ERROR:                   # pylint: disable=W0703
            msg = "ERR: comunicazione con cupola interrotta"
            self.setinfo(msg)
            self.log_mark(msg)
            self.dome_mov.clear()
            self.dome_az.clear()
            self.dome_led.set("gray")
        else:
            self.dome_led.set("green")
            self.dome_az.set(azm)
            if slw:
                self.dome_mov.set("SLEW", fg="yellow")
            else:
                self.dome_mov.set("IDLE", fg="lightgreen")
        if self.at_target:
            self.attgt_led.set("green")
        else:
            self.attgt_led.set("gray")
        if self.target_az is not None:
            self._log(slw, azm, self.target_az, telrep)
        self.after(UPDATE_TRACKER, self.update)

    def setinfo(self, info):
        "Scrive in linea di stato"
        self.stline.config(text=info)

def main():
    "funzione main"
    if "-v" in sys.argv:
        print(__version__)
        sys.exit()

    GLOB.config = configure.get_config()
    if '-s' in sys.argv:
        GLOB.config["tel_ip"] = "127.0.0.1"
        GLOB.config["tel_port"] = 9753
        GLOB.config["debug"] = 1
        mode = " [Sim. Tel.]"
    else:
        mode = ""

    if SIMULATED_ASCOM:
        mode += " [No WIN]"

    GLOB.root = Tk()

    if "-h" in sys.argv:
        vinfo = "Vers. %s - %s, %s"%(__version__, __author__, __date__)
        msg = __doc__%vinfo
        wdg = WarningMsg(GLOB.root, msg)
    elif GLOB.config:
        GLOB.dome = wcl.Dispatch(GLOB.config["dome_ascom"])
        GLOB.root.title("OPC - Asservimento cupola - V. %s%s"%(__version__, mode))
        GLOB.dome_maxerr = GLOB.config["dome_maxerr"]
        GLOB.dome_crit = GLOB.config["dome_critical"]
        if not GLOB.dome.Connected:
            msg = "Errore comunicazione con cupola"
            wdg = WarningMsg(GLOB.root, msg)
        else:
            wdg = DTracker(GLOB.root, logging=True)
            GLOB.root.protocol("WM_DELETE_WINDOW", wdg.termina)
    else:
        GLOB.root.title("OPC - Configurazione parametri")
        wdg = configure.MakeConfig(GLOB.root, force=True)
    wdg.pack()
    GLOB.root.mainloop()

if __name__ == "__main__":
    main()
