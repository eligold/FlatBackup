#!/usr/bin/env python3
import asyncio, obd, traceback, subprocess, cv2, numpy as np
from obd import Unit
from time import sleep


DIM = (720, 576) # video upscale dimensions
SDIM = (1200, 960)
COLOR_REC = 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
CVT3TO2B = cv2.COLOR_BGR2BGR565    # convenience defs \/ \/
WIDTH = cv2.CAP_PROP_FRAME_WIDTH
HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
BUF_SIZE = 25*60*2 #f/s * s/m * 2min buffer

# below values are specific to my backup camera run thru
# my knock-off easy-cap calibrated with my phone screen. 
# YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to upscale and undistort. TODO upscale later?
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)

def run(camIndex=0,apiPreference=cv2.CAP_V4L2):
    psi = 19
    ec = 0
    count = 0
    obdd = OBDData()
    buffer = CircBuffer()
    elm327 = getOBDconn()
    wait = True
    while(True):
        subprocess.run(['bash','-c','ip link set wlan0 down'])
        try:
            camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
            camera.set(WIDTH,720)
            camera.set(HEIGHT,576)
            color = COLOR_NORMAL
            success, img = getUndist(camera)
            with open('/dev/fb0','rb+') as buf:
                while camera.isOpened():
                    onScreen(buf,img,color,f"{psi:.2f} PSI")
                    success, img = getUndist(camera)
                    if not success:
                        img = screenPrint(np.full((1600,480),COLOR_BAD,np.uint16),"No Signal!",(500,200))
                    if not wait and elm327.is_connected():
                        psi = getPSI(elm327,obdd)
                    else:
                        psi = 19.1
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
            close(elm327,camera)
            exit()
        except Exception as e:
            ec += 1
            if ec > 10:
                ec = 0
                raise e
            traceback.print_exc()
        finally:
            close(elm327,camera)

async def getImage():
    camera = cv2.VideoCapture(0,apiPreference=cv2.CAP_V4L2)
    while camera.isOpened():
        success, image = camera.read()
        if success:
            image = cv2.remap(image, mapx, mapy, interpolation=cv2.INTER_LINEAR)
        yield success, image

async def buff(buffer):
    async for success, image in getImage():
        if not success:
            image = np.full((1600,480),COLOR_BAD,np.uint16) 
        buffer.append(image)

async def display(buffer,elm327):
    with open('/dev/fb0','rb+') as frame_buffer:
        while(True):
            image = screenPrint(buffer.getLatest(),f"{getPSI(elm327)} PSI")
            for i in range(480):
                frame_buffer.write(image[i])
            frame_buffer.seek(0,0)
                
async def other():
    try:
        elm327 = getOBDconn()
        elm327.start()
        buffer = CircBuffer()
        await asyncio.gather(buff(buffer=buffer),display(buffer=buffer,elm327=elm327))
    finally:
        elm327.close()

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

def screenPrint(img,text,color=COLOR_NORMAL,pos=(1209,385)):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 2.5
    if img.shape[1] < 1600:
        img = cv2.copyMakeBorder(img,0,0,0,1600-img.shape[1],cv2.BORDER_CONSTANT,value=color)
    return cv2.putText(img, text, pos, font_face, scale, (0xc4,0xe4), 2, cv2.LINE_AA)

def getUndist(c):
    r, img = c.read()
    if r:
        img = cv2.resize(cv2.remap(img, mapx, mapy, interpolation=cv2.INTER_LINEAR),SDIM)[175:655] #[166:646]
    return r, img

def onScreen(buf,f,c,t):
    if len(f.shape) > 2 and f.shape[2] != 2:
        f = cv2.cvtColor(f,CVT3TO2B)
    f = screenPrint(f,t,c)
    for i in range(480):
        buf.write(f[i])
    buf.seek(0,0)

def close(elm327,camera):
    if elm327.is_connected():
                elm327.close()
    camera.release()
    subprocess.run(['bash','-c','ip link set wlan0 up'])

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

class CircBuffer:
    def __init__(self,capacity=BUF_SIZE):
        self.capacity = capacity
        self.buf = []

    class __Full:
        def append(self, item):
            self.buf[self.pos] = item
            self.pos = (self.pos + 1) % self.capacity

        def get(self):
            return self.buf[self.pos:]+self.buf[:self.pos]
        
        def getLatest(self):
            pos = self.pos
            idx = -1
            if pos > 0:
                idx = idx+pos
            return self.buf[idx]

    def append(self,item):
        self.data.append(item)
        if len(self.data) == self.max:
            self.pos = 0
            self.__class__ = self.__Full

    def get(self):
        return self.buf
    
    def getLatest(self):
        return self.get()[-1]

if __name__ == "__main__":
    subprocess.run(['sh','-c','echo 0 | sudo tee /sys/class/leds/PWR/brightness'])
    run()
   # asyncio.run(other())
###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
# 