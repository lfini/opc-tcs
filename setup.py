"""
setup.py - Installatore per Windows

Normalmente lanciato da setup.bat
"""

import os
import sys
import shutil

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

NO_WINSHELL = """
Occorre installare il package python "winshell"
"""

NO_WIN32COM = """
Occorre installare il package python "win32com"
"""

if not (WINSHELL and WIN32COM):
    if not WINSHELL:
        print(NO_WINSHELL)
    if not WIN32COM:
        print(NO_WIN32COM)
    sys.exit()

HOMEDIR = os.path.expanduser("~")
DESTDIR = os.path.join(HOMEDIR, "dtracker")
ICONDIR = os.path.join(DESTDIR, "icons")
SCRIPT = "dtracker.py"
ICONFILE = "domec128.ico"

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

PYTHONW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
SCRIPTPATH = os.path.join(DESTDIR, SCRIPT)
DESKTOP = winshell.desktop()                # genera link in Desktop
SHELL = Dispatch('WScript.Shell')
SHORTC = SHELL.CreateShortCut(os.path.join(DESKTOP, "DTracker.lnk"))
SHORTC.Targetpath = PYTHONW
SHORTC.Arguments = SCRIPTPATH
SHORTC.WorkingDirectory = DESTDIR
SHORTC.IconLocation = os.path.join(DESTDIR, ICONFILE)
SHORTC.save()
print("Generato shortcut su Desktop")
