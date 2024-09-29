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
    delay_sec = 5
    obdd = OBDData()
    logger = logging.getLogger()
    portstr= "/dev/ttyS0" # "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"
    def _gear(messages):
        """ decoder for gear select """
        return bytes_to_int(messages[0].data[2:]) / 1000.0
    gear_command = OBDCommand("GEAR","Gear Select",b"01A4",4,_gear,ECU.ENGINE,False)

    def __init__(self,portstr=None):
        logger = self.logger
        if portstr is None: portstr = self.portstr
        elif self.portstr is not portstr: self.portstr = portstr
        self.delay_sec *= 2
        self.checktime = time() + self.delay_sec
        self.carOn = False
        port = os.path.realpath(portstr)
        if port == portstr and len(portstr.split("/")) > 3: logger.warning("ELM327 not found!")
        else: logger.info(f"ELM327 port: {portstr.split('/')[-1]} -> {port}")
        try: # obd.logger.setLevel(obd.logging.DEBUG)
            elm = OBD(port)
            self.carOn = elm.is_connected()
            if self.connected(elm): # seems to read high on first try, my battery has never produced 13.1V
                logger.info(f"ELM327 read voltage as {elm.query(VOLT).value}")
                logger.info(f"ELM327 read voltage as {elm.query(VOLT).value}")
                self.elm327 = elm
            else: elm.close()
        except:
            traceback.print_exc()
            self.close(True,elm)

    def speed(self):
        if self.carOn:
            elm = self.elm327
            try:
                vr = elm.query(MPH)
                if not vr.is_null(): return vr.value.magnitude
            except Exception as e: self.logger.exception(e)
        return self.reset(0.0)

    def gear(self):
        if self.carOn:
            elm = self.elm327
            try: return elm.query(self.gear_command,force=True)
            except Exception as e: self.logger.exception(e)
        return self.reset()

    def psi(self):
        if self.carOn:
            try: return self._update()
            except Exception as e: self.logger.exception(e)
        else: return self.reset(19.1)

    def _update(self, retry = False):
        elm = self.elm327
        rpmr = elm.query(RPM)
        if not rpmr.is_null() and rpmr.value.magnitude != 0.0:
            self.obdd.update(rpm = rpmr.value,
                        iat = elm.query(TEMP).value.to('degK'),
                        maf = elm.query(MAF).value,
                        bps = elm.query(BPS).value.to('psi'))
            return self.obdd.psi()
        if not retry: return self._update(retry=True)
        return self.reset(19.0)

    def volts(self):
        if self.connected():
            elm = self.elm327
            try:
                vr = elm.query(VOLT)
                if not vr.is_null():
                    return vr.value.magnitude
            except Exception as e: self.logger.exception(e)
        else: return self.reset(12.0)

    def reset(self, default_value=None):
        if time() - self.checktime > self.delay_sec: self.checktime = time() + self.delay_sec / 2
        sleep(0.19) # /\ bandaid for no RTC
        self.carOn = False
        if time() > self.checktime: self.close(True)
        if default_value is not None: return default_value

    def close(self, restart=False, elm=None):
        if elm is None: elm = self.elm327
        if elm is not None: elm.close()
        self.carOn = False
        self.elm327 = None # self.elm327?
        if restart: self.__init__()

    def connected(self, elm=None):
        if elm is None: elm = self.elm327
        return (elm is not None and (elm.is_connected() or OBDStatus.OBD_CONNECTED == elm.status()))
