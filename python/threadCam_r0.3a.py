#!/usr/bin/env python3
import os, sys, traceback, cv2, logging, numpy as np #, asyncio, aiofiles
from subprocess import run, Popen, PIPE
from threading  import Thread
from queue import Queue, Empty, Full
from time import sleep, time, ctime, perf_counter_ns
from ELM327 import ELM327

FINAL_IMAGE_WIDTH = 1480
FINAL_IMAGE_HEIGHT = 480
DIM = (720,576) # video dimensions
SDIM = (960,768)
FDIM = (1040,FINAL_IMAGE_HEIGHT)

COLOR_REC = 0xfa00 # 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
COLOR_LAYM = 0xbfe4
FPS = cv2.CAP_PROP_FPS
CUBIC = cv2.INTER_CUBIC
FORMAT = cv2.CAP_PROP_FOURCC
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
fourcc = cv2.VideoWriter_fourcc(*'MJPG')

touch_queue = Queue()
display_queue = Queue()
processing_queue = Queue()
sidebar_queue = Queue(2)
dash_queue = Queue()

sidebar_base = np.full((FINAL_IMAGE_HEIGHT,120),COLOR_LOW,np.uint16)
for i in range(160,480):
    for j in range(120):
        sidebar_base[i][j] = np.uint16(i*2&(i-255-j))

no_signal_frame = cv2.putText(
    np.full((FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

def begin():
    wifi = False
    try:
        res=run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        if res.stdout == b'up\n':
            pass # raise KeyboardInterrupt("wifi connected")
        else:
           wifi = True
           run('ip link set wlan0 down',shell=True)
        for f in [enqueue_touch_output,get_image,on_screen,sidebar_builder,dash_cam]:
            Thread(target=f,name=f.__name__,daemon=True).start()
            logger.info(f"started thread {f.__name__}")
        while(True):
            pipeline_output()
            touchscreen()
    except Exception as e:
        logger.error(traceback.format_tb(e.__traceback__))
    finally:
        logger.warning(f"sidebars: {sidebar_queue.qsize()}\timages ready to display: {display_queue.qsize()}")
        logger.warning(f"processing: {processing_queue.qsize()}\tdash camera: {dash_queue.qsize()}")
        if wifi:
            run('ip link set wlan0 up',shell=True)

def pipeline_output():
    try:
        image = processing_queue.get_nowait()
        image = undistort(image)
        display_queue.put(build_reverse_view(image))
    except Empty:
        pass

def touchscreen():
    try:
        line = touch_queue.get_nowait()
        if(b'POSITION_X' in line and b'value' in line):
            x = int(line.decode().split('value')[-1])
            if x > FINAL_IMAGE_WIDTH:
                line = touch_queue.get_nowait()
                y = int(line.decode().split('value')[-1])
                if y > 239:
                    raise KeyboardInterrupt(f"touch input, x,y: {x},{y}")
    except Empty:
        pass

def enqueue_touch_output():
    while True:
        cmd = 'evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00'
        out = Popen(cmd,shell=True,stdout=PIPE,stderr=PIPE).stdout
        for line in iter(out.readline, b''):
            touch_queue.put(line)
        out.close()

def get_image(usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0",
              width=720,height=576,processing_queue=processing_queue,mjpg=False):
    while(True):
        try:
            usb_capture_real_path = os.path.realpath(usb_capture_id_path)
            if usb_capture_id_path == usb_capture_real_path:
                logger.error("camera not found!\twaiting...")
                sleep(3)
            else:
                logger.info(f"{usb_capture_id_path} -> {usb_capture_real_path}")
                index = int(usb_capture_real_path.split("video")[-1])
                camera = get_camera(index,width,height,mjpg)
                size = (int(camera.get(WIDTH)), int(camera.get(HEIGHT)))
                fps = (int(camera.get(FPS)))
                logger.info(f"camera resolution: {size[0]}x{size[1]}\t@ {fps}FPS")
                camera.read()
                try:
                    while camera.isOpened():
                        success, image = camera.read()
                        if success:
                            processing_queue.put(image)
                        else:
                            logger.error("bad UVC read!")
                finally:
                    logger.warning("release camera resource")
                    camera.release()
            
        except Exception as e:
            logger.error(traceback.format_tb(e.__traceback__))

def on_screen():
    while(True):
        sidebar = sidebar_base
        try:
            with open('/dev/fb0','rb+') as frame_buffer:
                while(True):
                    try:
                        sidebar = sidebar_queue.get_nowait()
                    except Empty:
                        pass
                    try:
                        final_image = display_queue.get(timeout=0.04)
                        for i in range(480):
                            frame_buffer.write(final_image[i])
                            frame_buffer.write(sidebar[i])
                        frame_buffer.seek(0)
                    except Empty:
                        logger.warning("no frame from processing thread")
        except Exception as e:
            logger.error(traceback.format_tb(e.__traceback__))

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

def dash_cam():
    while(True): # /dev/disk/by-id/ata-APPLE_SSD_TS128C_71DA5112K6IK-part1
        dashcam_id_path = \
                "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
        width, height = size = (2592, 1944)
        fps = 15.0
        timeout = 1/fps
        threadname = 'dashcam-input'
        Thread(target=get_image,name=threadname,args=(dashcam_id_path,width,height,dash_queue,True),daemon=True).start()
        logger.info(f"started thread {threadname}")
        firstframe = None
        try:
            while(True):
                stop_time = int(time()) + 1800
                out = cv2.VideoWriter(f"/media/usb/dashcam-{ctime()}.avi",fourcc,fps,size)
                if firstframe is not None:
                    out.write(firstframe)
                    firstframe = None
                while(time()<stop_time):
                    try:
                        frame = dash_queue.get(timeout=timeout)
                        out.write(frame)
                    except Empty:
                        logger.warning("missing frame from dashcam!")
                    except:
                        firstframe = frame
                        break
                out.release()
        except Exception:
            traceback.print_exc()
        finally:
            out.release()

def get_camera(camIndex:int,width,height,mjpg:bool=False,apiPreference=cv2.CAP_V4L2,brightness=25) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    if mjpg:
        camera.set(FORMAT,fourcc)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(cv2.CAP_PROP_BRIGHTNESS,brightness)
    return camera

def undistort(img):
    undist = cv2.remap(img,mapx,mapy,interpolation=CUBIC)
    image = cv2.resize(undist,SDIM,interpolation=CUBIC)[64:556]
    return image

def build_reverse_view(image):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=CUBIC)
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    return cv2.cvtColor(combo,cv2.COLOR_BGR2BGR565)

def putText(img, text, origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,thickness=2,lineType=cv2.LINE_AA):
    return cv2.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

if __name__ == "__main__":
    handler = logging.FileHandler("/root/runtime-carCam.log")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('[%(levelname)s] [%(threadName)s] %(message)s'))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    run('echo none > /sys/class/leds/PWR/trigger',shell=True)
    run('echo 0 > /sys/class/leds/PWR/brightness',shell=True)
   # dash_entry()
    begin()
