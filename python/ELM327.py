import os, logging
from obd import OBD, OBDCommand, commands
from obd.utils import bytes_to_int
from obd.protocols import ECU
from time import sleep, time

from OBDData import OBDData

TEMP = commands.INTAKE_TEMP
RPM = commands.RPM
MAF = commands.MAF
BPS = commands.BAROMETRIC_PRESSURE
VOLT = commands.ELM_VOLTAGE
MPH = commands.SPEED
#TODO Define exception if not found
class ELM327:
    wait = True
    carOn = False
    elm327 = None
    checktime = None
    obdd = OBDData()
    logger = logging.getLogger()
    def gear(messages):
        """ decoder for gear select """
        return bytes_to_int(messages[0].data[2:]) / 1000.0
    gear_command = OBDCommand("GEAR","Gear Select",b"01A4",4,gear,ECU.ENGINE,False)

    def __init__(self,portstr="/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"):
        logger = self.logger
        self.close()
        sleep(0.019)
        self.checktime = time()
        self.carOn = False
        port = os.path.realpath(portstr)
        if port == portstr:
            logger.warning("ELM327 not found!")
        else:
            logger.info(f"ELM327 port: {portstr.split('/')[-1]} -> {port}")
        elm = OBD(port)
        if elm.is_connected():
            voltage = elm.query(VOLT)
            if not voltage.is_null() and voltage.value.magnitude > 12.1:
                self.carOn = True
            self.elm327 = elm
        else:
            self.elm327 = None
            self.checktime = time() + 30

    def speed(self):
        elm = self.elm327
        if elm is not None:
            vr = elm.query(MPH)
            if not vr.is_null():
                return vr.value.magnitude
        elif time() > self.checktime:
            self.__init__()
            return self.speed()
        return 0.0

    def gear(self):
        elm = self.elm327
        if self.carOn:
            return elm.query(self.gear_command,force=True)
        return None

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
                            bps = elm.query(BPS).value.to('psi'))
            except AttributeError:
                self.__init__()
                return self.psi()
            return self.obdd.psi()
        else:
            if self.volts() > 12.1 or time() > self.checktime:
                self.__init__()
                return self.psi()
            sleep(0.19)
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
