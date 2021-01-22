"""
Widget ed utilities per GUI OPC
"""

import os
import math
import tkinter as tk

import astro

__version__ = "1.5"
__date__ = "dicembre 2020"
__author__ = "Luca Fini"

H1_FONT = "Helvetica 18 bold"
H2_FONT = "Helvetica 16 bold"
H3_FONT = "Helvetica 14 bold"
H4_FONT = "Helvetica 12 bold"
BD_FONT = "Helvetica 10 bold"
H12_FONT = "Helvetica 12"

#                 Button states
ON = "on"
OFF = "off"
GRAY = "gray"
GREEN = "green"
YELLOW = "yellow"
RED = "red"

#                 Button types
ONOFF = "onoff"
CIRCLE = "circle"
SQUARE = "square"
UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"

SHAPES = (ONOFF, CIRCLE, SQUARE, UP, DOWN, RIGHT, LEFT)
SIZES = (48, 64)

FOURCOLORS = (GRAY, GREEN, YELLOW, RED)

STATE_MAP = {ONOFF: (OFF, ON),
             CIRCLE: FOURCOLORS,
             LEFT: FOURCOLORS,
             RIGHT: FOURCOLORS,
             SQUARE: FOURCOLORS,
             DOWN: FOURCOLORS,
             UP: FOURCOLORS}

MAX = 9223372036854775807
MIN = -9223372036854775806

UP_IMAGE_DATA = """R0lGODlhCgAKAOMKAAAAAAEBAQQGCAUICwYJDAcKDgkOFAoPFgoQGAsRGP//////////////////
/////yH+EUNyZWF0ZWQgd2l0aCBHSU1QACH5BAEKAA8ALAAAAAAKAAoAAAQf8MlJKRp1ApBf2kS2
bdUxAqF2cpK5CtI6PkZg33YRAQA7"""

DOWN_IMAGE_DATA = """R0lGODlhCgAKAOMMAAAAAAYHCQQIDQcJDAcKDAgLDgkNEwkOFAoPFQoPFgwSGgwVIP//////////
/////yH+EUNyZWF0ZWQgd2l0aCBHSU1QACH5BAEKAA8ALAAAAAAKAAoAAAQfcIlJp3og6/ze2VnQ
YeD4GBthktyaZMXatTIyyPgTAQA7"""

PLUS_IMAGE_DATA = """
R0lGODdhDAAMAOeeAAAAAAABAQEBAAABBQABBgMEBgAFDAMFCAUHCAEJFAYJDgcLEgMMGQsNEAEQ
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
/////////////////////////////////////////////////////ywAAAAADAAMAAAIVQAxCRxI
ENOiS3cS3tmzR+GdJggT7gFhQ+EeiBY7zLCIkeEfjQwZQpzYoUOBBiVB/Bk5o2UDEC1nrIy4UCNH
mntsSsQokeLNkHv+AL24qInRo0iFBAQAOw=="""

MINUS_IMAGE_DATA = """
R0lGODdhDAAMAOMPACgoKDk5OWJhYGdnZmhnZnt7e4SEhLKysrOzs7S0tLe3t9PT09jY2NnZ2dra
2v///ywAAAAADAAMAAAEL1CtSasz6Oi9G+Yg84GbiJwoeohJALxwgJiEYN/DPJLrTpo8jSmVOjQK
hqRyqYgAADs="""


class IMGS:              # pylint: disable=R0903
    "Per la persistenza delle immagini"
    up_image = None
    down_image = None
    plus_image = None
    minus_image = None

class WidgetError(Exception):
    "Exception per errori dei widget"

class ToolTip:
    "Tooltip per widget"
    def __init__(self, widget, text='widget info', position="NW"):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.x_offset = 0
        self.y_offset = 0
        if "N" in position:
            self.y_offset -= 20
        if "W" in position:
            self.x_offset -= 45
        if "S" in position:
            self.y_offset += 20
        if "E" in position:
            self.x_offset += 25
        self.twdg = None

    def enter(self, _unused=None):
        "Chiamata quando il focus è sul relativo widget"
        xco = yco = 0
        xco, yco = self.widget.bbox("insert")[:2]
        xco += self.widget.winfo_rootx() + self.x_offset
        yco += self.widget.winfo_rooty() + self.y_offset
        # creates a toplevel window
        self.twdg = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.twdg.wm_overrideredirect(True)
        self.twdg.wm_geometry("+%d+%d" % (xco, yco))
        label = tk.Label(self.twdg, text=self.text, justify='left',
                         background='yellow', relief='solid', borderwidth=1,
                         font=("times", "10", "normal"))
        label.pack(ipadx=1)

    def close(self, _unused=None):
        "Rimuove tooltip"
        if self.twdg:
            self.twdg.destroy()

def down_image(mode):
    "crea immagine per freccia in giu"
    if mode.startswith("a"):
        if not IMGS.down_image:
            IMGS.down_image = tk.PhotoImage(data=DOWN_IMAGE_DATA)
        return IMGS.down_image
    if not IMGS.minus_image:
        IMGS.minus_image = tk.PhotoImage(data=MINUS_IMAGE_DATA)
    return IMGS.minus_image

def up_image(mode):
    "crea immagine per freccia in su"
    if mode.startswith("a"):
        if not IMGS.up_image:
            IMGS.up_image = tk.PhotoImage(data=UP_IMAGE_DATA)
        return IMGS.up_image
    if not IMGS.plus_image:
        IMGS.plus_image = tk.PhotoImage(data=PLUS_IMAGE_DATA)
    return IMGS.plus_image

class LabelFrame(tk.Frame):              # pylint: disable=R0901
    "Frame con etichetta e widget generico"
    def __init__(self, parent, label=None, label_side=tk.W,
                 label_font=H4_FONT, **kw):
        super().__init__(parent, **kw)
        self._side = label_side
        if label is not None:
            self.label = tk.Label(self, text=label, font=label_font)
        else:
            self.label = None
        self.widget = None

    def add_widget(self, widget, expand=None, fill=None):
        "Inserisce widget"
        if self.widget:
            raise WidgetError("Widget già definito")
        self.widget = widget
        if self._side == tk.N:
            if self.label:
                self.label.pack(side=tk.TOP, expand=expand, fill=fill)
            self.widget.pack(side=tk.TOP, expand=expand, fill=fill)
        elif self._side == tk.S:
            self.widget.pack(side=tk.TOP, expand=expand, fill=fill)
            if self.label:
                self.label.pack(side=tk.TOP, expand=expand, fill=fill)
        elif self._side == tk.E:
            self.widget.pack(side=tk.LEFT, expand=expand, fill=fill)
            if self.label:
                self.label.pack(side=tk.LEFT, expand=expand, fill=fill)
        else:
            if self.label:
                self.label.pack(side=tk.LEFT, expand=expand, fill=fill)
            self.widget.pack(side=tk.LEFT, expand=expand, fill=fill)

    def set_label(self, text):
        "Aggiorna testo della label"
        self.label.config(text=text)

class LabelRadiobutton(tk.Frame):              # pylint: disable=R0901
    "Radiobutton con label"
    def __init__(self, parent, label, variable, value):
        super().__init__(parent)
        self.button = tk.Radiobutton(self, variable=variable, value=value)
        self.button.pack(side=tk.LEFT)
        self.label = tk.Label(self, text=label, font=H4_FONT)
        self.label.pack(side=tk.LEFT)
        self.def_bg = self.label.cget("bg")

    def set_bg(self, color=None):
        "Imposta colore di fondo"
        if not color:
            color = self.def_bg
        self.config(bg=color)
        self.label.config(bg=color)
        self.button.config(bg=color)

class Controller(LabelFrame):              # pylint: disable=R0901
    "Widget per campo numerico con frecce +-"
    def __init__(self, parent, value=0, width=5, lower=MIN, upper=MAX,
                 font=H12_FONT, step=1, circular=False, mode="arrow", fmt="%d",
                 label=None, label_font=H4_FONT, label_side=tk.W, **kw):
        super().__init__(parent, label=label, label_font=label_font,
                         label_side=label_side, **kw)
        self.step = step
        self.value = value
        self.lower = lower
        self.upper = upper
        self.fmt = fmt
        self.circular = circular
        container = tk.Frame(self)
        self.entry = tk.Entry(container, width=width, font=font)
        self.entry.pack(side=tk.LEFT)
        btframe = tk.Frame(container)
        self.bup = tk.Button(btframe, image=up_image(mode), command=self.incr)
        self.bup.pack(side=tk.TOP)
        self.bdown = tk.Button(btframe, image=down_image(mode), command=self.decr)
        self.bdown.pack(side=tk.TOP)
        btframe.pack(side=tk.LEFT)
        self.add_widget(container)
        self.set(value)

    def config(self, **kw):
        "config reimplementation"
        if "state" in kw:
            self.entry.config(state=kw["state"])
            self.bup.config(state=kw["state"])
            self.bdown.config(state=kw["state"])
            del kw["state"]
        super().config(**kw)

    def set(self, value):
        "imposta valore Controller"
        if value > self.upper:
            if self.circular:
                value = self.lower
            else:
                value = self.upper
        elif value < self.lower:
            if self.circular:
                value = self.upper
            else:
                value = self.lower
        self.value = value
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.fmt%value)

    def get(self):
        "riporta valore Controller"
        try:
            value = int(self.entry.get())
        except Exception:
            self.set(self.value)
        else:
            if self.value != value:
                self.set(value)
        return float(self.entry.get())

    def incr(self):
        "incrementa valore Controller"
        newval = self.get()+self.step
        self.set(newval)

    def decr(self):
        "decrementa valore Controller"
        newval = self.get()-self.step
        self.set(newval)

class Announce(tk.Frame):              # pylint: disable=R0901
    "Classe per linee con scroll"
    def __init__(self, master, nlines, width=54, **kargs):
        "Costruttore"
        super().__init__(master, **kargs)
        self.lines = []
        while nlines:
            self.lines.append(Field(self, border=0, width=width,
                                    font=H12_FONT, expand=1, fill=tk.X))
            nlines -= 1
        for llne in self.lines:
            llne.pack(expand=1, fill=tk.X)
        self.nextid = 0

    def _scrollup(self):
        "Scroll lines up one step"
        for nline, dest in enumerate(self.lines[:-1]):
            src = self.lines[nline+1]
            text = src.cget("text")
            fgc = src.cget("fg")
            dest.config(text=text, fg=fgc)

    def writeline(self, line, fgcolor):
        "Aggiunge una linea"
        if self.nextid == len(self.lines):
            self._scrollup()
            self.nextid -= 1
        self.lines[self.nextid].config(text=line, fg=fgcolor)
        self.nextid += 1

    def clear(self):
        "Azzera il widget"
        for line in self.lines:
            line.config(text="")
        self.nextid = 0

class Icons:
    "Classe per la gestione di icone"
    def __init__(self):
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons")
        self.images = {}

    def get_icon(self, icon):
        "specifica icon: (shape, size, status)"
        name = "%s_%d_%s"%tuple(icon)
        if name not in self.images:
            try:
                self.images[name] = tk.PhotoImage(file=os.path.join(self.icon_path, name+".gif"))
            except:
                raise WidgetError("No such icon: %s"%str(icon))
        return self.images[name]

ICONS = Icons()

# Selettori tipo coordinate
HMS = 1
DMS = 2

class CoordEntry(tk.Frame):              # pylint: disable=R0901
    "Widget per coordinate"
    def __init__(self, parent, label, ctype, width=2, editable=True):
        super().__init__(parent)
        tk.Label(self, text=label).pack(side=tk.LEFT)
        self.ctype = ctype
        if ctype == HMS:
            seps = ("h", "m", "s")
        else:
            seps = ("°", "'", '"')
        state = "normal" if editable else "normal"
        self.deg = tk.Entry(self, width=width, state=state)
        self.deg.pack(side=tk.LEFT)
        tk.Label(self, text=seps[0]).pack(side=tk.LEFT)
        self.mnt = tk.Entry(self, width=2, state=state)
        self.mnt.pack(side=tk.LEFT)
        tk.Label(self, text=seps[1]).pack(side=tk.LEFT)
        self.sec = tk.Entry(self, width=2, state=state)
        self.sec.pack(side=tk.LEFT)
        tk.Label(self, text=seps[2]).pack(side=tk.LEFT)

    def value_dms(self):
        "Riporta valore campi: (deg, min, sec)"
        try:
            deg = int(self.deg.get())
            mnt = int(self.mnt.get())
            sec = int(self.sec.get())
        except Exception:
            return ()
        return (deg, mnt, sec)

    def value_rad(self):
        "Riporta valore campi in radianti"
        ret = self.value_dms()
        if ret:
            if self.ctype == HMS:
                return astro.hms2rad(*ret)          # pylint: disable=E1120
            return astro.dms2rad(*ret)              # pylint: disable=E1120
        return float("nan")

    def set(self, value):
        "Assegna il valore"
        self.clear()
        sign, ddd, mmm, sss = astro.float2ums(value)
        ssgn = "-" if sign < 0 else "+"
        self.deg.insert(0, ssgn+"%d"%int(ddd))
        self.mnt.insert(0, "%2.2d"%int(mmm))
        self.sec.insert(0, "%2.2d"%int(sss))

    def clear(self):
        "Azzera il widget"
        self.deg.delete(0, tk.END)
        self.mnt.delete(0, tk.END)
        self.sec.delete(0, tk.END)

class Led(tk.Frame):
    "Led di vari colori"
    def __init__(self, parent, border=2, color=None, size=10):
        if not color:
            color = parent["bg"]
        super().__init__(parent, width=size, height=size, border=border, bg=color, relief=tk.RAISED)

    def set(self, color):
        "Imposta colore del Led"
        self.config(bg=color)

class CButton(LabelFrame):              # pylint: disable=R0901
    "Bottone colorabile con etichetta opzionale"
    def __init__(self, parent, name, text="", color=None, font=H4_FONT,
                 width=None, command=None, padx=None, pady=None,
                 label=None, label_side=tk.W, label_font=H4_FONT, **kw):
        super().__init__(parent, label=label, label_side=label_side,
                         label_font=label_font, **kw)
        self.name = name
        if command:
            _command = lambda name=name: command(name)
        else:
            _command = None
        self.button = tk.Button(self, text=text, font=font, width=width,
                                padx=padx, pady=pady, command=_command)
        self.add_widget(self.button)
        if color:
            self.defc = color
        else:
            self.defc = self.cget("bg")
        self.set(self.defc)

    def set(self, color):
        "Imposta colore del bottone"
        if color:
            self.button.config(bg=color, activebackground=color)
        else:
            self.button.config(bg=self.defc, activebackground=self.defc)

    def clear(self):
        "Azzera  bottone"
        self.set(None)

class MButton(LabelFrame):              # pylint: disable=R0901
    "Bottone Multi-icona a piu stati con Label"
    def __init__(self, parent, name, shape, size, value=None,
                 label=None, label_side=tk.W, label_font=H4_FONT,
                 command=None, **kw):
        super().__init__(parent, label=label, label_side=label_side,
                         label_font=label_font, **kw)
        self.name = name
        self.status = 0
        self.shape = shape
        self.size = size
        self.states = STATE_MAP[shape]
        image0 = ICONS.get_icon((shape, size, self.states[0]))
        if command:
            widget = tk.Button(self, image=image0,
                               command=lambda name=name: command(name))
        else:
            widget = tk.Label(self, image=image0)
        self.add_widget(widget)
        if value:
            self.set(value)
    def nstates(self):
        "Riporta numero di stati definiti"
        return len(self.states)

    def get(self):
        "Riporta stato corrente"
        return self.status

    def set(self, status):
        "Imposta stato del bottone"
        if isinstance(status, str):
            idx = self.states.index(status)
        else:
            if self.shape == ONOFF:
                idx = 1 if status else 0
            else:
                idx = status
        self.status = idx
        self.widget.config(image=ICONS.get_icon((self.shape, self.size, self.states[idx])))

    def clear(self):
        "Azzera bottone"
        self.set(0)

class FrameTitle(tk.Frame):              # pylint: disable=R0901
    "Frame con titolo"
    def __init__(self, parent, title, font=H1_FONT, **kw):
        super().__init__(parent, padx=5, pady=5, **kw)
        self.title = tk.Label(self, text=title, font=font)
        self.title.pack(expand=1, fill=tk.X)
        self.body = tk.Frame(self)
        self.body.pack(expand=1, fill=tk.BOTH)

class Field(LabelFrame):              # pylint: disable=R0901
    "Widget per display di stringa generica"
    def __init__(self, parent, bg="black", fg="lightgreen",
                 font="TkDefaultFont", width=10, text="",
                 label=None, label_side=tk.W, label_font=H4_FONT, **kw):
        super().__init__(parent, label=label, label_side=label_side,
                         label_font=label_font, **kw)
        self.add_widget(tk.Label(self, text=text, bg=bg, fg=fg, width=width,
                                 font=font, border=1, relief=tk.SUNKEN))

    def set(self, text, **kw):
        "Imposta valore campo"
        if not text:
            self.clear()
        else:
            self.widget.config(text=text, **kw)

    def clear(self):
        "Azzera campo"
        self.widget.config(text="")

class Number(Field):              # pylint: disable=R0901
    "Widget per display di valore numerico"
    def __init__(self, parent, fmt="%d", **kw):
        super().__init__(parent, **kw)
        self._format = fmt
        self.value = None

    def set(self, value, **kw):
        "Imposta valore del campo"
        if value is None or math.isnan(value):
            self.clear()
            self.value = None
        else:
            self.value = value
            svalue = self._format%value
            Field.set(self, svalue, **kw)

    def get(self):
        "Riporta valore del campo"
        return self.value

class Coord(Field):              # pylint: disable=R0901
    "Classe per display di coordinata"
    def __init__(self, parent, value=None, **kw):
        super().__init__(parent, **kw)
        self.set(value)

    def set(self, value):
        "Imposta valore"
        try:
            dms = astro.float2ums(value)
        except:
            self.value = None
            self.clear()
            return
        self.value = value
        ssgn = "-" if dms[0] < 0 else "+"
        if value == 0:
            ssgn = " "
        strv = "%s%d:%2.2d:%2.2d"%(ssgn, dms[1], dms[2], dms[3])
        Field.set(self, strv)

    def get(self):
        "Riporta valore numerico widget"
        return self.value

class MyToplevel(tk.Toplevel):
    "Toplevel posizionabile con metodo quit"
    def quit(self):
        "Chiamato dal widget interno"
        self.destroy()

    def position(self, xpp, ypp):
        "imposta posizione del widget"
        xp0 = self.master.winfo_x()+xpp
        yp0 = self.master.winfo_y()+ypp
        self.geometry("+%d+%d"%(xp0, yp0))

class Message(tk.Frame):              # pylint: disable=R0901
    "Display di messaggio"
    def __init__(self, parent, msg):
        super().__init__(parent)
        lines_len = tuple(len(x) for x in msg.split("\n"))
        n_lines = len(lines_len)+1
        n_chars = max(lines_len)+2
        self.body = tk.Text(self, height=n_lines, width=n_chars,
                            padx=5, pady=5, border=3, relief=tk.RIDGE)
        self.body.insert(tk.END, msg)
        self.body.pack()
        self.status = None

    def _quit(self, _unused):
        self.master.quit()

class WarningMsg(Message):              # pylint: disable=R0901
    "Display di messaggio informativo"
    def __init__(self, parent, msg):
        super().__init__(parent, msg)
        CButton(self, "chiude", text="Chiudi", color="light sky blue", command=self._quit).pack()

class YesNo(Message):              # pylint: disable=R0901
    "Display di messaggio con scelta opzioni Si/No"
    def __init__(self, parent, msg):
        super().__init__(parent, msg)
        bot_frame = tk.Frame(self)
        tk.Button(bot_frame, text="Si", command=lambda x=True: self._quit(x)).pack(side=tk.LEFT)
        tk.Button(bot_frame, text="No", command=lambda x=False: self._quit(x)).pack(side=tk.LEFT)
        bot_frame.pack()

    def _quit(self, isyes):
        self.status = isyes
        self.master.quit()

class SelectionMsg(Message):              # pylint: disable=R0901
    "Display di messaggio con scelta opzioni"
    def __init__(self, parent, msg, choices=None):
        super().__init__(parent, msg)
        bot_frame = tk.Frame(self)
        for nbutt, choice in enumerate(choices):
            tk.Button(bot_frame, text=choice,
                      command=lambda x=nbutt: self._quit(x)).pack(side=tk.LEFT)
        bot_frame.pack()

    def _quit(self, nbutt):
        self.status = nbutt
        self.master.quit()

class HSpacer(tk.Label):              # pylint: disable=R0901
    "Spaziatore orizzontale: se nspaces=0, riempie tutto lo spazio disponibile"
    def __init__(self, parent, nspaces=0):
        if nspaces:
            spaces = " "*nspaces
            super().__init__(parent, text=spaces)
            self.pack(side=tk.LEFT)
        else:
            super().__init__(parent, text=" ")
            self.pack(side=tk.LEFT, expand=1, fill=tk.X)

def main():
    "Procedura di test"
    def premuto_bottone(b_name):
        "Bottone premuto"
        print("Premuto bottone:", b_name)
    root = tk.Tk()
    sinistra = FrameTitle(root, "Vari bottoni", border=2, relief=tk.RIDGE)
    ToolTip(sinistra.title, text="Tooltip del titolo di sinistra")
    avar = tk.IntVar()
    llf = tk.Frame(sinistra)
    LabelRadiobutton(llf, "", avar, 2).pack(side=tk.LEFT)
    LabelRadiobutton(llf, "Bottone 'radio'", avar, 1).pack(side=tk.LEFT)
    llf.pack()
    # Esempi di vari tipi di bottone
    MButton(sinistra, "b1", "circle", 32,
            label="Bottone circolare ", command=premuto_bottone).pack()
    MButton(sinistra, "b2", "square", 32,
            value=RED, label="Bottone quadrato inattivo ").pack()
    MButton(sinistra, "b3", "up", 32, value=GREEN, label=" Etichetta a destra",
            command=premuto_bottone, label_side=tk.E).pack()
    MButton(sinistra, "b4", "left", 32, value=YELLOW, label_side=tk.N,
            label="Etichetta sopra", command=premuto_bottone).pack()
    CButton(sinistra, "b5", color="lightgreen", text="Pigiami",
            label="Bottone colorabile ", command=premuto_bottone).pack()
    sinistra.pack(side=tk.LEFT, anchor=tk.N)
    # Esempi di altri widget
    destra = FrameTitle(root, "Altri widget", border=2, relief=tk.RIDGE)
    # Controller con frecce
    Controller(destra, label="Controller 1 ",
               lower=-10, upper=10, circular=True).pack()
    # Controller +/-
    Controller(destra, label="Controller 2 ", mode="plus",
               lower=-10, upper=10, circular=True).pack()
    # Campo per visualizzazione stringhe
    fld = Field(destra, label="Campo generico: ", label_side=tk.W)
    fld.pack()
    fld.set("Tarabaralla")
    # Campo per visualizzazione Valori numerici
    fld = Number(destra, label="Campo numerico: ", fmt="%.2f")
    fld.pack()
    fld.set(1234)
    crd = Coord(destra, label="Coordinata: ")
    crd.pack()
    crd.set(-137.34)
    leds = tk.Frame(destra)
    tk.Label(leds, text="Vari led colorati: ").pack(side=tk.LEFT)
    Led(leds, color="blue").pack(side=tk.LEFT)
    Led(leds, color="white", size=15).pack(side=tk.LEFT)
    Led(leds, size=20).pack(side=tk.LEFT)
    Led(leds, color="yellow", size=25).pack(side=tk.LEFT)
    Led(leds, color="red", size=30).pack(side=tk.LEFT)
    leds.pack()
    destra.pack(side=tk.LEFT, anchor=tk.N)
    root.mainloop()

if __name__ == "__main__":
    main()
