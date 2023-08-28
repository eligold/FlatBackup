#!/usr/bin/env python3
import asyncio#, aiofiles, 
import os, traceback, cv2, numpy as np
from subprocess import run, Popen, PIPE
from threading  import Thread
from queue import Queue, Empty
from time import sleep
from gpiozero import CPUTemperature as onboardTemp
from evdev.ecodes import (ABS_MT_TRACKING_ID, ABS_MT_POSITION_X,
                          ABS_MT_POSITION_Y, EV_ABS)
#import evdev
from ELM327 import ELM327

DIM = (720, 576) # video dimensions
SDIM = (960, 768)
FDIM = (1040,480)

COLOR_REC = 0xfa00 # 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae

CVT3TO2B = cv2.COLOR_BGR2BGR565
WIDTH = cv2.CAP_PROP_FRAME_WIDTH
HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
BRIGHTNESS = cv2.CAP_PROP_BRIGHTNESS
CONTRAST = cv2.CAP_PROP_CONTRAST

# below values are specific to my backup camera run thru
# my knock-off easy-cap calibrated with my phone screen. 
# YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to upscale and undistort. TODO upscale later vs now
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)

intemp = onboardTemp()

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()
q = Queue()

# touch = evdev.InputDevice('/dev/input/event4')
# psi queue, image queue
# async def run():
#     async for img in getImage():
#         # push to queue
#         outImage(latestPSI())
#     async with aiofiles.open('/dev/fb0','rb+') as buf:
#         pass

# async def touch_input(elm,camera,touch=touch):
#     async for event in touch.async_read_loop():
#         #if event.type == EV_ABS:
#         if event.code == ABS_MT_POSITION_X:
#             if event.value > 1479:
#                 bounce(elm,camera)
#                 exit(0)

# /dev/disk/by-id/ata-APPLE_SSD_TS128C_71DA5112K6IK-part1
def start():
    # dashcam_id_path = \
    #     "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    # dashcam = getCamera(int(os.path.realpath(dashcam_id_path).split("video")[-1]))
    # asyncio.ensure_future(touch_input(elm,camera,touch))
    # loop = asyncio.get_event_loop()
    # loop.run_forever()
    elm = ELM327()
    camera = None
    ec = 0
    usb_capture_id_path = "/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
    index = int(os.path.realpath(usb_capture_id_path).split("video")[-1])
    while(True):
        try:
            camera = getCamera(index)
            # /dev/input/by-id/... (or uuid?)
            cmd = Popen('evtest /dev/input/event0',shell=True,stdout=PIPE,stderr=PIPE)
            t = Thread(target=enqueue_output, args=(cmd.stdout, q))
            t.daemon = True
            t.start()
            res=run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
            volts = elm.volts()
            #if res.stdout == b'up\n' and volts < 12.1:
                #close(elm,camera)
                #exit(0)
            if volts > 12.1:
                run('ip link set wlan0 down',shell=True)
            success, img = getUndist(camera)
            with open('/dev/fb0','rb+') as buf:
                while camera.isOpened():
                    while(True):
                        try:  
                            line = q.get_nowait()
                            if(b'POSITION_X' in line and b'value' in line):
                                if int(line.decode().split('value')[-1]) > 1480:
                                    bounce(elm,camera)
                        except Empty:
                            break
                    success, img = getUndist(camera)
                    mainImage = combinePerspective(img)
                    sidebar = buildSidebar(elm)
                    onScreen(buf,mainImage,sidebar) if success else errScreen(buf)
            sleep(0.19)
        except KeyboardInterrupt:
            bounce(elm,camera)
        except Exception as e:
            print(e)
            ec += 1
            if ec > 10:
                ec = 0
                raise e
            traceback.print_exc()
        finally:
            bounce(elm,camera,1)

def errScreen(frame_buffer):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1
    image = cv2.putText(
                np.full((480,1600),COLOR_BAD,np.uint16),
            "No Signal!",(500,200), font_face, scale, (0xc4,0xe4), 2, cv2.LINE_AA)
    for i in range(480):
        frame_buffer.write(image[i])
    frame_buffer.seek(0)

def getCamera(camIndex:int,apiPreference=cv2.CAP_V4L2) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    camera.set(BRIGHTNESS,25)
    return camera

def getUndist(c):
    success, image = c.read()
    if success:
        undist = cv2.remap(image,mapx,mapy,interpolation=cv2.INTER_LANCZOS4)
        image = cv2.resize(undist,SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return success, image

def putText(img, text="you forgot the text idiot", origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,
            thickness=2,
            lineType=cv2.LINE_AA
        ):
    return cv2.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

def newOnScreen(frame_buffer,image,pos=(0,0)):
    h,w,d = image.shape
    if pos < (0,0) or d != 2:
        raise Exception(f"negative position!\n{pos}")
    # trim too wide
    if w + pos[0] > 1600:
        image = image[:,:1600-pos[0]]
    # vertical offset
    if pos[1] > 0:
        frame_buffer.seek(pos[1]*2*1600)
    for i in range(h):
        # horizontal offset
        if pos[0] > 0:
            frame_buffer.seek(pos[0]*2,1)
        frame_buffer.write(image[i])
        # if not full width seek end of line
        if w + pos[0] < 1600:
            frame_buffer.seek((1600-w-pos[0])*2,1)
    frame_buffer.seek(0)

def onScreen(frame_buffer,image,sidebar):
    for i in range(480):
        frame_buffer.write(image[i])
        if i > 320:
            for j in range(120):
                frame_buffer.write(np.uint16(i*2&(i-255-j)))
        else:
            frame_buffer.write(sidebar[i])
    frame_buffer.seek(0)

def combinePerspective(image):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4)
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    final_image = cv2.cvtColor(combo,CVT3TO2B)
    return final_image

def buildSidebar(elm):
    base = np.full((480,120),0xc55e,np.uint16) # COLOR_LOW,np.uint16)
    # TODO better battery interface to come
    sidebar = putText(base,f"{elm.volts()}V",(38,319),
                    color=(0xc5,0x9e,0x21),thickness=1,fontScale=0.5)
    sidebar = putText(sidebar,f"{elm.psi():.1f}",(4,38),color=COLOR_NORMAL)
    sidebar = putText(sidebar,"PSI",(7,76))
    temp = int(intemp.temperature)
    color = 0xf800 # red
    if temp < 20:
        color = 0xc55e # light blue
    elif temp < 60:
        color = COLOR_LOW # yellow
    # sidebar = putText(sidebar,f"{int(intemp.temperature)}C",(4,190))
    sidebar = cv2.circle(sidebar,(60,290),17,(0xffff),2)
    sidebar = cv2.circle(sidebar,(60,290),15,(0),2)
    sidebar = cv2.circle(sidebar,(60,290),15,(color),-1)
    sidebar = cv2.rectangle(sidebar,(48,178),(72,278),(0xffff),2)
    sidebar = cv2.rectangle(sidebar,(50,180),(70,280),(0),2)
    sidebar = cv2.rectangle(sidebar,(50,180),(70,280),(0x630c),-1)
    sidebar = cv2.rectangle(sidebar,(50,280-temp),(70,290),(color),-1)
    return sidebar

def close(elm,camera):
    elm.close()
    camera.release()

def bounce(elm,camera,ec=0):
    close(elm,camera)
    run(['bash','-c','ip link set wlan0 up'])
    exit(ec)

if __name__ == "__main__":
    run('echo 1 > /sys/class/leds/PWR/brightness',shell=True)
    start()

###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
