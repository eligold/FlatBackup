#!/usr/bin/env python3
import os, sys, traceback, cv2, logging, numpy as np #, asyncio, aiofiles
from subprocess import run, Popen, PIPE
from threading  import Thread
from queue import Queue, Empty, Full
from time import sleep
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
touch_queue = Queue()
output_queue = Queue()
sidebar = np.full((IMAGE_HEIGHT,120),COLOR_LOW,np.uint16)
for i in range(480): #(320,480):
    for j in range(120):
        sidebar[i][j] = np.uint16(i*2&(i-255-j))
no_signal_frame = cv2.putText(
    np.full((IMAGE_HEIGHT,IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def begin(): # /dev/disk/by-id/ata-APPLE_SSD_TS128C_71DA5112K6IK-part1
    # dashcam_id_path = \
    #     "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    # dashcam = getCamera(int(os.path.realpath(dashcam_id_path).split("video")[-1]))
    try:
        res=run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        if res.stdout == b'up\n':
            pass # raise KeyboardInterrupt
        else:
           run('ip link set wlan0 down',shell=True)
        for f in [get_image,on_screen]:
            t = Thread(target=f,name=f.__name__)
            t.daemon = True
            t.start()
            logger.info(f"started thread {f.__name__}")
        cmd = Popen('evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00',
                    shell=True,stdout=PIPE,stderr=PIPE)
        touch_thread = Thread(target=enqueue_output, args=(cmd.stdout, touch_queue))
        touch_thread.daemon = True
        touch_thread.start()
        while(True):
            try:
                line = touch_queue.get_nowait()
                if(b'POSITION_X' in line and b'value' in line):
                    if int(line.decode().split('value')[-1]) > IMAGE_WIDTH:
                        line = touch_queue.get_nowait()
                        if int(line.decode().split('value')[-1]) < 240:
                            show_graph = not show_graph
                        else:
                            raise KeyboardInterrupt("touch input")
            except Empty:
                sleep(0.019)
    except KeyboardInterrupt:
        print("deuces")
    except:
        traceback.print_exc()
    finally:
        logger.warning(f"image queue size: {output_queue.qsize()}")

def get_camera(camIndex:int,apiPreference=cv2.CAP_V4L2) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    camera.set(BRIGHTNESS,25)
    return camera

def get_image(output_queue=output_queue):
    usb_capture_id_path = "/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
    usb_capture_real_path = os.path.realpath(usb_capture_id_path)
    logger.info(f"{usb_capture_id_path} -> {usb_capture_real_path}")
    index = int(usb_capture_real_path.split("video")[-1])
    camera = get_camera(index)
    camera.read()
    try:
        while camera.isOpened():
            success, image = camera.read()
            if success:
                undist_image = undistort(image)
                output_queue.put(undist_image)
    finally:
        logger.warning("release camera resource")
        camera.release()

def on_screen(output_queue=output_queue):
    with open('/dev/fb0','rb+') as frame_buffer:
        while(True):
            try:
                image = output_queue.get()
            except Empty:
                logger.warning("no image to display")
            final_image = build_reverse_view(image)
            for i in range(480):
                frame_buffer.write(final_image[i])
                frame_buffer.write(sidebar[i])
            frame_buffer.seek(0)

def undistort(img):
    undist = cv2.remap(img,mapx,mapy,interpolation=cv2.INTER_LANCZOS4)
    image = cv2.resize(undist,SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return image

def build_reverse_view(image):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4)
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    final_image = cv2.cvtColor(combo,CVT3TO2B)
    return final_image

if __name__ == "__main__":
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('[%(levelname)s] [%(threadName)s] %(message)s'))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    run('echo none > /sys/class/leds/PWR/trigger',shell=True)
    run('echo 0 > /sys/class/leds/PWR/brightness',shell=True)
    begin()
    # run(['bash','-c','ip link set wlan0 up'])
