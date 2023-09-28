#!/usr/bin/env python3
import os, sys, traceback, cv2, logging, numpy as np #, asyncio, aiofiles
from subprocess import run, Popen, PIPE
from threading  import Thread
from queue import Queue, Empty, Full
from collections import deque
from time import sleep
from gpiozero import CPUTemperature as onboardTemp
from ELM327 import ELM327
#import evdev
# from evdev.ecodes import (ABS_MT_TRACKING_ID, ABS_MT_POSITION_X,
#                           ABS_MT_POSITION_Y, EV_ABS)
IMAGE_WIDTH = 1480
IMAGE_HEIGHT = 480
PSI_BUFFER_DEPTH = 740
PPPSI = 30          # pixels per PSI and negative Bar
DIM = (720,576) # video dimensions
SDIM = (960,768)
FDIM = (1040,IMAGE_HEIGHT)

COLOR_REC = 0xfa00 # 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
COLOR_LAYM = 0xbfe4
COLOR_OVERLAY = (199,199,190)
DOT = (255,0,0)
SHADOW = (133,38,38)
BLACK = (0,0,0)
ALPHA = 0.57

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
intemp = onboardTemp()
show_graph = False
psi_list = deque()
touch_queue = Queue()
display_queue = Queue()
sidebar_queue = Queue()

sidebar_base = np.full((IMAGE_HEIGHT,120),COLOR_LOW,np.uint16)
for i in range(160,480): #(320,480):
    for j in range(120):
        sidebar_base[i][j] = np.uint16(i*2&(i-255-j))

no_signal_frame = cv2.putText(
    np.full((IMAGE_HEIGHT,IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

def begin(): # /dev/disk/by-id/ata-APPLE_SSD_TS128C_71DA5112K6IK-part1
    wifi = False
    try:
        res=run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        if res.stdout != b'up\n':
           wifi = True
           run('ip link set wlan0 down',shell=True)
        for f in [get_image,touch_input,sidebar_builder,on_screen]:
            t = Thread(target=f,name=f.__name__)
            t.daemon = True
            t.start()
        while(True):
            # todo overlay builder stuff here
            try:
                line = touch_queue.get_nowait()
                if(b'POSITION_X' in line and b'value' in line):
                    x = int(line.decode().split('value')[-1])
                    if x > IMAGE_WIDTH:
                        line = touch_queue.get_nowait()
                        y = int(line.decode().split('value')[-1])
                        if y > 239: raise KeyboardInterrupt(f"touch input, x,y: {x},{y}")
                        else: show_graph = not show_graph
            except Empty:
                sleep(0.019)
    except KeyboardInterrupt as ki:
        logger.warning(ki.with_traceback(traceback))
        print("leaving on purpose")
    except Exception as e:
        logger.error(e.with_traceback(traceback))
        traceback.print_exc()
    finally:
        logger.warning(f"sidebars: {sidebar_queue.qsize()}\timages ready to display: {display_queue.qsize()}")
        if wifi:
            run('ip link set wlan0 up',shell=True)

def get_image():
    while(True):
        try:
            usb_capture_id_path = "/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
            usb_capture_real_path = os.path.realpath(usb_capture_id_path)
            if usb_capture_id_path == usb_capture_real_path:
                logger.error("camera not found!\twaiting...")
                sleep(3)
            else:
                logger.info(f"{usb_capture_id_path} -> {usb_capture_real_path}")
                index = int(usb_capture_real_path.split("video")[-1])
                camera = get_camera(index)
                camera.read()
                try:
                    while camera.isOpened():
                        success, image = camera.read()
                        if success:
                            display_queue.put(undistort(image))
                        else:
                            logger.error("bad UVC read!")
                finally:
                    logger.warning("release camera resource")
                    camera.release()
        except Exception as e:
            logger.error(e.with_traceback(traceback))

def on_screen():
    while(True):
        sidebar = sidebar_base
        try:
            with open('/dev/fb0','rb+') as frame_buffer:
                while(True):
                    try:
                        final_image = build_reverse_view(display_queue.get(timeout=0.04))
                        for i in range(480):
                            frame_buffer.write(final_image[i])
                            frame_buffer.write(sidebar[i])
                        frame_buffer.seek(0)
                    except Empty:
                        sleep(0.019)
                    try:
                        sidebar = sidebar_queue.get_nowait()
                    except Empty:
                        pass
        except Exception as e:
            logger.error(e.with_traceback(traceback))

def sidebar_builder():
    while(True):
        try:
            elm = ELM327()
            while(True):
                sidebar = sidebar_base.copy()
                psi = add_pressure(elm.psi())
                sidebar = putText(sidebar,f"{psi:.1f}",(4,57),color=COLOR_NORMAL,fontScale=1.19,thickness=3)
                sidebar = putText(sidebar,"BAR" if psi < 0.0 else "PSI",(60,95),color=COLOR_BAD)
                try:
                    sidebar_queue.put(sidebar)
                except Full:
                    try:
                        sidebar_queue.get_nowait()
                    except Empty:
                        pass
                    sidebar_queue.put(sidebar)
        except Exception as e:
            traceback.print_exc()
            logger.error(e.with_traceback(traceback))
        finally:
            elm.close()
            sleep(3)

def touch_input():
    while(True):
        try:
            cmd = Popen('evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00',
                        shell=True,stdout=PIPE,stderr=PIPE)
            for line in iter(cmd.stdout.readline, b''):
                touch_queue.put(line)
            cmd.stdout.close()
        except Exception as e:
            logger.error(e.with_traceback(traceback))

def get_camera(camIndex:int,apiPreference=cv2.CAP_V4L2) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    camera.set(cv2.CAP_PROP_BRIGHTNESS,25)
    return camera

def undistort(img):
    undist = cv2.remap(img,mapx,mapy,interpolation=cv2.INTER_LANCZOS4)
    image = cv2.resize(undist,SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return image

def build_reverse_view(image):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4)
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    if show_graph:
        combo = addOverlay(combo)
    return cv2.cvtColor(combo,cv2.COLOR_BGR2BGR565)

def putText(img, text="you forgot the text idiot", origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,thickness=2,lineType=cv2.LINE_AA):
    return cv2.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

# make boost graph here ~+15psi to ~-1.5bar
# add each point to new deque and increment position by one when reading current deque
def addOverlay(image):
    h,w = image.shape[:2]
    radius,offset = 19,38
    overlay_image = image.copy()
    graph_list = psi_list.copy()
    overlay_image = cv2.rectangle(overlay_image,(offset,offset-radius),(w-offset,h-(offset-radius)),COLOR_OVERLAY,-1)
    overlay_image = cv2.rectangle(overlay_image,(offset-radius,offset),(w-(offset-radius),h-offset),COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(offset,offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(offset,h-offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(w-offset,h-offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(w-offset,offset),radius,COLOR_OVERLAY,-1)
    cv2.addWeighted(overlay_image,ALPHA,image,1-ALPHA,0,image)
    image[25:455,44:46] = BLACK
    image[405:407,25:1456] = BLACK
    image[135:137,38:45] = BLACK
    image = putText(image,"10",(25,133),color=BLACK,fontScale=0.38,thickness=1)
    for x in range(PSI_BUFFER_DEPTH-len(graph_list),PSI_BUFFER_DEPTH):
        try:
            x = x * 2
            y = FDIM[1] - 2 * PPPSI - 15 - graph_list.popLeft()
            image[y:y+2,x:x+2] = DOT
            image[y+2,x:x+3] = SHADOW
            image[y:y+3,x+2] = SHADOW
        except IndexError:
            pass
    return image

def add_pressure(pressure):
    entry = int(pressure*PPPSI)
    while(len(psi_list)>=PSI_BUFFER_DEPTH-1):
        psi_list.popLeft() # pop()
    psi_list.append(entry) # appendLeft()
    return pressure

if __name__ == "__main__":
    handler = logging.FileHandler("/root/runtime-carCam.log") # StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('[%(levelname)s] [%(threadName)s] %(message)s'))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    run('echo none > /sys/class/leds/PWR/trigger',shell=True)
    run('echo 0 > /sys/class/leds/PWR/brightness',shell=True)
    begin()

###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
# [3] https://github.com/tmckay1/pi_bluetooth_auto_connect

# touch = evdev.InputDevice('/dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00')
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
# def main(): # async?
#     ...
#     asyncio.ensure_future(touch_input(elm,camera,touch))
#     loop = asyncio.get_event_loop()
#     loop.run_forever()
