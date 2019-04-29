"""
Widget ed utilities per GUI OPC
"""

import os
import math
import tkinter as tk

import astro

__version__ = "1.2"
__date__ = "ottobre 2018"
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

UP_IMAGE = None
DOWN_IMAGE = None

class WidgetError(Exception):
    "Exception per errori dei widget"
    pass

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

def down_image():
    "crea immagine per freccia in giu"
    global DOWN_IMAGE
    if not DOWN_IMAGE:
        DOWN_IMAGE = tk.PhotoImage(data=DOWN_IMAGE_DATA)
    return DOWN_IMAGE

def up_image():
    "crea immagine per freccia in su"
    global UP_IMAGE
    if not UP_IMAGE:
        UP_IMAGE = tk.PhotoImage(data=UP_IMAGE_DATA)
    return UP_IMAGE

class _LabelFrame(tk.Frame):
    "Frame con etichetta e widget generico (uso locale)"
    def __init__(self, parent, label=None, label_side=tk.W,
                 label_font=H4_FONT, **kw):
        tk.Frame.__init__(self, parent, **kw)
        self._side = label_side
        if label is not None:
            self.label = tk.Label(self, text=label, font=label_font)
        else:
            self.label = None
        self.wdg = None

    def add_widget(self, widget, expand=None, fill=None):
        "Inserisce widget"
        if self.wdg:
            raise WidgetError("Widget già definito")
        self.wdg = widget
        if self._side == tk.N:
            if self.label:
                self.label.pack(side=tk.TOP, expand=expand, fill=fill)
            self.wdg.pack(side=tk.TOP, expand=expand, fill=fill)
        elif self._side == tk.S:
            self.wdg.pack(side=tk.TOP, expand=expand, fill=fill)
            if self.label:
                self.label.pack(side=tk.TOP, expand=expand, fill=fill)
        elif self._side == tk.E:
            self.wdg.pack(side=tk.LEFT, expand=expand, fill=fill)
            if self.label:
                self.label.pack(side=tk.LEFT, expand=expand, fill=fill)
        else:
            if self.label:
                self.label.pack(side=tk.LEFT, expand=expand, fill=fill)
            self.wdg.pack(side=tk.LEFT, expand=expand, fill=fill)

    def set_label(self, text):
        "Aggiorna testo della label"
        self.label.config(text=text)


class LabelRadiobutton(tk.Frame):
    "Radiobutton con label"
    def __init__(self, parent, label, variable, value):
        tk.Frame.__init__(self, parent)
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

class Controller(_LabelFrame):
    "Widget per campo numerico con frecce +-"
    def __init__(self, parent, value=0, width=5, lower=MIN, upper=MAX,
                 font=H12_FONT, step=1, circular=False,
                 label=None, label_font=H4_FONT, label_side=tk.W, **kw):
        _LabelFrame.__init__(self, parent, label=label, label_font=label_font,
                             label_side=label_side, **kw)
        self.step = step
        self.value = value
        self.lower = lower
        self.upper = upper
        self.circular = circular
        container = tk.Frame(self)
        self.entry = tk.Entry(container, width=width, font=font)
        self.entry.pack(side=tk.LEFT)
        btframe = tk.Frame(container)
        bup = tk.Button(btframe, image=up_image(), command=self.incr)
        bup.pack(side=tk.TOP)
        bdown = tk.Button(btframe, image=down_image(), command=self.decr)
        bdown.pack(side=tk.TOP)
        btframe.pack(side=tk.LEFT)
        self.add_widget(container)
        self.set(value)

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
        self.entry.insert(0, int(self.value))

    def get(self):
        "riporta valore Controller"
        try:
            value = int(self.entry.get())
        except Exception:
            self.set(self.value)
        else:
            if self.value != value:
                self.set(value)
        return int(self.entry.get())

    def incr(self):
        "incrementa valore Controller"
        newval = self.get()+self.step
        self.set(newval)

    def decr(self):
        "decrementa valore Controller"
        newval = self.get()-self.step
        self.set(newval)

class Announce(tk.Frame):
    "Classe per linee con scroll"
    def __init__(self, master, nlines, width=54, **kargs):
        "Costruttore"
        tk.Frame.__init__(self, master, **kargs)
        self.lines = []
        while nlines:
            self.lines.append(Field(self, border=0, width=width, font=H12_FONT, expand=1, fill=tk.X))
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

class CoordEntry(tk.Frame):
    "Widget per coordinate"
    def __init__(self, parent, label, ctype, width=2, editable=True):
        tk.Frame.__init__(self, parent)
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
                return astro.hms2rad(*ret)
            return astro.dms2rad(*ret)
        return float("nan")

    def set(self, value, _sign=False):
        "Assrgna il valore"
        self.clear()
        ddd, mmm, sss = astro.float2ums(value)
        if _sign:
            self.deg.insert(0, "%+d"%int(ddd))
        else:
            self.deg.insert(0, "%d"%int(ddd))
        self.mnt.insert(0, "%2.2d"%int(mmm))
        self.sec.insert(0, "%2.2d"%int(sss))

    def clear(self):
        "Azzera il widget"
        self.deg.delete(0, tk.END)
        self.mnt.delete(0, tk.END)
        self.sec.delete(0, tk.END)

class CButton(_LabelFrame):
    "Bottone colorabile con etichetta opzionale"
    def __init__(self, parent, name, text="", color=None, font=H4_FONT,
                 width=None, command=None, padx=None, pady=None,
                 label=None, label_side=tk.W, label_font=H4_FONT, **kw):
        _LabelFrame.__init__(self, parent, label=label,
                             label_side=label_side, label_font=label_font, **kw)
        self.name = name
        if command:
            _command = lambda name=name: command(name)
        else:
            _command = None
        self.button = tk.Button(self, text=text, font=font, width=width,
                                padx=padx, pady=pady, command=_command)
        self.defc = self.cget("bg")
        self.add_widget(self.button)
        self.set(color)

    def set(self, color):
        "Imposta colore del bottone"
        if color:
            self.button.config(bg=color, activebackground=color)
        else:
            self.button.config(bg=self.defc, activebackground=self.defc)

    def clear(self):
        "Azzera  bottone"
        self.set(None)

class MButton(_LabelFrame):
    "Bottone Multi-icona a piu stati con Label"
    def __init__(self, parent, name, shape, size, value=None,
                 label=None, label_side=tk.W, label_font=H4_FONT,
                 command=None, **kw):
        _LabelFrame.__init__(self, parent, label=label,
                             label_side=label_side, label_font=label_font, **kw)
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
        self.wdg.config(image=ICONS.get_icon((self.shape, self.size, self.states[idx])))

    def clear(self):
        "Azzera bottone"
        self.set(0)

class FrameTitle(tk.Frame):
    "Frame con titolo"
    def __init__(self, parent, title, font=H1_FONT, **kw):
        tk.Frame.__init__(self, parent, padx=5, pady=5, **kw)
        self.title = tk.Label(self, text=title, font=font)
        self.title.pack(expand=1, fill=tk.X)
        self.body = tk.Frame(self)
        self.body.pack(expand=1, fill=tk.BOTH)

class Field(_LabelFrame):
    "Widget per display di stringa generica"
    def __init__(self, parent, bg="black", fg="lightgreen",
                 font="TkDefaultFont", width=10, text="",
                 label=None, label_side=tk.W, label_font=H4_FONT,
                 expand=None, fill=None, **kw):
        _LabelFrame.__init__(self, parent, label=label,
                             label_side=label_side, label_font=label_font, **kw)
        self.add_widget(tk.Label(self, text=text, bg=bg, fg=fg, width=width,
                                 font=font, border=1, relief=tk.SUNKEN))

    def set(self, text):
        "Imposta valore campo"
        if not text:
            self.clear()
        else:
            self.wdg.config(text=text)

    def clear(self):
        "Azzera campo"
        self.wdg.config(text="")

class Number(Field):
    "Widget per display di valore numerico"
    def __init__(self, parent, _format="%d", **kw):
        Field.__init__(self, parent, **kw)
        self._format = _format
        self.value = None

    def set(self, value):
        "Imposta valore del campo"
        if value is None or math.isnan(value):
            self.clear()
            self.value = None
        else:
            self.value = value
            svalue = self._format%value
            Field.set(self, svalue)

    def get(self):
        "Riporta valore del campo"
        return self.value

class Coord(Field):
    "Classe per display di coordinata"
    def __init__(self, parent, value=None, **kw):
        Field.__init__(self, parent, **kw)
        self.set(value)

    def set(self, value):
        "Imposta valore"
        try:
            dms = astro.float2ums(value)
        except:
            value = None
        self.value = value
        if value is None:
            self.clear()
            return
        strv = "%d:%2.2d:%2.2d"%dms
        Field.set(self, strv)

    def get(self):
        "Riporta valore numerico widget"
        return self.value

class WarningMsg(tk.Frame):
    "Display di messaggio"
    def __init__(self, parent, msg):
        self.parent = parent
        tk.Frame.__init__(self, parent)
        lines_len = tuple(len(x) for x in msg.split("\n"))
        n_lines = len(lines_len)+1
        n_chars = max(lines_len)+2
        self.body = tk.Text(self, height=n_lines, width=n_chars,
                            padx=5, pady=5, border=3, relief=tk.RIDGE)
        self.body.insert(tk.END, msg)
        self.body.pack()
        CButton(self, "chiude", text="Chiudi", color="light sky blue", command=self._quit).pack()

    def _quit(self, _unused):
        self.master.quit()

class HSpacer(tk.Label):
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
    # Controller
    Controller(destra, label="Controller ",
               lower=-10, upper=10, circular=True).pack()
    # Campo per visualizzazione stringhe
    fld = Field(destra, label="Campo generico: ", label_side=tk.W)
    fld.pack()
    fld.set("Tarabaralla")
    # Campo per visualizzazione Valori numerici
    fld = Number(destra, label="Campo numerico: ", _format="%.2f")
    fld.pack()
    fld.set(1234)
    destra.pack(side=tk.LEFT, anchor=tk.N)
    root.mainloop()

if __name__ == "__main__":
    main()
