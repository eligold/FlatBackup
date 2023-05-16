import obd, asyncio
from obd import Unit

car_connected = False

def getOBD():
    pass

class OBDData:
    R = Unit.Quantity(1,Unit.R).to_base_units()
    VF = Unit.Quantity(1984,Unit.cc).to_base_units()/Unit.Quantity(2,Unit.turn)
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