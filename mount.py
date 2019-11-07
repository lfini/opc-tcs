# -*- coding: utf-8 -*-
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

import sys
import math
import random
import pickle
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from sympy import symbols, solve, sin, cos
from sympy.vector import CoordSys3D
from sympy import Plane, Point3D, Line3D, Segment3D

import configure as conf
from telecomm import TeleCommunicator

OPC_LAT = 0.7596254681097
OPC_ZD  = 1.5707963267948966-OPC_LAT

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

h, m, b, l = symbols("h m b l")

ha, dec = symbols("ha dec")

x,y,z=symbols("x y z")

CS0 = CoordSys3D("CS0")   # Sistema di riferimento principale (alt-az)

SIDE = "e"    # Lato del tubo (E/O)
if "-w" in sys.argv:
    SIDE = "w"

if "-h" in sys.argv:
    print(__doc__)
    sys.exit()

# L'asse polare passa per un punto H (0, 0, h) (sull'asse k ad altezza h)

H = CS0.origin.locate_new("H", h*CS0.k)

# Il piano di rotazione equatoriale è ortogonale all'asse polare
# e passa per un punto M a distanza m dal punto H lungo l'asse polare

# Il sistema di riferimento equatoriale e' ruotato di OPC_ZD intorno
# all'asse j di CS0 e ha origine in M

PCS0 = CS0.orient_new_axis("PCS0", -OPC_ZD, CS0.j, location=-m*cos(OPC_LAT)*CS0.i+(h+m*sin(OPC_LAT))*CS0.k)

# Il sistema di riferimento del tubo nel riferimento PCS0 è
# ruotato di ha rispetto all'asse k e traslato di b (braccio ad est) o -b (braccio ad ovest)

PCSTE = PCS0.orient_new_axis("PCSTE", -ha, PCS0.k, location=b*sin(ha)*PCS0.i+b*cos(ha)*PCS0.j)
PCSTW = PCS0.orient_new_axis("PCSTW", -ha, PCS0.k, location=-b*sin(ha)*PCS0.i-b*cos(ha)*PCS0.j)

class FIG:
    AX = None

if SIDE == "e":
    PCST = PCSTE
else:
    PCST = PCSTW

# L'estremità del tubo E in PCST è:

E = PCST.origin.locate_new("E", l*cos(dec)*PCST.i + l*sin(dec)*PCST.k)

CUPOLA = x**2 + y**2 + z**2 - R_MM**2  # Equazione della cupola"

ORIGIN = Point3D(0,0,0)
Z_DOME = Point3D(0,0,R_MM)
NORTH_P = Point3D(-R_MM,0,0)
SOUTH_P = Point3D(R_MM,0,0)
WEST_P = Point3D(0,-R_MM,0)
EAST_P = Point3D(0,R_MM,0)

N_PLANE = Plane(NORTH_P,(1,0,0))
S_PLANE = Plane(SOUTH_P,(1,0,0))
W_PLANE = Plane(WEST_P,(0,1,0))
E_PLANE = Plane(EAST_P,(0,1,0))
H_PLANE = Plane(ORIGIN, (0,0,1))  # Piano orizzonte
Z_PLANE = Plane(Z_DOME, (0,0,1))  # Piano orizzontale per zenit cupola

def relevant_points(ha_h, de_d, as3d=False):
    "Punti rilevanti del modello"
    ha_r = HOUR_TO_RAD*ha_h
    de_r = DEG_TO_RAD*de_d
    all_subs = list(zip((h, m, b, l, ha, dec), (H_MM, M_MM, B_MM, L_MM, ha_r, de_r)))
                                # Proietta i punti sul sist. principale
    h0 = H.subs(all_subs).express_coordinates(CS0)
    m0 = PCS0.origin.subs(all_subs).express_coordinates(CS0)
    t0 = PCST.origin.subs(all_subs).express_coordinates(CS0)
    e0 = E.subs(all_subs).express_coordinates(CS0)
    if as3d:
        return Point3D(h0), Point3D(m0), Point3D(t0), Point3D(e0)
    return h0, m0, t0, e0

def plot_tel(ha_h, de_d):
    h0, m0, t0, e0 = relevant_points(ha_h, de_d, True)
    
    pier=Segment3D(ORIGIN, h0)
    plot_segment(pier, color="b")

    pol_ax = Segment3D(h0,m0)
    plot_segment(pol_ax, color="b")

    brace = Segment3D(m0,t0)
    plot_segment(brace, color="b")

    tube = Segment3D(t0, e0)
    plot_segment(tube, color="r", linewidth=3)

class MountDrawing:
    def __init__(self, ha_h, de_d):
        h0, m0, t0, e0 = relevant_points(ha_h, de_d, True)
        self.hah = ha_h
        self.ded = de_d
        self.pier = Segment3D(ORIGIN, h0)
        self.pol_ax = Segment3D(h0,m0)
        self.brace = Segment3D(m0,t0)
        self.tube = Segment3D(t0, e0)
        self.theplot = []

    def plotme(self):
        self.theplot.append(plot_segment(self.pier, color="b"))
        self.theplot.append(plot_segment(self.brace, color="b"))
        self.theplot.append(plot_segment(self.pol_ax, color="b"))
        self.theplot.append(plot_segment(self.tube, color="r", linewidth=3))
        strv = "HA: %.4f  DE: %.4f"%(self.hah, self.ded)
        self.text = FIG.AX.text(0.01, 0.01, 0.01, strv, transform=FIG.AX.transAxes)

    def clear(self):
        for sgmlist in self.theplot:
            for sgm in sgmlist:
                sgm.remove()
        self.text.remove()

def plot_segment(segment, **kw):
    "Plots a Segment3D"
    p1 = segment.p1.evalf()
    p2 = segment.p2.evalf()
    xx = (p1.x, p2.x)
    yy = (p1.y, p2.y)
    zz = (p1.z, p2.z)
    return FIG.AX.plot(xx,yy,zz, **kw)

def plot_line(aline, **kw):
    "Plots a Line3D (inside the view cube)"
    try:
        ph = aline.intersection(H_PLANE)[0].evalf()
        pz = aline.intersection(Z_PLANE)[0].evalf()
    except:
        ph, pz = None, None
    try:
        pn = aline.intersection(N_PLANE)[0].evalf()
        ps = aline.intersection(S_PLANE)[0].evalf()
    except:
        pn, ps = None, None
    try:
        pw = aline.intersection(W_PLANE)[0].evalf()
        pe = aline.intersection(E_PLANE)[0].evalf()
    except:
        pw, pe = None, None
    segm = None
    if ph and abs(ph.x) <= R_MM and abs(ph.y) <= R_MM:
        p0 = ph
    elif pn and abs(pn.x) <= R_MM and abs(pn.y) <= R_MM:
        p0 = pn
    elif pw and abs(pw.x) <= R_MM and abs(pw.y) <= R_MM:
        p0 = pw
    if pz and abs(pz.x) <= R_MM and abs(pz.y) <= R_MM:
        p1 = pz
    elif ps and abs(ps.x) <= R_MM and abs(ps.y) <= R_MM:
        p1 = ps
    elif pe and abs(pe.x) <= R_MM and abs(pe.y) <= R_MM:
        p1 = pe

    segm = Segment3D(p0,p1)
    return plot_segment(segm, **kw)

def plot_point(point, **kw):
    "Plot a point (either a Point3D or a tuple)"
    if type(point) is Point3D:
        the_point = (point.x.evalf(), point.y.evalf(), point.z.evalf())
    else:
        the_point = point
    return FIG.AX.plot([the_point[0]],[the_point[1]],[the_point[2]],"o", **kw)

def plot_frame():
    "Traccia cerchi di riferimento"
    fig = plt.figure()
    FIG.AX = fig.gca(projection='3d')
    FIG.AX.cla()
    FIG.AX.set_xlim(-R_MM,R_MM)
    FIG.AX.set_ylim(-R_MM,R_MM)
    FIG.AX.set_zlim(0,R_MM)

    degs = np.linspace(0,np.pi*2.,800)  # Traccia cerchio base cupola
    FIG.AX.plot(np.cos(degs)*R_MM,np.sin(degs)*R_MM,0,"--",color="gray")

    degs = np.linspace(0.,np.pi,400)  # Traccia semicerchio meridiano
    yv = np.zeros(len(degs))
    FIG.AX.plot(np.cos(degs)*R_MM,yv,np.sin(degs)*R_MM,"--",color="gray")
    FIG.AX.text(-R_MM,0,0,"N")
    FIG.AX.text(R_MM,0,0,"S")
    FIG.AX.text(0,-R_MM,0,"W")
    FIG.AX.text(0,+R_MM,0,"E")

def plot_win(az_r):
    "Traccia un quarto di cerchio in corrispondenza di azimuth dato"
    az = -az_r - math.pi
    cy = R_MM*sin(az)
    cx = R_MM*cos(az)/cy
    ang = np.linspace(0,np.pi/2.,200)  # Traccia cerchio base cupola
    z = R_MM*np.sin(ang)
    y = cy*np.cos(ang)
    x = cx*y
    FIG.AX.plot(x,y,z,color="g")

def optical_axis(ha_h, de_d):
    "Asse ottico del telescopio, se >1 grad0 sopra orizzonte (Line3D)"
    (h0, m0, t0, e0) = relevant_points(ha_h, de_d, True)
    if (e0.z.evalf()-t0.z.evalf())/L_MM > DEG_TO_RAD:
        return Line3D(t0,e0)
    return None

def point_coord(apoint):
    "Calcola altezza, azimuth di un punto, rispetto all'origine"
    xx = apoint.x.evalf()
    yy = apoint.y.evalf()
    zz = apoint.z.evalf()
    az = (math.pi-math.atan2(yy, xx))*RAD_TO_DEG
    alt = (math.atan2(zz, math.sqrt(xx*xx+yy*yy)))*RAD_TO_DEG
    return alt, az

def dome_coord(ha_h, de_d):
    "Trova altezza, azimuth punto cupola dati ha e dec telescopio)"
    apoint = dome_viewpoint(ha_h, de_d)
    if apoint:
        return point_coord(apoint)
    return float("nan"), float("nan")

def main():
    goon = True
    if "-d" in sys.argv:
        config = {"tel_ip": "127.0.0.1", "tel_port": 9752}
    else:
        config = conf.get_config()
    tel = TeleCommunicator(config["tel_ip"], config["tel_port"])
    plot_frame()

    while goon:
        dec = tel.get_current_de()
        if dec is None: dec = 0.0
        han = tel.get_current_ha()
        if han is None: han = 0.0
        dwg = MountDrawing(han, dec)
        dwg.plotme()
        plt.pause(1)
        dwg.clear()
        plt.draw()
        pass

if __name__ == "__main__":
    main()
