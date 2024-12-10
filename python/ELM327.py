import os, logging, traceback
from obd import OBD, OBDCommand, OBDStatus, commands, Unit
from obd.utils import bytes_to_int
from obd.protocols import ECU
from time import sleep, time

TEMP = commands.INTAKE_TEMP
RPM = commands.RPM
MAF = commands.MAF
BPS = commands.BAROMETRIC_PRESSURE
VOLT = commands.ELM_VOLTAGE
CONNECTED = OBDStatus.OBD_CONNECTED

class EA888_2_0TFSI_PSI_CONV:
    R = Unit.Quantity(1,Unit.R).to_base_units() # Gas constant R
    VF = Unit.Quantity(1984,Unit.cc).to_base_units()/Unit.Quantity(2,Unit.turn) # 1984 mL(cc) air
    MM = Unit.Quantity(28.949,"g/mol").to_base_units() # < Air molar mass    flow every 2 rotations
    C = R/(VF*MM) # Constant for calculating airflow from OBD sensor readings
    def __init__(self,atm=14.3,iat=499.0,maf=132.0,rpm=4900): # random start values
        self.atmospheric_pressure = atm * Unit.psi
        self.intake_air_temp = iat * Unit.degK
        self.mass_air_flow = maf * Unit.gps
        self.rpm = rpm * Unit.rpm
        self._recalc()
   # Calculate pressure using ideal gas law with volumetric and mass air _flow_
    def _recalc(self): # P*V(f) = mm(f)*R*T --> C * IAT(K) * MAF / RPM = IAP
        iap = self.C / self.rpm * self.intake_air_temp * self.mass_air_flow
        self.intake_abs_pressure = iap.to('psi') # this doesn't fail because _unit analysis_
    def update(self,iat,rpm,maf,bps):
        self.intake_air_temp=iat
        self.rpm=rpm
        self.mass_air_flow=maf
        self.atmospheric_pressure=bps
        self._recalc()
    def psi(self):
        negative = self.intake_abs_pressure < self.atmospheric_pressure
        result = self.intake_abs_pressure - self.atmospheric_pressure
        if negative:
            result = result.to('bar')
        return result.magnitude

#TODO Define exception if not found
class ELM327:
    wait = True
    carOn = False
    elm327 = None
    checktime = None
    delay_sec = 5
    conv = EA888_2_0TFSI_PSI_CONV()
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
            if elm is not None and (elm.is_connected() or CONNECTED == elm.status()):
                logger.info(f"ELM327 read voltage as {elm.query(VOLT).value}")
                self.elm327 = elm # seems to read high, my battery has never produced 13.1V
            else: elm.close()
        except:
            traceback.print_exc()
            self.close(True,elm)

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
        rpmr = elm.query(RPM) # no boost if not spinning
        if not rpmr.is_null() and rpmr.value.magnitude != 0.0:
            self.conv.update(rpm = rpmr.value,
                        iat = elm.query(TEMP).value.to('degK'),
                        maf = elm.query(MAF).value,
                        bps = elm.query(BPS).value.to('psi'))
            return self.conv.psi()
        if not retry: return self._update(retry=True)
        return self.reset(19.0)

    def volts(self):
        if elm is not None and (elm.is_connected() or CONNECTED == elm.status()):
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
