from obd import Unit

class OBDData:
    # Gas constant R
    R = Unit.Quantity(1,Unit.R).to_base_units()
    # 1984 mL or cc air flow every 2 rotations
    VF = Unit.Quantity(1984,Unit.cc).to_base_units()/Unit.Quantity(2,Unit.turn)
    # Air molar mass
    MM = Unit.Quantity(28.949,"g/mol").to_base_units()
    # Constant for calculating airflow from
    C = R/(VF*MM)  #   OBD sensor readings

    def __init__(self,atm=14.3,iat=499.0,maf=132.0,rpm=4900):
        self.atmospheric_pressure = atm * Unit.psi
        self.intake_air_temp = iat * Unit.degK
        self.mass_air_flow = maf * Unit.gps
        self.rpm = rpm * Unit.rpm
        self._recalc()
    
    # Calculate pressure using ideal gas law with volumetric
    # and mass air _flow_  -->  P*V(f) = mm(f)*R*T
    def _recalc(self): # C * IAT(K) * MAF / RPM = IAP
        iap = self.C / self.rpm * self.intake_air_temp * self.mass_air_flow
        # this doesn't fail because _unit analysis_
        self.intake_abs_pressure = iap.to('psi')

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
