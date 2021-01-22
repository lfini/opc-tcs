"""
Prove driver ASCOM di OCS-III
"""

import win32com.client as wcl

# Dome attributes

# Altitude
# AtHome
# AtPark
# Azimuth
# CanFindHome
# CanPark
# CanSetAltitude
# CanSetAzimuth
# CanSetPark
# CanSetShutter
# CanSlave
# CanSyncAzimuth
# Connected
# Description
# DriverInfo
# DriverVersion
# InterfaceVersion
# Name
# ShutterStatus
# Slaved
# Slewing
# SupportedActions


# Dome Methods

# AbortSlew
# Action
# Choose
# CloseShutter
# CommandBlind
# CommandBool
# CommandString
# Dispose
# FindHome
# OpenShutter
# Park
# SetPark
# SetupDialog
# SlewToAltitude
# SlewToAzimuth
# SyncToAzimuth


HELP = """
Comandi:

    ab - AbortSlew
    cl - CloseShutter
    di - Dispose
    fi - FindHome
    op - OpenShutter
    pa - Park
    sp - SetPark
    st - SlewToAltitude
    sa - SlewToAzimuth
    sy - SyncToAzimuth
"""
def get_val(answ):
    "estrae valore da linea di comando"
    try:
        aaa = answ.split()
        val = "%2f"%aaa[1]
    except:
        val = 0
    return val


def main():
    "main ...."
    dome = wcl.Dispatch("OCS.Dome")

# Get all available info:

    print("\nInformazioni generali:")
    print("  Description:", dome.Description)
    print("  DriverInfo:", dome.DriverInfo)
    print("  DriverVersion:", dome.DriverVersion)
    print("  InterfaceVersion:", dome.InterfaceVersion)
    print("  Name:", dome.Name)


    print("\nOperazioni supportate:")

    print("  Connected:", "SI" if dome.Connected else "NO")
    print("  CanFindHome:", "SI" if dome.CanFindHome else "NO")
    print("  CanPark:", "SI" if dome.CanPark else "NO")
    print("  CanSetAltitude:", "SI" if dome.CanSetAltitude else "NO")
    print("  CanSetAzimuth:", "SI" if dome.CanSetAzimuth else "NO")
    print("  CanSetPark:", "SI" if dome.CanSetPark else "NO")
    print("  CanSetShutter:", "SI" if dome.CanSetShutter else "NO")
    print("  CanSlave:", "SI" if dome.CanSlave else "NO")
    print("  CanSyncAzimuth:", "SI" if dome.CanSyncAzimuth else "NO")
#   print()
#   print("  SupportedActions:", dome.SupportedActions)

    while 1:
        print("\nStato attuale:")
        print("  AtHome: ", "SI" if dome.AtHome else "NO")
        print("  AtPark: ", "SI" if dome.AtPark else "NO")
        print("  ShutterStatus: ", dome.ShutterStatus)
        print("  Slaved: ", "SI" if dome.Slaved else "NO")
        print("  Slewing: ", "SI" if dome.Slewing else "NO")
        print("  Altitude: ", dome.Altitude)
        print("  Azimuth: ", dome.Azimuth)
        print()

        answ = (input("Comando (?:aiuto, q:esci): ")+"  ").lower()
        if answ[0] == "?":
            print(HELP)
        elif answ[0] == "q":
            break
        elif answ[:2] == "ab":
            dome.AbortSlew()
        elif answ[:2] == "cl":
            dome.CloseShutter()
        elif answ[:2] == "di":
            dome.Dispose()
        elif answ[:2] == "fi":
            dome.FindHome()
        elif answ[:2] == "op":
            dome.OpenShutter()
        elif answ[:2] == "pa":
            dome.Park()
        elif answ[:2] == "sp":
            dome.SetPark()
        elif answ[:2] == "st":
            val = get_val(answ)
            dome.SlewToAltitude(val)
        elif answ[:2] == "sa":
            val = get_val(answ)
            dome.SlewToAzimuth(val)
        elif answ[:2] == "sy":
            val = get_val(answ)
            dome.SyncToAzimuth(val)  # Sembra che il comando voglia interi

if __name__ == "__main__":
    main()
