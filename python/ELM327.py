import os, logging, traceback
from obd import OBD, OBDCommand, OBDStatus, commands
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
    def _gear(messages):
        """ decoder for gear select """
        return bytes_to_int(messages[0].data[2:]) / 1000.0
    gear_command = OBDCommand("GEAR","Gear Select",b"01A4",4,_gear,ECU.ENGINE,False)

    def __init__(self,portstr="/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"):
        logger = self.logger
        self.checktime = time() + 10
        self.carOn = False
        port = os.path.realpath(portstr)
        if port == portstr:
            logger.warning("ELM327 not found!")
        else:
            logger.info(f"ELM327 port: {portstr.split('/')[-1]} -> {port}")
        elm = OBD(port)
        if self.connected():
            voltage = elm.query(VOLT)
            print(voltage.value)
            if not voltage.is_null() and voltage.value.magnitude > 12.9: self.carOn = True
            self.elm327 = elm
        else: self.close()

    def speed(self):
        elm = self.elm327
        if elm is not None:
            try:
                vr = elm.query(MPH)
                if not vr.is_null():
                    return vr.value.magnitude
            except Exception as e: self.logger.exception(e)
        return self.reset(0.0)

    def gear(self):
        elm = self.elm327
        if self.carOn:
            try: return elm.query(self.gear_command,force=True)
            except Exception as e: self.logger.exception(e)
        return None

    def psi(self):
        elm = self.elm327
        if self.carOn:
            try:
                rpmr = elm.query(RPM)
                if not (rpmr.is_null() or rpmr.value.magnitude == 0.0):
                    self.obdd.update(rpm = rpmr.value,
                                iat = elm.query(TEMP).value.to('degK'),
                                maf = elm.query(MAF).value,
                                bps = elm.query(BPS).value.to('psi'))
                    return self.obdd.psi()
            except Exception as e: self.logger.exception(e)
        return self.reset(19.0)

    def volts(self):
        elm = self.elm327
        if elm is not None:
            try:
                vr = elm.query(VOLT)
                if not vr.is_null():
                    return vr.value.magnitude
            except Exception as e: self.logger.exception(e)
        return self.reset(12.0)

    def reset(self, default_value=None):
        self.close()
        if time() - self.checktime > 10: self.checktime = time()
        sleep(0.19)
        if time() > self.checktime: self.__init__()
        if default_value is not None: return default_value

    def close(self):
        elm = self.elm327
        if elm is not None:
            elm.close()
            elm = None

    def connected(self):
        elm = self.elm327
        if elm is not None:
            return elm.is_connected() or elm.status() == OBDStatus.OBD_CONNECTED
        return False
