#!/usr/bin/env python3
import obd, traceback, subprocess, cv2, numpy as np
from obd import Unit
from time import sleep

def run():
    ec = 0
    count = 0
    psi = 19.0
    obdd = OBDData()
    elm327 = getOBDconn()
    while(True):
        try:
            if elm327.is_connected():
                psi = getPSI(elm327,obdd)
            else:
                elm327.close()
                elm327 = getOBDconn()
            with open('/dev/fb0','rb+') as buf:
                while True:
                    img = screenPrint(np.full((1600,480),0x8248,np.uint16),"No Signal!",(500,200))
                    sleep(0.038) # ~25fps
                    if elm327.is_connected():
                        psi = getPSI(elm327,obdd)
                    else:
                        psi = 19.1
                    onScreen(buf,img,f"{psi:.2f} PSI")
                    if count > 125:
                        count = 0
                        if not elm327.is_connected():
                            elm327.close()
                            elm327 = getOBDconn()
                    else: count += 1
        except KeyboardInterrupt:
            if elm327.is_connected():
                elm327.close()
            exit()
        except Exception as e:
            ec += 1
            if ec > 10:
                ec = 0
                raise e
            traceback.print_exc()
        finally:
            if elm327.is_connected():
                elm327.close()

def getOBDconn():
    elm327 = obd.Async(portstr="/dev/ttyUSB0")
    elm327.watch(obd.commands.INTAKE_TEMP)
    elm327.watch(obd.commands.RPM)
    elm327.watch(obd.commands.MAF)
    elm327.watch(obd.commands.BAROMETRIC_PRESSURE)
    elm327.start()

    print(f"RPM: {elm327.query(obd.commands.RPM).value}")
    sleep(1)                                               #SLEEP HERE!!!

    return elm327

def getPSI(elm327,obdd):
    if elm327.supports(obd.commands.RPM) and elm327.is_connected():
        try:
            obdd.update(maf = elm327.query(obd.commands.MAF).value,
                        iat = elm327.query(obd.commands.INTAKE_TEMP).value.to('degK'), 
                        rpm = elm327.query(obd.commands.RPM).value,
                        atm = elm327.query(obd.commands.BAROMETRIC_PRESSURE).value.to('psi'))
            return obdd.psi()
        except AttributeError:
            print('"None" value from obd conn')
    return 19.0

def screenPrint(img,text,pos=(109,385)):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 2.5
    return cv2.putText(img, text, pos, font_face, scale, (0xc4,0xe4), 2, cv2.LINE_AA)

def onScreen(buf,f,t):
    f = cv2.cvtColor(screenPrint(f,t),cv2.COLOR_BGR2BGR565)
    for i in range(480):
        buf.write(f[i])
    buf.seek(0,0)

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

if __name__ == "__main__":
    subprocess.run(['sh','-c','echo 0 | sudo tee /sys/class/leds/PWR/brightness'])
    try:
       # subprocess.run(['bash','-c','ip link set wlan0 down'])
        run()
       # asyncio.run(other())
    finally:
        pass#subprocess.run(['bash','-c','ip link set wlan0 up'])

###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
# 