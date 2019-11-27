"""
Modello vettoriale del telescopio

Uso:
      python3 mount.py [-w] [-d]

Dove:
      -w  Telescopio in posizione ovest (default: est)
      -d  Debug mode (connect to simulator)
"""

#  Sistema di riferimento cartesiano:

#    origine nel centro geometrico della cupola
#    Asse i diretto a sud
#    Asse j diretto ad est
#    Asse k diretto allo zenith

import sys, time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from multiprocessing import SimpleQueue, Process

from sympy import symbols, sin, cos
from sympy.vector import CoordSys3D
from sympy import Plane, Point3D, Segment3D

import configure as conf
from telecomm import TeleCommunicator

class DEBUG:
    on = False

OPC_LAT = 0.7596254681097
OPC_ZD = 1.5707963267948966-OPC_LAT

# COSTANTI:

HOUR_TO_RAD = 0.2617993877991494   # Da angolo orario a radianti
DEG_TO_RAD = 0.017453292519943295  # Da gradi sessag. a radianti
RAD_TO_DEG = 57.29577951308232

#   h: altezza dall'origine dell'intersezione dell'asse polare
#      con la verticale dal centro del piano di rotazione cupola
#   m: distanza fra  il punto sopra ed il piano di rotazione orario
#   b: distanza dell'asse ottico dal centro rotazione braccio
#   l: lunghezza del tubo
#   r: raggio cupola

H_MM = 470
M_MM = 650
B_MM = 1035
L_MM = 1550
R_MM = 3000

ORIGIN = Point3D(0, 0, 0)
Z_DOME = Point3D(0, 0, R_MM)
NORTH_P = Point3D(-R_MM, 0, 0)
SOUTH_P = Point3D(R_MM, 0, 0)
WEST_P = Point3D(0, -R_MM, 0)
EAST_P = Point3D(0, R_MM, 0)

N_PLANE = Plane(NORTH_P, (1, 0, 0))
S_PLANE = Plane(SOUTH_P, (1, 0, 0))
W_PLANE = Plane(WEST_P, (0, 1, 0))
E_PLANE = Plane(EAST_P, (0, 1, 0))
H_PLANE = Plane(ORIGIN, (0, 0, 1))  # Piano orizzonte
Z_PLANE = Plane(Z_DOME, (0, 0, 1))  # Piano orizzontale per zenit cupola

CS0 = CoordSys3D("CS0")   # Sistema di riferimento principale (alt-az)

STEPS = 20    # Polling checks per second

class FIG:
    "Global axis"
    AX = None

def log_debug(what):
    if DEBUG.on:
        print(what)

def stop_here(what=""):
    if DEBUG.on:
        input("Stop [%s]: "%what)

def plot_segment(segment, **kw):
    "Plots a Segment3D"
    pp1 = segment.p1.evalf()
    pp2 = segment.p2.evalf()
    xxp = (pp1.x, pp2.x)
    yyp = (pp1.y, pp2.y)
    zzp = (pp1.z, pp2.z)
    return FIG.AX.plot(xxp, yyp, zzp, **kw)

def plot_frame():
    "Traccia cerchi di riferimento"
    plt.ion()
    fig = plt.figure()
    stop_here("after plt.ion")
    FIG.AX = fig.gca(projection='3d')
    FIG.AX.cla()
    FIG.AX.set_xlim(-R_MM, R_MM)
    FIG.AX.set_ylim(-R_MM, R_MM)
    FIG.AX.set_zlim(0, R_MM)

    degs = np.linspace(0, np.pi*2., 800)  # Traccia cerchio base cupola
    FIG.AX.plot(np.cos(degs)*R_MM, np.sin(degs)*R_MM, 0, "--", color="gray")

    degs = np.linspace(0., np.pi, 400)  # Traccia semicerchio meridiano
    yvc = np.zeros(len(degs))
    FIG.AX.plot(np.cos(degs)*R_MM, yvc, np.sin(degs)*R_MM, "--", color="gray")
    FIG.AX.text(-R_MM, 0, 0, "N")
    FIG.AX.text(R_MM, 0, 0, "S")
    FIG.AX.text(0, -R_MM, 0, "W")
    FIG.AX.text(0, +R_MM, 0, "E")
    plt.draw()
    stop_here("after first plt.draw")

class Mount(Process):
    "Descrizione telescopio"
    def __init__(self, dataq):
        Process.__init__(self)
        self.dataq = dataq
        self.h_sym, self.m_sym = symbols("h m")
        self.b_sym, self.l_sym = symbols("b l")
        self.ha_sym, self.de_sym = symbols("ha dec")
        self.x_sym, self.y_sym, self.z_sym = symbols("x y z")

# L'asse polare passa per un punto H (0, 0, h) (sull'asse k ad altezza h)

        self.hpt = CS0.origin.locate_new("H", self.h_sym*CS0.k)

# Il piano di rotazione equatoriale è ortogonale all'asse polare
# e passa per un punto M a distanza m dal punto H lungo l'asse polare

# Il sistema di riferimento equatoriale e' ruotato di OPC_ZD intorno
# all'asse j di CS0 e ha origine in M

        self.pcs0 = CS0.orient_new_axis("PCS0", -OPC_ZD, CS0.j,\
                    location=-self.m_sym*cos(OPC_LAT)*CS0.i+(self.h_sym+self.m_sym*sin(OPC_LAT))*CS0.k)

# Il sistema di riferimento del tubo nel riferimento PCS0 è
# ruotato di ha rispetto all'asse k e traslato di b (braccio ad est) o -b (braccio ad ovest)

        self.pcste = self.pcs0.orient_new_axis("PCSTE", -self.ha_sym, self.pcs0.k,\
                location=self.b_sym*sin(self.ha_sym)*self.pcs0.i+self.b_sym*cos(self.ha_sym)*self.pcs0.j)
        self.pcstw = self.pcs0.orient_new_axis("PCSTW", -self.ha_sym, self.pcs0.k,\
                location=-self.b_sym*sin(self.ha_sym)*self.pcs0.i-self.b_sym*cos(self.ha_sym)*self.pcs0.j)

# L'estremità del tubo E in PCST è:

        self.exte_e = self.pcste.origin.locate_new("E", self.l_sym*cos(self.de_sym)*self.pcste.i+self.l_sym*sin(self.de_sym)*self.pcste.k)
        self.exte_w = self.pcstw.origin.locate_new("E", self.l_sym*cos(self.de_sym)*self.pcstw.i+self.l_sym*sin(self.de_sym)*self.pcstw.k)
        self.theplot = []
        self.text = ""
        plot_frame()

    def relevant_points(self, ha_h, de_d, side, as3d=False):
        "Punti rilevanti del modello"
        ha_r = HOUR_TO_RAD*ha_h
        de_r = DEG_TO_RAD*de_d
        all_subs = list(zip((self.h_sym, self.m_sym, self.b_sym, self.l_sym, self.ha_sym, self.de_sym),
                            (H_MM, M_MM, B_MM, L_MM, ha_r, de_r)))
                                    # Proietta i punti sul sist. principale
        h0p = self.hpt.subs(all_subs).express_coordinates(CS0)
        m0p = self.pcs0.origin.subs(all_subs).express_coordinates(CS0)
        if side == "E":
            t0p = self.pcste.origin.subs(all_subs).express_coordinates(CS0)
            e0p = self.exte_e.subs(all_subs).express_coordinates(CS0)
        else:
            t0p = self.pcstw.origin.subs(all_subs).express_coordinates(CS0)
            e0p = self.exte_w.subs(all_subs).express_coordinates(CS0)
        if as3d:
            return Point3D(h0p), Point3D(m0p), Point3D(t0p), Point3D(e0p)
        return h0p, m0p, t0p, e0p

    def plotme(self, ha_h, de_d, side):
        "Traccia figura"
        if self.theplot:
            self.clear()
        self.theplot = []
        h0p, m0p, t0p, e0p = self.relevant_points(ha_h, de_d, side, True)
        pier = Segment3D(ORIGIN, h0p)
        pol_ax = Segment3D(h0p, m0p)
        brace = Segment3D(m0p, t0p)
        tube = Segment3D(t0p, e0p)
        self.theplot.append(plot_segment(pier, color="b"))
        self.theplot.append(plot_segment(brace, color="b"))
        self.theplot.append(plot_segment(pol_ax, color="b"))
        self.theplot.append(plot_segment(tube, color="r", linewidth=3))
        strv = "HA: %.4f  DE: %.4f"%(ha_h, de_d)
        self.text = FIG.AX.text(0.01, 0.01, 0.01, strv, transform=FIG.AX.transAxes)
        plt.draw()
        stop_here("After following draw")
        log_debug("Redraw")

    def clear(self):
        "Cancella figura"
        for sgmlist in self.theplot:
            for sgm in sgmlist:
                sgm.remove()
        self.text.remove()

    def run(self):
        log_debug("Processo lanciato")
        count = 0
        coords = None
        delay = 1./STEPS
        while 1:
            count += 1
            if not self.dataq.empty():
                coords = self.dataq.get()
                if not coords:
                    break
            if count%STEPS == 0:
                if coords:
                    self.plotme(*coords)
                    coords = None
            time.sleep(delay)

HA_DE = ((1,30,"E"),(2,20,"E"),(3,40,"W"),(-5,0,"W"),())

def main():
    DEBUG.on = True
    qqq = SimpleQueue()
    mnt = Mount(qqq)
    log_debug("Lancio processo")
    mnt.start()
    for coords in HA_DE:
        time.sleep(1.2)
        log_debug("Sending: "+str(coords))
        qqq.put(coords)

if __name__ == "__main__":
    main()
