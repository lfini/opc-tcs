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
creato il collegamento di start sul desktop. 

Se rispondi "SI" alla domanda, sarà necessario creare manualmente il
collegamento (riceverai istruzioni al termine dell'istallazione).

In alternativa (scelta consigliata), puoi rispondere "NO" per interrompere
l'installazione e riprenderla dopo aver installato il modulo winshell
con il comando:

         python -m pip install winshell


Vuoi proseguire con l'installazione?
"""

OK = """
Istallazione terminata (la cartella di installazione
può essere cancellata)
"""

SHORTCUT = """
Per creare il collegamento per il lancio della procedura, occorre cliccare in un
punto qualunque dello schermo e scegliere:  nuovo -> collegamento.

Nel campo "Percorso" deve essere impostato il comando completo:

   %s  %s

Poi premere "Avanti" e immettere il nome (ad es.: DTracker)

Infine premere "Fine"

Volendo impostare anche l'icona specifica, cliccare con il tasto destro sul
collegamento e scegliere "Proprietà" e poi "Cambia icona".

Il percorso dell'icona da specificare è:

   %s

NOTA: per rivedere questo messaggio cliccare su "collegamento.bat"
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
    wdg = YesNo(root, NO_WINSHELL)
    wdg.pack()
    root.after(20, center, root)
    root.mainloop()
    return wdg.status

if "-s" in sys.argv:
    message(SHORTCUT%(PYTHONW, SCRIPTPATH, ICONPATH))
    sys.exit()
    
if not WIN32COM:
    message(NO_WIN32COM)
    sys.exit()

if not WINSHELL:
    ret = nowinshell()
    if not ret:
        sys.exit()

os.makedirs(ICONDIR, exist_ok=True)

SOURCEFILES = [os.path.join("dist", x) for x in os.listdir("dist") if os.path.splitext(x)[1] in (".py", ".ico", ".p")]
ICONFILES = [os.path.join("icons", x) for x in os.listdir("icons")]

for src in SOURCEFILES:                      # Installa scripts e file dati
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
    print("Generato collegamento su Desktop")
    message(OK)
else:
    message(OK+SHORTCUT%(PYTHONW, SCRIPTPATH, ICONPATH))
