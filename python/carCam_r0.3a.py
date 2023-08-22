#!/usr/bin/env python3
import asyncio#, aiofiles, 
import os, traceback, cv2, numpy as np
from subprocess import run
from time import sleep, time
from gpiozero import CPUTemperature as inTemp
from evdev.ecodes import (ABS_MT_TRACKING_ID, ABS_MT_POSITION_X,
                          ABS_MT_POSITION_Y, EV_ABS)
import evdev
import ELM327

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

# below values are specific to my backup camera run thru
# my knock-off easy-cap calibrated with my phone screen. 
# YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to upscale and undistort. TODO upscale later vs now
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)

intemp = inTemp()
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
    camera = None
    psi = 19
    ec = 0
    count = 0
    dashcam = getCamera(int(os.path.realpath(
            "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
        ).split("video")[-1]))
    index = int(os.path.realpath(
            "/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
        ).split("video")[-1])
    elm = ELM327(portstr="/dev/ttyUSB0")
    wait = True
    # asyncio.ensure_future(touch_input(elm,camera,touch))
    # loop = asyncio.get_event_loop()
    # loop.run_forever()
    while(True):
        try:
            camera = getCamera(index)
            res=run(['bash','-c','cat /sys/class/net/wlan0/operstate'],capture_output=True)
            if res.stdout == b'up\n':
                #close(elm,camera)
                pass#exit(0)
            #run(['bash','-c','ip link set wlan0 down'])
            success, img = getUndist(camera)
            with open('/dev/fb0','rb+') as buf:
                while camera.isOpened():
                    if not wait:
                        psi = elm.psi()
                    else:
                        psi = 19.1
                    success, img = getUndist(camera)
                    onScreen(buf,img,psi) if success else errScreen(buf)
                    if count > 125:
                        print(ec)
                        wait = False
                        count = 0
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
    frame_buffer.seek(0,0)

def getCamera(camIndex=0,apiPreference=cv2.CAP_V4L2):
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    camera.set(BRIGHTNESS,25)
    return camera

def getUndist(c):
    success, image = c.read()
    if success:
        image = cv2.resize(
                    cv2.remap(image,mapx,mapy,interpolation=cv2.INTER_LANCZOS4),
                SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return success, image

def onScreen(frame_buffer,image,psi):
    image_right = cv2.cvtColor(image,CVT3TO2B)
    image_left = image_right[8:488,:220]
    image_right = image_right[:480,-220:]
    args = {"fontFace":cv2.FONT_HERSHEY_SIMPLEX,"fontScale":1,"color":(0xc4,0xe4),"thickness":2,"lineType":cv2.LINE_AA}
    pos = (4,38)
    text = f"{psi:.1f}"
    sidebar = cv2.putText(
                cv2.putText(
                    cv2.putText(
                            np.full((480,120),0x19ae,np.uint16),
                        "PSI",(7,76),**args),
                    f"{int(intemp.temperature)}C",(4,190),**args),
            text,pos,**args)
    image = cv2.cvtColor(
                cv2.resize(image[220:460,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4),
            CVT3TO2B)
    for i in range(480):
        frame_buffer.write(image_left[i])
        frame_buffer.write(image[i])
        frame_buffer.write(image_right[i])
        if i == 160 or i == 320:
            frame_buffer.write(np.full((120),0xc4e4,np.uint16))
        else:
            frame_buffer.write(sidebar[i])
    frame_buffer.seek(0,0)

def close(elm,camera):
    elm.close()
    camera.release()

def bounce(elm,camera,ec=0):
    close(elm,camera)
    run(['bash','-c','ip link set wlan0 up'])
    exit(ec)

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
