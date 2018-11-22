#!/usr/bin/python3
"""
GUI per controllo cupola OPC. Vers. %s - %s, %s

Uso:
        python3 cupola.py [-h] [-d] [-i]

Dove:
       [-d]  Modo debug: si connette al simulatore con IP: 127.0.0.1, Port: 9752
       [-i]  Mostra configurazione
"""
import sys
import re
import time
import math
import tkinter as tk

from widgets import FrameTitle, CButton, MButton, LabelRadiobutton, Number, Controller, Coord
from widgets import CoordEntry, Announce, Field, WarningMsg
from widgets import BD_FONT, H2_FONT, H4_FONT, H12_FONT, HMS, DMS
from domecomm import DomeCommunicator, StatiVano
from telecomm import TeleCommunicator
import astro
import configure
from interpolator import Interpolator

__author__ = "Luca Fini"
__version__ = "1.3"
__date__ = "Maggio 2018"

OK = "OK"
DOME_UPDATE_RATE = 1000           # Millisecondi
TELESCOPE_UPDATE_RATE = 2000      # Millisecondi

DOME_POS_ERROR = 0.8  # Max Errore inseguimento cupola (gradi)

# Modi di funzionamento rotatore cupola
DOME_MODE_MANUAL = 0
DOME_MODE_TELESCOPE = 1
DOME_MODE_TARGET = 2
DOME_MODE_OBJECT = 3

SELECTED_COLOR = "#0000cc"

BR_EAST = -1       # Valori variabile selettore lato braccio
BR_CENTER = 0
BR_WEST = 1

DOME_STATUS_FMT = """DomeStatus
   cupola: %s
   latitude: %s
   longitude: %s
   selector: %s
   telescope: %s"""

class DomeStatus:
    "Informazioni di stato per cupola"
    cupola = {}
    latitude = None
    longitude = None
    telescope = {}
    selector = None

    def __str__(self):
        return DOME_STATUS_FMT%(str(self.cupola), str(self.latitude),
                                str(self.longitude), str(self.selector), str(self.telescope))

DOME_STATUS = DomeStatus()

class LightStatus(FrameTitle):
    "Widget per stato luci"
    def __init__(self, parent, dcom, logfunc):
        FrameTitle.__init__(self, parent, "Luci",
                            font=H2_FONT, border=2, relief=tk.RIDGE)
        self.dcom = dcom
        self.logfunc = logfunc
        tk.Label(self.body, text="Principale ",
                 font=H4_FONT).grid(row=0, column=0, sticky=tk.E)
        CButton(self.body, "ml_on", text="On", width=3,
                padx=1, pady=0, command=self.bpress).grid(row=0, column=1)
        CButton(self.body, "ml_off", text="Off", width=3,
                padx=1, pady=0, command=self.bpress).grid(row=0, column=2)
        tk.Label(self.body, text=" ").grid(row=0, column=3)
        self.main_light = MButton(self.body, "m_light", "circle", 32)
        self.main_light.grid(row=0, column=4)

        tk.Label(self.body, text="Notturna ",
                 font=H4_FONT).grid(row=1, column=0, sticky=tk.E)
        CButton(self.body, "nl_on", text="On", width=3,
                padx=1, pady=0, command=self.bpress).grid(row=1, column=1)
        CButton(self.body, "nl_off", text="Off", width=3,
                padx=1, pady=0, command=self.bpress).grid(row=1, column=2)
        self.night_light = MButton(self.body, "n_light", "circle", 32)
        self.night_light.grid(row=1, column=4)

    def bpress(self, bname):
        "Bottone premuto"
        if bname == "ml_on":
            self.dcom.main_light_on()
        elif bname == "ml_off":
            self.dcom.main_light_off()
        elif bname == "nl_on":
            self.dcom.night_light_on()
        elif bname == "nl_off":
            self.dcom.night_light_off()

    def clear(self):
        "Azzera campi widget"
        self.night_light.clear()
        self.main_light.clear()

    def updatew(self):
        "Aggiorna widget"
        lnstat = DOME_STATUS.cupola.get("LN")
        if lnstat:
            self.night_light.set("yellow")
        else:
            self.night_light.clear()
        lnstat = DOME_STATUS.cupola.get("LP")
        if lnstat:
            self.main_light.set("yellow")
        else:
            self.main_light.clear()

class ManualCtrl(tk.Frame):
    "Widget per parte controllo manuale"
    def __init__(self, parent, selectvar, dcom, logfunc):
        tk.Frame.__init__(self, parent, border=1, relief=tk.GROOVE, padx=3, pady=3)
        self.logfunc = logfunc
        self.dcom = dcom
        internal_fr = tk.Frame(self)
        self.def_bg = self.cget("bg")
        top_ln = tk.Frame(internal_fr)
        LabelRadiobutton(top_ln, "Controllo manuale",
                         selectvar, DOME_MODE_MANUAL).pack(side=tk.LEFT)
        self.sync_bt = CButton(top_ln, "sync", text="Sync",
                               command=self.bpress, width=5, padx=0, pady=0)
        tk.Label(top_ln, text=" ").pack(side=tk.LEFT, expand=1, fill=tk.X)
        self.sync_bt.pack(side=tk.LEFT)
        top_ln.pack(expand=1, fill=tk.X)
        bot_fr = tk.Frame(internal_fr)
        btns_fr = tk.Frame(bot_fr)
        self.left_bt = MButton(btns_fr, "left", "left", 32, command=self.bpress)
        self.left_bt.pack(side=tk.LEFT)
        tk.Label(btns_fr, text=" ").pack(side=tk.LEFT)
        self.stop_bt = CButton(btns_fr, "stop", text="Stop",
                               command=self.bpress, width=5, pady=4)
        self.stop_bt.pack(side=tk.LEFT)
        tk.Label(btns_fr, text=" ").pack(side=tk.LEFT)
        self.right_bt = MButton(btns_fr, "right", "right", 32, command=self.bpress)
        self.right_bt.pack(side=tk.LEFT)
        btns_fr.grid(row=0, column=1, pady=3)
        tk.Label(bot_fr, text="Pos. ",
                 font=H4_FONT).grid(row=1, column=0)
        pos_fr = tk.Frame(bot_fr)
        self.az_fr = Number(pos_fr, font=H12_FONT,
                            _format="%3d", width=5, pady=5)
        tk.Label(pos_fr, text=" ").pack(side=tk.LEFT)
        self.az_fr.pack(side=tk.LEFT)
        self.goto_bt = MButton(pos_fr, "goto", "left", 32, command=self.bpress)
        self.goto_bt.pack(side=tk.LEFT, padx=3)
        self.goto_val = Controller(pos_fr, upper=359, lower=0, circular=True)
        self.goto_val.pack(side=tk.LEFT)
        pos_fr.grid(row=1, column=1)
        bot_fr.pack(anchor=tk.W)
        internal_fr.pack(expand=1, fill=tk.BOTH)
        self.azimuth = -1

    def goto(self, pos):
        "Goto chiamato da widget tracking"
        self.goto_val.set(pos)
        self.dcom.goto(pos)

    def bpress(self, bname):
        "ManualCtrl: Premuto bottone movimento"
        if bname == "left":
            self.dcom.go_left()
        elif bname == "right":
            self.dcom.go_right()
        elif bname == "sync":
            self.dcom.sync()
        elif bname == "stop":
            self.dcom.do_stop()
        elif bname == "goto":
            pos = self.goto_val.get()
            self.dcom.goto(pos)

    def select(self, value):
        "Imposta colore selezione"
        if value:
            self.config(bg=SELECTED_COLOR)
        else:
            self.config(bg=self.def_bg)

    def clear(self):
        "ManualCtrl: Azzera tutto il widget"
        self.sync_bt.clear()
        self.left_bt.clear()
        self.right_bt.clear()
        self.stop_bt.clear()
        self.az_fr.set(None)

    def updatew(self):
        "ManualCtrl: Aggiorna widget"
        if not DOME_STATUS.cupola:
            self.clear()
        if DOME_STATUS.selector == DOME_MODE_MANUAL:
            self.config(bg=SELECTED_COLOR)
        else:
            self.config(bg=self.def_bg)
        lnstat = DOME_STATUS.cupola.get("MOV")
        if lnstat == -1:
            self.right_bt.clear()
            self.left_bt.set("yellow")
            self.stop_bt.set("red")
        elif lnstat == 1:
            self.left_bt.clear()
            self.right_bt.set("yellow")
            self.stop_bt.set("red")
        elif lnstat == 0:
            self.right_bt.clear()
            self.left_bt.clear()
            self.stop_bt.clear()
        elif lnstat is not None:
            self.logfunc("Stato inatteso per movimento cupola: "+str(lnstat), 2)
        self.azimuth = DOME_STATUS.cupola.get("POS", -1)
        if self.azimuth < 0:
            self.az_fr.clear()
            self.sync_bt.clear()
        else:
            self.az_fr.set(self.azimuth)
            self.sync_bt.set("green")
        issync = DOME_STATUS.cupola.get("SYNC", 0)
        if issync == 1:
            self.sync_bt.set("yellow")
        elif issync == 2:
            self.sync_bt.set("green")
        else:
            self.sync_bt.clear()
        if DOME_STATUS.cupola.get("GOTO"):
            self.goto_bt.set("yellow")
        else:
            self.goto_bt.clear()

class TelescopeCtrl(tk.Frame):
    "Widget per parte inseguimento telescopio"
    def __init__(self, parent, selectvar, tcom, logfunc):
        tk.Frame.__init__(self, parent, border=1, relief=tk.RAISED, padx=3, pady=3)
        line1 = tk.Frame(self)
        self.logfunc = logfunc
        self.communicator = tcom
        self.def_bg = self.cget("bg")
        LabelRadiobutton(line1, "Pos. telescopio    ",
                         selectvar, DOME_MODE_TELESCOPE).pack(side=tk.LEFT, anchor=tk.W)
        LabelRadiobutton(line1, "Target",
                         selectvar, DOME_MODE_TARGET).pack(side=tk.LEFT, anchor=tk.W)
        line1.pack(expand=1, fill=tk.X)
        line2 = tk.Frame(self)
        tk.Label(line2, text="    A.R. ").grid(column=0, row=0, sticky=tk.E)
        self.tel_ra_wdg = Coord(line2, width=9)
        self.tel_ra_wdg.grid(column=1, row=0, sticky=tk.W)
        tk.Label(line2, text="        Dec ").grid(column=2, row=0, sticky=tk.E)
        self.tel_de_wdg = Coord(line2, width=10)
        self.tel_de_wdg.grid(column=3, row=0, sticky=tk.W)
        tk.Label(line2, text=" HA ").grid(column=0, row=1, sticky=tk.E)
        self.tel_ha_wdg = Coord(line2, width=9)
        self.tel_ha_wdg.grid(column=1, row=1, sticky=tk.W)
        tk.Label(line2, text=" T.Sid ").grid(column=2, row=1, sticky=tk.E)
        self.tsid_wdg = Coord(line2, width=10)
        self.tsid_wdg.grid(column=3, row=1, sticky=tk.W)
        line2.pack(expand=1, fill=tk.X)
        self.updatew()

    def clear(self):
        "TelescopeCtrl: Pulisci widget T.B.D."
        self.tel_de_wdg.clear()
        self.tel_ra_wdg.clear()
        self.tel_ha_wdg.clear()
        self.tsid_wdg.clear()

    def select(self, value):
        "Imposta colore selezione"
        if value:
            self.config(bg=SELECTED_COLOR)
        else:
            self.config(bg=self.def_bg)

    def updatew(self):
        "TelescopeCtrl: Aggiorna widget"
        selector = DOME_STATUS.selector
        pside = self.communicator.get_pside()
        tsid = astro.loc_st_now(DOME_STATUS.longitude)
        if selector == DOME_MODE_TARGET:
            ras = self.communicator.get_target_ra()
            dec = self.communicator.get_target_de()
        else:
            ras = self.communicator.get_current_ra()
            dec = self.communicator.get_current_de()
            print("ar dec:", ras, dec)
        try:
            hra = tsid - ras
        except:
            hra = None
        DOME_STATUS.telescope = {"DE": dec, "RA": ras, "HA": hra, "TS": tsid, "PSIDE": pside}
        self.tel_de_wdg.set(dec)
        self.tel_ra_wdg.set(ras)
        self.tel_ha_wdg.set(hra)
        self.tsid_wdg.set(tsid)
        self.after(TELESCOPE_UPDATE_RATE, self.updatew)

class ObjectCtrl(tk.Frame):
    "Widget per parte inseguimento oggetto"
    def __init__(self, parent, selectvar, logfunc, debug):
        tk.Frame.__init__(self, parent, border=1, relief=tk.GROOVE, padx=3, pady=3)
        self.debug = debug
        self.logfunc = logfunc
        self.def_bg = self.cget("bg")
        internal_fr = tk.Frame(self)
        self.selector = LabelRadiobutton(internal_fr, "Inseguimento oggetto",
                                         selectvar, DOME_MODE_OBJECT)
        self.selector.pack(anchor=tk.W)
        coo_fr = tk.Frame(internal_fr)
        self.rga = CoordEntry(coo_fr, "  A.R.", HMS)
        self.rga.pack(side=tk.LEFT)
        self.dec = CoordEntry(coo_fr, "  Dec.", DMS, width=3)
        self.dec.pack(side=tk.LEFT)
        coo_fr.pack()
        internal_fr.pack(expand=1, fill=tk.BOTH)
        self.tsid0 = None
        self.time0 = None

    def get_ha(self, ar_rad):
        "ObjectCtrl: Calcola angolo orario da ascensione retta (in radianti)"
        if self.tsid0 is None:
            self.time0 = time.time()
            tsid_rad = astro.loc_st_now(DOME_STATUS.longitude)*astro.HOUR_TO_RAD
            self.tsid0 = tsid_rad
        else:
            delta = (time.time()-self.time0)*astro.TSEC_TO_RAD
            tsid_rad = self.tsid0+delta*astro.TCIV_TO_TSID
        ha_rad = tsid_rad-ar_rad
        return ha_rad

    def clear(self):
        "ObjectCtrl: Azzera campi"
        self.rga.clear()
        self.dec.clear()
        self.tsid0 = None

    def select(self, value):
        "ObjectCtrl: seleziona/deseleziona widget"
        if value:
            self.config(bg=SELECTED_COLOR)
        else:
            self.config(bg=self.def_bg)

class DomeRotator(FrameTitle):
    "Widget per rotazione cupola"
    def __init__(self, parent, selectvar, dcom, tcom, logfunc, debug):
        FrameTitle.__init__(self, parent, "Rotazione cupola",
                            font=H2_FONT, border=2, relief=tk.RIDGE)
        self.brace_side = tk.IntVar()
        self.mode_select = selectvar
        self.dcom = dcom
        self.tcom = tcom
        self.debug = debug
        self.logfunc = logfunc
        self.man_wdg = ManualCtrl(self, selectvar, dcom, logfunc)
        self.man_wdg.pack(expand=1, fill=tk.X)
        self.tel_wdg = TelescopeCtrl(self, selectvar, tcom, logfunc)
        self.tel_wdg.pack(expand=1, fill=tk.X)
        self.obj_wdg = ObjectCtrl(self, selectvar, logfunc, self.debug)
        self.obj_wdg.pack(expand=1, fill=tk.X)
        brace_fr = tk.Frame(self, border=1, relief=tk.GROOVE, padx=3, pady=3)
        tk.Label(brace_fr, text="  Posizione braccio:", font=BD_FONT).pack(side=tk.LEFT)
        tk.Label(brace_fr, text="    E").pack(side=tk.LEFT)
        tk.Radiobutton(brace_fr, variable=self.brace_side,
                       value=BR_EAST, padx=0).pack(side=tk.LEFT)
        tk.Label(brace_fr, text="   ").pack(side=tk.LEFT)
        tk.Radiobutton(brace_fr, variable=self.brace_side, value=BR_CENTER).pack(side=tk.LEFT)
        tk.Label(brace_fr, text="    O").pack(side=tk.LEFT)
        tk.Radiobutton(brace_fr, variable=self.brace_side, value=BR_WEST).pack(side=tk.LEFT)
        brace_fr.pack(expand=1, fill=tk.X)
        self.interp_e = Interpolator("e", de_units="R", ha_units="R")
        self.interp_w = Interpolator("w", de_units="R", ha_units="R")
        self.mode_select.set(DOME_MODE_MANUAL)
        self.last_selected = DOME_MODE_MANUAL

    def get_azimuth(self, ha_rad, de_rad, side):
        "DomeRotator: Calcola l'azimuth dell'oggetto stellare"
        if side == BR_EAST:
            az_deg = self.interp_e.interpolate(ha_rad, de_rad)
        elif side == BR_WEST:
            az_deg = self.interp_w.interpolate(ha_rad, de_rad)
        else:
            try:
                az_rad = astro.az_coords(ha_rad, de_rad)[0]
                az_deg = int(astro.normalize_angle(az_rad*astro.RAD_TO_DEG, 360.)+0.5)
            except Exception:
                az_deg = float("nan")
        if self.debug:
            print("DBG> get_azimut: ha_rad, de_rad, side, az_deg", (ha_rad, de_rad, side, az_deg))
        return az_deg

    def track_telescope(self):
        "DomeRotator: Attiva modo tracking del telescopio"
        side = self.brace_side.get()
        ha_hou = self.tel_wdg.tel_ha_wdg.get()
        de_deg = self.tel_wdg.tel_de_wdg.get()
        if self.debug:
            print("DBG> TEL.(HA, DE):", (ha_hou, de_deg))
        if ha_hou is None or de_deg is None:
            return False
        ha_rad = ha_hou*astro.HOUR_TO_RAD
        de_rad = de_deg*astro.DEG_TO_RAD
        target_deg = self.get_azimuth(ha_rad, de_rad, side)
        return self.track(target_deg)

    def track_object(self):
        "DomeRotator: Ativa modo tracking di oggetto dato"
        side = self.brace_side.get()
        ar_rad = self.obj_wdg.rga.value_rad()
        if math.isnan(ar_rad):
            return False
        ha_rad = self.obj_wdg.get_ha(ar_rad)
        de_rad = self.obj_wdg.dec.value_rad()

        target_deg = self.get_azimuth(ha_rad, de_rad, side)
        return self.track(target_deg)

    def track(self, target_deg):
        "DomeRotator: Track target"
        if self.man_wdg.azimuth < 0:
            return False
        if math.isnan(target_deg):
            return False
        dist = astro.find_shortest(self.man_wdg.azimuth, target_deg)[0]
        if dist > DOME_POS_ERROR:
            self.man_wdg.goto(target_deg)
        return True

    def clear(self):
        "DomeRotator: Azzera campi del widget"
        self.man_wdg.clear()
        self.tel_wdg.clear()
        self.obj_wdg.clear()

    def updatew(self):
        "DomeRotator: Aggiorna widget Rotazione Cupola"
        selection = self.mode_select.get()
        if selection in (DOME_MODE_TELESCOPE, DOME_MODE_TARGET):
            if not self.track_telescope():
                selection = DOME_MODE_MANUAL
                self.logfunc("Inseguimento telescopio non possibile", 2)
        elif selection == DOME_MODE_OBJECT:
            if not self.track_object():
                selection = DOME_MODE_MANUAL
                self.logfunc("Inseguimento oggetto non possibile", 2)
        else:
            selection = DOME_MODE_MANUAL
        if selection != self.last_selected:
            self.last_selected = selection
            if selection == DOME_MODE_MANUAL:
                self.man_wdg.select(True)
                self.tel_wdg.select(False)
                self.obj_wdg.select(False)
                self.logfunc("Selezionato modo manuale")
            elif selection == DOME_MODE_TELESCOPE:
                self.man_wdg.select(False)
                self.tel_wdg.select(True)
                self.obj_wdg.select(False)
                self.logfunc("Selezionato inseguimento telescopio (posizione)")
            elif selection == DOME_MODE_TARGET:
                self.man_wdg.select(False)
                self.tel_wdg.select(True)
                self.obj_wdg.select(False)
                self.logfunc("Selezionato inseguimento telescopio (target)")
            elif selection == DOME_MODE_OBJECT:
                self.man_wdg.select(False)
                self.tel_wdg.select(False)
                self.obj_wdg.select(True)
                self.logfunc("Selezionato inseguimento oggetto")
#           if selection in (DOME_MODE_TELESCOPE, DOME_MODE_TARGET):
#               bside = dome_status["TEL"][4]
#               if bside == "E":
#                   self.brace_side.set(-1)
#               elif bside == "W":
#                   self.brace_side.set(1)
#               else:
#                   self.brace_side.set(0)
        DOME_STATUS.selector = selection
        self.mode_select.set(selection)
        self.man_wdg.updatew()

class DomeDoor(FrameTitle):
    "Pannello per vano osservazione"
    def __init__(self, parent, dcom, logfunc):
        FrameTitle.__init__(self, parent, "Vano osservazione",
                            font=H2_FONT, border=2, relief=tk.RIDGE)
        tk.Label(self.body, text="Stato ", font=H4_FONT).grid(row=1, column=0, sticky=tk.E)
        self.dcom = dcom
        self.logfunc = logfunc
        self.status_wdg = Field(self.body, font=H12_FONT, width=15)
        self.status_wdg.grid(row=1, column=1, sticky=tk.W)
        bframe = tk.Frame(self.body)
        self.open_bt = CButton(bframe, "open", text="Apre",
                               command=self.bpress, width=5, pady=4)
        self.open_bt.pack(side=tk.LEFT)
        self.close_bt = CButton(bframe, "close", text="Chiude",
                                command=self.bpress, width=5, pady=4)
        self.close_bt.pack(side=tk.LEFT)
        bframe.grid(row=10, column=1)

    def bpress(self, bname):
        "DomeDoor: premuto bottone"
        if bname == "open":
            self.dcom.do_open()
        elif bname == "close":
            self.dcom.do_close()

    def clear(self):
        "DomeDoor: Azzera campi del widget"
        self.status_wdg.clear()
        self.close_bt.clear()
        self.open_bt.clear()

    def updatew(self):
        "DomeDoor: Aggiorna campi del widget"
        lnstat = DOME_STATUS.cupola.get("VANO")
        if lnstat == StatiVano.CLOSED:
            self.status_wdg.set("CHIUSO")
            self.close_bt.clear()
            self.open_bt.clear()
        elif lnstat == StatiVano.OPENING:
            self.status_wdg.set("IN APERTURA")
            self.open_bt.set("yellow")
        elif lnstat == StatiVano.OPEN:
            self.status_wdg.set("APERTO")
            self.close_bt.clear()
            self.open_bt.clear()
        elif lnstat == StatiVano.CLOSING:
            self.status_wdg.set("IN CHIUSURA")
            self.close_bt.set("yellow")
        elif lnstat is not None:
            self.logfunc("Stato inatteso per Vano Osservazione: "+str(lnstat), 2)

class Dome(FrameTitle):
    "Pannello per controllo cupola"
    SeverityColor = ["white", "yellow", "red"]
    def __init__(self, parent, config):
        self.root = parent
        domeip = config["dome_ip"]
        domeport = config["dome_port"]
        telip = config["tel_ip"]
        telport = config["tel_port"]
        self.debug = config.get("debug", False)
        self.dcom = DomeCommunicator(domeip, domeport)
        self.tcom = TeleCommunicator(telip, telport)
        self.d_connected = False
        self.t_connected = False
        FrameTitle.__init__(self, parent, "Controllo cupola")
        self.comdome = MButton(self.body, "", "circle", 32,
                               label="    Comunicazione cupola ",
                               border=1, relief=tk.GROOVE, padx=4)
        self.comdome.grid(row=0, column=0)
        left_frame = tk.Frame(self.body)
        self.lights_wdg = LightStatus(left_frame, self.dcom, self.logmsg)
        self.lights_wdg.pack(fill=tk.X, expand=1, anchor=tk.N)
        self.domdoor_wdg = DomeDoor(left_frame, self.dcom, self.logmsg)
        self.domdoor_wdg.pack(expand=1, fill=tk.X, anchor=tk.N)
        left_frame.grid(row=1, column=0, sticky=tk.W+tk.E)
        tk.Label(self.body, text=" ").grid(row=0, column=1)
        self.comtele = MButton(self.body, "", "circle", 32,
                               label="        Comunicazione telescopio ",
                               border=1, relief=tk.GROOVE, padx=4)
        self.comtele.grid(row=0, column=2)
        right_frame = tk.Frame(self.body)
        self.mode_select = tk.IntVar()
        self.domrot_wdg = DomeRotator(right_frame, self.mode_select, self.dcom,
                                      self.tcom, self.logmsg, self.debug)
        self.domrot_wdg.pack(anchor=tk.N, fill=tk.X, expand=1)
        right_frame.grid(row=1, column=2, sticky="ewn")

        self.loglines = Announce(self, 3, width=64)
        self.loglines.pack(expand=1, fill=tk.X)
        self.updatew()
#       self.logmsg("Connessione cupola a: %s port %d"%(domeip, domeport))

    def logmsg(self, line, severity=0):
        "Dome: Scrive messaggio in area di log"
        fgcolor = self.SeverityColor[severity]
        self.loglines.writeline(line, fgcolor)

    def clear(self):
        "Dome: Ripulisce widget (escluso area telescopio)"
#       self.domrot_wdg.clear()
        self.lights_wdg.clear()
        self.domdoor_wdg.clear()
        self.comdome.clear()

    def updatew(self):
        "Dome: Aggiornamento campi del widget DOME"
        DOME_STATUS.cupola = self.dcom.get_hw_status()
        if DOME_STATUS.telescope.get("HA") is not None:
            self.comtele.set("green")
        else:
            self.comtele.clear()
        if DOME_STATUS.cupola.get("POS") is not None:
            self.comdome.set("green")
            if not self.d_connected:
                self.logmsg("Server cupola connesso")
            self.d_connected = True
        else:
            self.clear()
            if self.d_connected:
                self.logmsg("Server cupola disconnesso", 2)
            self.d_connected = False
        if self.debug:
            print("DBG>", DOME_STATUS)
        self.lights_wdg.updatew()
        self.domdoor_wdg.updatew()
        self.domrot_wdg.updatew()
        self.root.after(DOME_UPDATE_RATE, self.updatew)

PUNCT = re.compile("[^0-9.]+")
def str2rad(line):
    "Converte tre numeri (g,m,s) in radianti"
    three = [float(x) for x in PUNCT.split(line)]
    rad = astro.dms2rad(*three)
    return rad

def main():
    "funzione main"
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
        config = configure.get_config()

    DOME_STATUS.longitude = config.get("lon", 0)
    DOME_STATUS.latitude = config.get("lat", 0)

    root = tk.Tk()
    root.title("Osservatorio Polifunzionale del Chianti")
    if "-h" in sys.argv:
        msg = __doc__ % (__version__, __author__, __date__)
        wdg1 = WarningMsg(root, msg)
    elif '-i' in sys.argv:
        str_conf = configure.show_config(config)
        wdg1 = WarningMsg(root, str_conf)
    elif not config:
        wdg1 = WarningMsg(root, configure.NO_CONFIG)
    else:
        wdg1 = Dome(root, config)
    wdg1.pack()
    root.mainloop()

if __name__ == "__main__":
    main()
