from time import time
import obd

import OBDData

TEMP = obd.commands.INTAKE_TEMP
RPM = obd.commands.RPM
MAF = obd.commands.MAF
PRES = obd.commands.BAROMETRIC_PRESSURE
VOLT = obd.commands.ELM_VOLTAGE
wait = True
carOn = False
elm327 = None
obdd = OBDData()
def __init__(self,portstr="/dev/ttyUSB0"):
    self.close()
    elm = obd.obd(portstr)
    if elm.is_connected():
        voltage = elm.query(VOLT)
        if not voltage.is_null() and voltage.value.magnitude > 13.0:
            self.carOn = True
        elm.close()
        elm = obd.Async(portstr)

        if self.carOn:
            elm.watch(TEMP)
            elm.watch(RPM)
            elm.watch(MAF)
            elm.watch(PRES)
        elm.watch(VOLT)
        elm.start()
        self.elm327 = elm
    else:
        elm = None

def psi(self):
    elm = self.elm327
    if self.carOn:
        rpmr = elm.query(RPM)
        if rpmr.is_null() or rpmr.value == 0.0:
            self.__init__()
            return self.psi()
        self.obdd.update(rpm = rpmr.value,
                    iat = elm.query(TEMP).value.to('degK'),
                    maf = elm.query(MAF).value,
                    atm = elm.query(PRES).value.to('psi'))
        return self.obdd.psi()
    else:
        if self.volts() > 13:
            self.__init__()
            return self.psi()
        return 19.0

def volts(self):
    elm = self.elm327
    if elm is not None:
        vr = elm.query(VOLT)
        if not vr.is_null():
            return vr.value.magnitude
    return 12.0

def close(self):
    elm = self.elm327
    if elm is not None:
        elm.close()

def is_connected(self):
    elm = self.elm327
    if elm is not None:
        return elm.is_connected()
    return False