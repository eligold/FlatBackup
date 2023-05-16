#!/usr/bin/env python3
import asyncio, obd, traceback, subprocess, cv2, numpy as np
from obd import Unit
from time import sleep

DIM = (720, 576) # video dimensions
SDIM = (960, 768)
FDIM = (1280,480)
COLOR_REC = 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
CVT3TO2B = cv2.COLOR_BGR2BGR565
WIDTH = cv2.CAP_PROP_FRAME_WIDTH
HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT

# below values are specific to my backup camera run thru
# my knock-off easy-cap calibrated with my phone screen. 
# YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to upscale and undistort. TODO upscale later vs now
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)

def run():
    psi = 19
    ec = 0
    count = 0
    obdd = OBDData()
    elm327 = getOBDconn()
    wait = True
    while(True):
        subprocess.run(['bash','-c','ip link set wlan0 down'])
        try:
            camera = getCamera()
            success, img = getUndist(camera)
            with open('/dev/fb0','rb+') as buf:
                while camera.isOpened():
                    if not wait and elm327.is_connected():
                        psi = getPSI(elm327,obdd)
                    else:
                        psi = 19.1
                    success, img = getUndist(camera)
                    if not success:
                        errScreen(buf)
                    else:
                        onScreen(buf,img,f"{psi:.2f} PSI")
                    if count > 125:
                        wait = False
                        count = 0
                        if not elm327.is_connected():
                            elm327.close()
                            elm327 = getOBDconn()
                            wait = True
                    else: count += 1
            sleep(3)
        except KeyboardInterrupt:
            bounce(elm327,camera)
        except Exception as e:
            ec += 1
            if ec > 10:
                ec = 0
                raise e
            traceback.print_exc()
        finally:
            close(elm327,camera)

def errScreen(frame_buffer):
    image = screenPrint(np.full((1600,480),COLOR_BAD,np.uint16),"No Signal!",(500,200))
    for i in range(480):
        frame_buffer.write(image[i])
    frame_buffer.seek(0,0)

def getCamera(camIndex=0,apiPreference=cv2.CAP_V4L2):
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    return camera

def getOBDconn():
    elm327 = obd.Async(portstr="/dev/ttyUSB0")
    elm327.watch(obd.commands.INTAKE_TEMP)
    elm327.watch(obd.commands.RPM)
    elm327.watch(obd.commands.MAF)
    elm327.watch(obd.commands.BAROMETRIC_PRESSURE)
    elm327.start()
    return elm327

def getPSI(elm327,obdd):
    if elm327.supports(obd.commands.RPM):
        obdd.update(maf = elm327.query(obd.commands.MAF).value,
                    iat = elm327.query(obd.commands.INTAKE_TEMP).value.to('degK'), 
                    rpm = elm327.query(obd.commands.RPM).value,
                    atm = elm327.query(obd.commands.BAROMETRIC_PRESSURE).value.to('psi'))
        return obdd.psi()
    else:
        return 19.0

def screenPrint(img,text,pos=(589,473)):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1
    return cv2.putText(img, text, pos, font_face, scale, (0xc4,0xe4), 2, cv2.LINE_AA)

def getUndist(c):
    success, image = c.read()
    if success:
        image = cv2.resize(
                cv2.remap(image, mapx, mapy, interpolation=cv2.INTER_CUBIC),
                SDIM)[68:556]
    return success, image

def onScreen(frame_buffer,image,text):
    image_right = cv2.cvtColor(image,CVT3TO2B)
    image_left = image_right[8:488,:160]
    image_right = image_right[:480,-160:]
    image = screenPrint(
            cv2.cvtColor(
            cv2.resize(image[216:456,160:800], FDIM,interpolation=cv2.INTER_CUBIC),
            CVT3TO2B),
            text)
    for i in range(480):
        frame_buffer.write(image_left[i])
        frame_buffer.write(image[i])
        frame_buffer.write(image_right[i])
    frame_buffer.seek(0,0)

def close(elm327,camera):
    if elm327.is_connected():
                elm327.close()
    camera.release()
    subprocess.run(['bash','-c','ip link set wlan0 up'])

def bounce(elm327,camera):
    close(elm327,camera)
    exit()

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
    run()
###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf