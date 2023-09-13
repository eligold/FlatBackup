from time import sleep, time
import obd

from OBDData import OBDData

TEMP = obd.commands.INTAKE_TEMP
RPM = obd.commands.RPM
MAF = obd.commands.MAF
PRES = obd.commands.BAROMETRIC_PRESSURE
VOLT = obd.commands.ELM_VOLTAGE

#TODO Define exception if not found
class ELM327:
    wait = True
    carOn = False
    elm327 = None
    checktime = None
    obdd = OBDData()
    def __init__(self,portstr="/dev/ttyUSB0"):
        self.close()
        sleep(0.019)
        self.checktime = time()
        self.carOn = False
        elm = obd.OBD(portstr)
        if elm.is_connected():
            voltage = elm.query(VOLT)
            if not voltage.is_null() and voltage.value.magnitude > 12.1:
                self.carOn = True
            self.elm327 = elm
        else:
            self.elm327 = None
            self.checktime = time() + 30

    def psi(self):
        elm = self.elm327
        if self.carOn:
            rpmr = elm.query(RPM)
            if rpmr.is_null() or rpmr.value == 0.0:
                self.__init__()
                return self.psi()
            try:
                self.obdd.update(rpm = rpmr.value,
                            iat = elm.query(TEMP).value.to('degK'),
                            maf = elm.query(MAF).value,
                            atm = elm.query(PRES).value.to('psi'))
            except AttributeError:
                self.__init__()
                return self.psi()
            return self.obdd.psi()
        else:
            if self.volts() > 12.1 or time() > self.checktime:
                self.__init__()
                return self.psi()
            return 19.0

    def volts(self):
        elm = self.elm327
        if elm is not None:
            vr = elm.query(VOLT)
            if not vr.is_null():
                return vr.value.magnitude
        elif time() > self.checktime:
            self.__init__()
            return self.volts()
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
