#!/usr/bin/env python3
import os, sys, traceback, cv2, logging, numpy as np #, asyncio, aiofiles
from subprocess import run, Popen, PIPE
from threading  import Thread
from queue import Queue, Empty, Full
from time import sleep, time, localtime
from ELM327 import ELM327
#import evdev
# from evdev.ecodes import (ABS_MT_TRACKING_ID, ABS_MT_POSITION_X,
#                           ABS_MT_POSITION_Y, EV_ABS)
IMAGE_WIDTH = 1480
IMAGE_HEIGHT = 480
DIM = (720,576) # video dimensions
SDIM = (960,768)
FDIM = (1040,IMAGE_HEIGHT)

COLOR_REC = 0xfa00 # 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
COLOR_LAYM = 0xbfe4
WIDTH = cv2.CAP_PROP_FRAME_WIDTH
HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
FPS = cv2.CAP_PROP_FPS

# below values are specific to my backup camera run thru
# my knock-off easy-cap calibrated with my phone screen. 
# YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to upscale and undistort. TODO upscale later vs now
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)
touch_queue = Queue()
display_queue = Queue()
sidebar_queue = Queue(2)

sidebar_base = np.full((IMAGE_HEIGHT,120),COLOR_LOW,np.uint16)
for i in range(160,480): #(320,480):
    for j in range(120):
        sidebar_base[i][j] = np.uint16(i*2&(i-255-j))

no_signal_frame = cv2.putText(
    np.full((IMAGE_HEIGHT,IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

def begin():
    wifi = True
    try:
        res=run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        if res.stdout == b'up\n':
            pass # raise KeyboardInterrupt("wifi connected")
        else:
           wifi = False
           run('ip link set wlan0 down',shell=True)
        for f in [dash_cam,get_image,on_screen,sidebar_builder]:
            t = Thread(target=f,name=f.__name__)
            t.daemon = True
            t.start()
            logger.info(f"started thread {f.__name__}")
        while(True):
            try:
                cmd = Popen('evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00',
                            shell=True,stdout=PIPE,stderr=PIPE)
                touch_thread = Thread(target=enqueue_output, args=(cmd.stdout,))
                touch_thread.daemon = True
                touch_thread.start()
                while(True):
                    try:
                        line = touch_queue.get_nowait()
                        if(b'POSITION_X' in line and b'value' in line):
                            x = int(line.decode().split('value')[-1])
                            if x > IMAGE_WIDTH:
                                line = touch_queue.get_nowait()
                                y = int(line.decode().split('value')[-1])
                                if y > 239:
                                    raise KeyboardInterrupt(f"touch input, x,y: {x},{y}")
                    except Empty:
                        sleep(0.019)
            except Exception as e:
                logger.error(e.with_traceback(traceback))
    except KeyboardInterrupt as ki:
        logger.warning(ki.with_traceback(traceback))
        print("deuces")
    except Exception as e:
        logger.error(e.with_traceback(traceback))
        traceback.print_exc()
    finally:
        logger.warning(f"sidebars: {sidebar_queue.qsize()}\timages ready to display: {display_queue.qsize()}")
        if not wifi:
            run('ip link set wlan0 up',shell=True)

def enqueue_output(out):
    for line in iter(out.readline, b''):
        touch_queue.put(line)
    out.close()

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
                psi = elm.psi()
                sidebar = putText(sidebar,f"{psi:.1f}",(4,57),color=COLOR_NORMAL,fontScale=1.19,thickness=3)
                sidebar = putText(sidebar,"BAR" if psi < 0.0 else "PSI",(60,95),color=COLOR_BAD)
                try:
                    sidebar_queue.put(sidebar)
                except Full:
                    sidebar_queue.get()
                    sidebar_queue.put(sidebar)
        except Exception as e:
            traceback.print_exc()
            logger.error(e.with_traceback(traceback))
        finally:
            elm.close()
            sleep(3)

def dash_entry():
    t = Thread(target=dash_cam)
    t.daemon = True
    t.start()

def dash_cam():
    while(True): # /dev/disk/by-id/ata-APPLE_SSD_TS128C_71DA5112K6IK-part1
        dashcam_id_path = \
                "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
        dashcam = get_camera(int(os.path.realpath(dashcam_id_path).split("video")[-1]),
                             width=2592,height=1944)
        size = (int(dashcam.get(WIDTH)), int(dashcam.get(HEIGHT)))
        logger.info(f"dashcam resolution: {size}")
        fps = dashcam.get(FPS)
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        out = cv2.VideoWriter("/tmp/tmp.mkv",fourcc,fps,(640,480))
        try:
            while(dashcam.isOpened()):
                out.release()
                stop_time = int(time()) + 1800
                out = cv2.VideoWriter(f"/media/dashcam-{stop_time}.mkv",fourcc,fps,size)
                while(time()<stop_time):
                    success, frame = dashcam.read()
                    if success:
                        out.write(cv2.cvtColor(frame,cv2.COLOR_BGR2HSV))
                    else:
                       # out.write(putText(np.full((1944,2592),COLOR_BAD,np.uint16),
                       #                   "No Signal!",(1200,972),COLOR_NORMAL))
                        logger.warning("missing frame from dashcam!")
        except Exception:
            traceback.print_exc()
        finally:
            dashcam.release()
            out.release()

def get_camera(camIndex:int,apiPreference=cv2.CAP_V4L2,width=720,height=576) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(cv2.CAP_PROP_BRIGHTNESS,25)
    return camera

def undistort(img):
    undist = cv2.remap(img,mapx,mapy,interpolation=cv2.INTER_LANCZOS4)
    image = cv2.resize(undist,SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return image

def build_reverse_view(image):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4)
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    return cv2.cvtColor(combo,cv2.COLOR_BGR2BGR565)

def putText(img, text="you forgot the text idiot", origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,thickness=2,lineType=cv2.LINE_AA):
    return cv2.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

if __name__ == "__main__":
    handler = logging.FileHandler("runtime-carCam.log")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('[%(levelname)s] [%(threadName)s] %(message)s'))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    run('echo none > /sys/class/leds/PWR/trigger',shell=True)
    run('echo 0 > /sys/class/leds/PWR/brightness',shell=True)
   # dash_entry()
    begin()
