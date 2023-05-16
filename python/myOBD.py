import obd, asyncio
from obd import Unit

class myOBD:
    def __init__(self):
        self.car_connected = False
        self.elm327 = None #_get_elm()
        self.portstr = '/dev/ttyUSB0'
        self.obd_data = OBDData()
        self.run()

    def _get_elm(self):
        self.car_connected, self.elm327 = self._test_connection()
        # elm327.watch(obd.commands.INTAKE_TEMP)
        # elm327.watch(obd.commands.RPM)
        # elm327.watch(obd.commands.MAF)
        # elm327.watch(obd.commands.BAROMETRIC_PRESSURE)

    def get_PSI(self):
        psi = 19.1
        if self.car_connected:
            psi = self.obd_data.psi()
        return psi

    def run(self): #needs async probably
        while True:
            self.obd_data.update(
                maf = self.elm327.query(obd.commands.MAF).value,
                iat = self.elm327.query(obd.commands.INTAKE_TEMP).value.to('degK'), 
                rpm = self.elm327.query(obd.commands.RPM).value,
                atm = self.elm327.query(obd.commands.BAROMETRIC_PRESSURE).value.to('psi')
            )

    def _test_connection(self):
        elm327 = obd.OBD(portstr=self.portstr)
        car_connected = False
        if elm327.is_connected():
            if elm327.supports(obd.commands.RPM):
                car_connected = True
        elm327.start()
        return car_connected,elm327


    def close(self):
        self.elm327.close()

class OBDData:
    R = Unit.Quantity(1,Unit.R).to_base_units()
    VF = Unit.Quantity(1984,Unit.cc).to_base_units() /  \
            Unit.Quantity(2,Unit.turn)
    MM = Unit.Quantity(28.949,"g/mol").to_base_units()
    C = R/(VF*MM)

    def __init__(self,atm=14.3,iat=499.0,maf=132.0,rpm=4900):
        self.atm = atm*Unit.psi
        self.iat = iat*Unit.degK
        self.maf = maf*Unit.gps
        self.rpm = rpm*Unit.rpm
        self._recalc()

    def update(self,iat,rpm,maf,atm):
        self.iat=iat
        self.rpm=rpm
        self.maf=maf
        self.atm=atm
        self._recalc()

    def psi(self):
        return (self.iap - self.atm).magnitude

    def _recalc(self): # [2] C * IAT(K) * MAF / RPM = IAP
        iap = self.C / self.rpm * self.maf * self.iat
        self.iap = iap.to('psi')