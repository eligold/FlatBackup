#!/usr/bin/env python3
import asyncio#, aiofiles, 
import sys, obd, traceback, cv2, numpy as np
from subprocess import run
import evdev
from evdev.ecodes import (ABS_MT_TRACKING_ID, ABS_MT_POSITION_X,
                          ABS_MT_POSITION_Y)
import select
from obd import Unit, OBDStatus
from time import sleep

DIM = (720, 576) # video dimensions
SDIM = (960, 768)
FDIM = (1040,480)

COLOR_REC = 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae

CVT3TO2B = cv2.COLOR_BGR2BGR565
WIDTH = cv2.CAP_PROP_FRAME_WIDTH
HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
BRIGHTNESS = cv2.CAP_PROP_BRIGHTNESS
CONTRAST = cv2.CAP_PROP_CONTRAST

TEMP = obd.commands.INTAKE_TEMP
RPM = obd.commands.RPM
MAF = obd.commands.MAF
PRES = obd.commands.BAROMETRIC_PRESSURE
VOLT = obd.commands.ELM_VOLTAGE

# below values are specific to my backup camera run thru
# my knock-off easy-cap calibrated with my phone screen. 
# YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to upscale and undistort. TODO upscale later vs now
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)
# psi queue, image queue
# async def run():
#     async for img in getImage():
#         # push to queue
#         outImage(latestPSI())
#     async with aiofiles.open('/dev/fb0','rb+') as buf:
#         pass

def start():
    psi = 19
    ec = 0
    count = 0
    elm = ELM327(portstr="/dev/ttyUSB0")
    wait = True
    carOff = True
    # for path in evdev.list_devices():
    #     device = evdev.InputDevice(path)
    #     if evdev.ecodes.EV_ABS in device.capabilities():
    #         r, w, x = select.select([device.fd], [], [])
    #         break
    while(True):
        try:
            camera = getCamera()
            res=run(['bash','-c','cat /sys/class/net/wlan0/operstate'],capture_output=True)
            if res.stdout == b'up\n':
                #close(elm,camera)
                pass#exit(0)
            #run(['bash','-c','ip link set wlan0 down'])
            success, img = getUndist(camera)
            with open('/dev/fb0','rb+') as buf:
                while camera.isOpened():
                    # id_ = -1
                    # x = y = 0
                    # for event in device.read():
                    #     if event.code == event.value == 0:
                    #         if id_ != -1 and x > 1519:
                    #             print(x, y)
                    #             bounce(elm327,camera)
                    #     elif event.code == ABS_MT_TRACKING_ID:
                    #         id_ = event.value
                    #     elif event.code == ABS_MT_POSITION_X:
                    #         x = event.value
                    #     elif event.code == ABS_MT_POSITION_Y:
                    #         y = event.value
                    if not wait:
                        psi = elm.psi()#getPSI(elm327,obdd)
                    else:
                        psi = 19.1
                    success, img = getUndist(camera)
                    onScreen(buf,img,f"{psi:.2f} PSI") if success else errScreen(buf)
                    if count > 125:
                        wait = False
                        count = 0

                        # NEEDS WORK:
                        if carOff and elm.volts() > 13:
                            elm.close()
                            elm = ELM327()
                            carOff = False
                            wait = True
                    else: count += 1
            sleep(0.19)
        except KeyboardInterrupt:
            bounce(elm,camera)
        except Exception as e:
            print(e)
            ec += 1
            if ec > 10:
                ec = 0
                raise e
            traceback.print_exc(e)
        finally:
            bounce(elm,camera,1)

def errScreen(frame_buffer):
    image = screenPrint(np.full((480,1600),COLOR_BAD,np.uint16),"No Signal!",(500,200))
    for i in range(480):
        frame_buffer.write(image[i])
    frame_buffer.seek(0,0)

def getCamera(camIndex=0,apiPreference=cv2.CAP_V4L2):
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    camera.set(BRIGHTNESS,25)
    return camera

def screenPrint(img,text,pos=(509,473)):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1
    return cv2.putText(img, text, pos, font_face, scale, (0xc4,0xe4), 2, cv2.LINE_AA)

def getUndist(c):
    success, image = c.read()
    if success:
        image = cv2.resize(
                    cv2.remap(image, mapx, mapy, interpolation=cv2.INTER_LANCZOS4),
                SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return success, image

def onScreen(frame_buffer,image,text):
    image_right = cv2.cvtColor(image,CVT3TO2B)
    image_left = image_right[8:488,:220]
    image_right = image_right[:480,-220:]
    image = screenPrint(
                cv2.cvtColor(
                    cv2.resize(image[220:460,220:740], FDIM,interpolation=cv2.INTER_LANCZOS4),
                CVT3TO2B),
            text)
    for i in range(480):
        frame_buffer.write(image_left[i])
        frame_buffer.write(image[i])
        frame_buffer.write(image_right[i])
        frame_buffer.write(np.full(120,0x19ae,np.uint16))
    frame_buffer.seek(0,0)

def close(elm,camera):
    elm.close()
    camera.release()

def bounce(elm,camera,ec=0):
    close(elm,camera)
    run(['bash','-c','ip link set wlan0 up'])
    exit(ec)

class ELM327:
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

    wait = True
    carOn = False
    elm327 = None
    obdd = OBDData()
    def __init__(self,portstr="/dev/ttyUSB0"):
        self.close()
        elm = obd.Async(portstr)
        if elm.is_connected():
            self.carOn = True
            elm.watch(TEMP)
            elm.watch(RPM)
            elm.watch(MAF)
            elm.watch(PRES)
        if not elm.status() != OBDStatus.OBD_CONNECTED:
            elm = None
        else:
            elm.watch(VOLT)
            elm.start()
        self.elm327 = elm

    def psi(self):
        elm = self.elm327
        obdd = self.obdd
        if elm is not None:
            if not self.carOn:
                if self.volts() > 13:
                    self.__init__()
                    return self.psi()
            mafr = elm.query(MAF)
            if mafr.is_null():
                self.__init__()
                return self.psi()
            obdd.update(maf = mafr.value,
                        iat = elm.query(TEMP).value.to('degK'),
                        rpm = elm.query(RPM).value,
                        atm = elm.query(PRES).value.to('psi'))
            return self.obdd.psi()
        else:
            return 19.0

    def volts(self):
        elm = self.elm327
        if elm is not None:
            vr = self.elm327.query(VOLT)
            if not vr.is_null():
                return vr.value
        return 12.0

    def close(self):
        elm = self.elm327
        if elm is not None:
            elm.close()

    def is_connected(self):
        elm = self.elm327
        if elm is not None:
            return elm.is_connected()
    

if __name__ == "__main__":
    run(['sh','-c','echo 0 | sudo tee /sys/class/leds/PWR/brightness'])
    start()
    # try:
    #     # run(['bash','-c','ip link set wlan0 down'])
    #     start()
    # finally:
    #     pass # run(['bash','-c','ip link set wlan0 up'])

###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
