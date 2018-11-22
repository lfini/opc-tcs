"""
Funzioni di comunicazione per GUI controllo cupola OPC

Invio comandi manuali al server cupola

      python domecomm.py [-d]

Dove:
      -d  Collegamento al simulatore (IP: 127.0.0.1, Port: 9752)

"""

import sys
import json
import socket
import configure as conf

__version__ = "1.2"
__date__ = "Maggio 2018"
__author__ = "Luca Fini"

class DomeCommands:
    "Definizione comandi per il controllo della cupola"
                        # COMANDI
    STAT = "STAT"       # Richesta stato
    LPON = "LPON"       # Luci pricipali ON
    LPOF = "LPOF"       # Luci pricipali OFF
    LNON = "LNON"       # Luci notturne ON
    LNOF = "LNOF"       # Luci notturne OFF
    LEFT = "LEFT"       # Muove cupola a sinistra (senso orario)
    RGHT = "RGHT"       # Muove cupola a destra (senso antiorario)
    SYNC = "SYNC"       # Sincronizzazione cupola
    GOTO = "GOTO"       # Porta cupola in posizione (argomento in gradi)
    SETZ = "SETZ"       # Imposta posizione cupola (argomento in gradi)
    STOP = "STOP"       # Ferma movimento cupola
    OPEN = "OPEN"       # Apri vano osservazione
    CLOS = "CLOS"       # Chiudi vano osservazione

class DomeErrors:
    "Codici di stato"
    ERR = "ERR:"   # Segnala errore grave, es: comando inesistente
    WNG = "WNG:"   # Segnala errore non grave, es: comando di stop
                   # ricevuto a cupola ferma
    OK = "OK_:"    # Comando accettato. Nel caso del comando STAT è seguito
                   # dai dati (vedi sotto)

class StatiLuce:
    "Definizione stati per luci"
    ON = 1
    OFF = 0

class StatiMovimento:
    "Definizione stati per rotazione cupola"
    LEFT = -1
    RIGHT = 1
    STOP = 0

class StatiVano:
    "Definizione stati per vano osservazione"
    ERROR = -1
    CLOSED = 0
    OPENING = 1
    OPEN = 2
    CLOSING = 3

class StatiSync:
    "Definizione stato sincronizzazione"
    NOTSYNC = 0
    SYNCING = 1
    INSYNC = 2

class DomeCommunicator:
    "Gestione comunicazione con server cupola"
    @staticmethod
    def is_notok(line):
        "test se linea è error o warning"
        if line:
            return line[:4] != DomeErrors.OK
        return True

    @staticmethod
    def is_ok(line):
        "test se linea è non errore o warning"
        if line:
            return line[:4] == DomeErrors.OK
        return False

    @staticmethod
    def is_error(line):
        "test se linea è errore"
        if line:
            return line[:4] == DomeErrors.ERR
        return False

    @staticmethod
    def is_warning(line):
        "test se linea è warning"
        if line:
            return line[:4] == DomeErrors.WNG
        return False

    def __init__(self, ipadr, port, timeout=0.2):
        "Costruttore"
        self.connected = False
        self.ipadr = ipadr
        self.port = port
        self.timeout = timeout

    def send_command(self, command):
        "Invio comandi"
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.settimeout(self.timeout)
        try:
            skt.connect((self.ipadr, self.port))
        except IOError:
            self.connected = False
            return None
        self.connected = True
        cmd_term = command+"\n"
        try:
            skt.send(cmd_term.encode("ascii"))
        except socket.timeout:
            skt.close()
            return None
        skt.shutdown(1)
        data = bytes()
        while True:
            try:
                ret = skt.recv(1024)
            except Exception:
                ret = bytes()
            if not ret:
                break
            data += ret
        skt.close()
        if data:
            line = data.decode("ascii").strip()
        else:
            line = None
        return line

    def get_hw_status(self):
        "Comando lettura stato"
        ret = self.send_command(DomeCommands.STAT)
        try:
            data = json.loads(ret[4:])
        except Exception:
            data = {}
        return data

    def main_light_on(self):
        "Comando accensione luce principale"
        ret = self.send_command(DomeCommands.LPON)
        return self.is_ok(ret)

    def main_light_off(self):
        "Comando Spengimento luce principale"
        ret = self.send_command(DomeCommands.LPOF)
        return self.is_ok(ret)

    def night_light_on(self):
        "Comando accensione luce notturna"
        ret = self.send_command(DomeCommands.LNON)
        return self.is_ok(ret)

    def night_light_off(self):
        "Comando Spengimento luce principale"
        ret = self.send_command(DomeCommands.LNOF)
        return self.is_ok(ret)

    def go_left(self):
        "Comando rotazione cupola a sinistra"
        ret = self.send_command(DomeCommands.LEFT)
        return self.is_ok(ret)

    def go_right(self):
        "Comando rotazione cupola a destra"
        ret = self.send_command(DomeCommands.RGHT)
        return self.is_ok(ret)

    def sync(self):
        "Comando esecuzione homing"
        ret = self.send_command(DomeCommands.SYNC)
        return self.is_ok(ret)

    def setz(self, azimuth):
        "Forza azimuth cupola"
        azm = "%d"%azimuth
        ret = self.send_command(DomeCommands.SETZ+":"+azm)
        return self.is_ok(ret)

    def goto(self, pos):
        "Comando esecuzione goto"
        ret = self.send_command(DomeCommands.GOTO+":"+str(pos))
        return self.is_ok(ret)

    def do_stop(self):
        "Comando stop movimento cupola"
        ret = self.send_command(DomeCommands.STOP)
        return self.is_ok(ret)

    def do_open(self):
        "Comando apertura vano osservazione"
        ret = self.send_command(DomeCommands.OPEN)
        return self.is_ok(ret)

    def do_close(self):
        "Comando chiusura vano osservazione"
        ret = self.send_command(DomeCommands.CLOS)
        return self.is_ok(ret)

USAGE = """
Comandi definiti:
    >      Movimento a destra (orario)
    <      Movimento a sinistra (antiorario)
    S      Stop
    G nnn  Goto
    I      Interroga stato
    Z      Imposta valore azimuth
    Y      Sync
    Q      Quit
"""

def main():
    "Programma per uso manuale (e test)"

    def value(line):
        "Verifica argomento"
        try:
            val = int(line.split()[1])
        except Exception:
            print("Valore errato!")
            val = None
        return val

    if '-h' in sys.argv:
        print(__doc__)
        sys.exit()

    if '-d' in sys.argv:
        config = {"dome_ip": "127.0.0.1",
                  "dome_port": 9752,
                  "debug": 1}
    else:
        config = conf.get_config()
    if not config:
        print("File di configurazione inesistente!")
        print("occorre definirlo con:")
        print()
        print("   python cupola.py -c")
        sys.exit()

    dcom = DomeCommunicator(config["dome_ip"], config["dome_port"])

    while True:
        answ = input("Comando (? per aiuto): ")
        if answ:
            cmd = answ[0].upper()
            if cmd == "<":
                dcom.go_left()
            elif cmd == ">":
                dcom.go_right()
            elif cmd == "S":
                dcom.do_stop()
            elif cmd == "G":
                val = value(answ)
                if val is not None:
                    dcom.goto(val)
            elif cmd == "I":
                ret = dcom.get_hw_status()
                for key, val in ret.items():
                    print(" %s:"%key, val)
            elif cmd == "Y":
                dcom.sync()
            elif cmd == "Z":
                val = value(answ)
                if val is not None:
                    dcom.setz(val)
            elif cmd == "?":
                print(USAGE)
            elif cmd == "Q":
                break
            else:
                print("Comando errato:", answ)
                print("Usa: ? per elenco dei comandi")

if __name__ == "__main__":
    main()
