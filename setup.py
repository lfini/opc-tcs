"""
setup.py - Installatore per Windows

Normalmente lanciato da setup.bat
"""

import os
import sys
import shutil
import tkinter as tk
from widgets import WarningMsg, YesNo

try:
    import winshell
except ImportError:
    WINSHELL = False
else:
    WINSHELL = True

try:
    from win32com.client import Dispatch
except ImportError:
    WIN32COM = False
else:
    WIN32COM = True

TITLE = "DTracker-installazione"

NO_WIN32COM = """

 Prima di procedere, è necessario installare il package
 python "win32com"

 Solitamente è sufficente il comando:

       python -m pip install win32com

"""

NO_WINSHELL = """
Non è installato il modulo python "winshell".

La procedura di installazione può proseguire egualmente, ma non sarà
creato lo 'shortcut' di start sul desktop. 

Se rispondi "SI" alla domanda, sarà necessario creare manualmente lo
'shortcut' specificando come destinazione il comando completo: 

   %s  %s

ed il percorso dell'icona:

   %s

In alternativa, puoi rispondere "NO" per interrompere l'installazione
e riprenderla dopo aver installato il modulo winshell con il comando:

         python -m pip install winshell


Vuoi proseguire con l'installazione?
"""

OK = """
Istallazione terminata (la cartella di installazione
può essere cancellata)
"""

SHORTCUT = """Lo 'shortcut' per il lancio della procedura
dovrà essere creato manualmente
"""

HOMEDIR = os.path.expanduser("~")
DESTDIR = os.path.join(HOMEDIR, "dtracker")
ICONDIR = os.path.join(DESTDIR, "icons")
SCRIPT = "dtracker.py"
ICONFILE = "domec128.ico"
SCRIPTPATH = os.path.join(DESTDIR, SCRIPT)
ICONPATH = os.path.join(DESTDIR, ICONFILE)
PYTHONW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

def center(theroot):
    "Centra finestra nello schermo"
    rwdt = theroot.winfo_width()
    rhgt = theroot.winfo_height()
    xps = int((theroot.winfo_screenwidth()-rwdt)/2)
    yps = int((theroot.winfo_screenheight()-rhgt)/2)
    theroot.geometry("%dx%d+%d+%d"%(rwdt, rhgt, xps, yps))

def message(msg):
    "Segnala mancanza win32com"
    root = tk.Tk()
    root.title(TITLE)
    root.quit = root.destroy
    wdg = WarningMsg(root, msg)
    wdg.pack()
    root.after(20, center, root)
    root.mainloop()
    
def nowinshell():
    "Segnala mancanza shell"
    root = tk.Tk()
    root.title(TITLE)
    root.quit = root.destroy
    wdg = YesNo(root, NO_WINSHELL%(PYTHONW, SCRIPTPATH, ICONPATH))
    wdg.pack()
    root.after(20, center, root)
    root.mainloop()
    return wdg.status
    
if not WIN32COM:
    message(NO_WIN32COM)
    sys.exit()

if not WINSHELL:
    ret = nowinshell()
    if not ret:
        sys.exit()

os.makedirs(ICONDIR, exist_ok=True)

SOURCEFILES = [x for x in os.listdir(".") if x.endswith(".py")]
ICONFILES = [os.path.join("icons", x) for x in os.listdir("icons")]
DATAFILES = ["dometab_e.p", "dometab_w.p", ICONFILE]

for src in SOURCEFILES+DATAFILES:           # Installa scripts e file dati
    shutil.copy(src, DESTDIR)
print("Copiati scripts e file dati")

for src in ICONFILES:                       # Installa icone
    shutil.copy(src, ICONDIR)
print("Copiati file icone")

if WINSHELL:
    DESKTOP = winshell.desktop()                # genera link in Desktop
    SHELL = Dispatch('WScript.Shell')
    SHORTC = SHELL.CreateShortCut(os.path.join(DESKTOP, "DTracker.lnk"))
    SHORTC.Targetpath = PYTHONW
    SHORTC.Arguments = SCRIPTPATH
    SHORTC.WorkingDirectory = DESTDIR
    SHORTC.IconLocation = ICONPATH
    SHORTC.save()
    print("Generato shortcut su Desktop")
    message(OK)
else:
    message(OK+SHORTCUT)
