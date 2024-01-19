#!/usr/bin/env python3
import os, traceback, cv2, logging, numpy as np
from subprocess import run, Popen, PIPE, CREATE_NEW_PROCESS_GROUP
from signal import SIGINT
from threading  import Thread
from queue import Queue, Empty, Full, SimpleQueue
from time import sleep, time
from ELM327 import ELM327

FINAL_IMAGE_WIDTH = 1480
FINAL_IMAGE_HEIGHT = 480
DIM = (720,576) # PAL video dimensions
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

# below values are specific to my backup camera run thru my knock-off easy-cap calibrated with my phone screen. YMMV
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
# calculate camera values to undistort image
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)

display_queue = SimpleQueue()
sidebar_queue = Queue(2)

sidebar_base = np.full((FINAL_IMAGE_HEIGHT,120),COLOR_LOW,np.uint16)
for i in range(160,FINAL_IMAGE_HEIGHT):
    for j in range(120):
        sidebar_base[i][j] = np.uint16(i*2&(i-255-j))

no_signal_frame = cv2.putText(
    np.full((FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

keyboard_interrupt = False
ready = False

def begin():
    global keyboard_interrupt # signal for threads to end
    global ready
    wifi_flag = False
    threads = []
    try: # is the wifi connected?
        process = run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        if process.stdout == b'up\n':
            pass # raise KeyboardInterrupt("wifi connected")
        else: # turn off radio, no need to waste power
           wifi_flag = True 
           run('ip link set wlan0 down',shell=True)
       # start each thread
        for function in [touch_screen,get_image,sidebar_builder,dash_cam]:
            thread = Thread(target=function,name=function.__name__)
            thread.start()
            threads.append(thread)
            logger.info(f"started thread {function.__name__}")
        while not keyboard_interrupt:
            sidebar = sidebar_base
            with open('/dev/fb0','rb+') as frame_buffer:
               # display_queue = SimpleQueue()
                ready = True # many seconds of lag currently, maybe stacking frames before disp init?
                while True:
                    try:
                       # while not display_queue.empty():
                       #     image = display_queue.get(block=False)
                        image = display_queue.get(timeout=0.04)  # maybe get_nowait?
                        image = build_reverse_view(undistort(image))
                        for i in range(480):
                            frame_buffer.write(image[i])
                            frame_buffer.write(sidebar[i])
                        frame_buffer.seek(0)
                    except Empty:
                        logger.warning("no frame from camera thread")
                    try:
                        sidebar = sidebar_queue.get_nowait()
                    except Empty:
                        pass
                    if keyboard_interrupt: break
    except Exception as ex:
        logger.error(traceback.format_tb(ex.__traceback__))
    except KeyboardInterrupt as kbx:
        logger.info(traceback.format_tb(kbx.__traceback__))
    finally:
        keyboard_interrupt = True
        if wifi_flag:
            run('ip link set wlan0 up',shell=True)
        for thread in threads:
            thread.join()

def touch_screen():
    global keyboard_interrupt
    command = 'evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00'
    while True:
        try:
            process = Popen(command,shell=True,stdout=PIPE,stderr=PIPE)
            stdout = process.stdout
            x = None
            for line in iter(stdout.readline, b''):
                if(b'POSITION_X' in line and b'value' in line):
                    x = int(line.decode().split('value')[-1])
                elif x is not None:
                    if x >= FINAL_IMAGE_WIDTH:
                        y = int(line.decode().split('value')[-1])
                        if y > 239:
                            logger.warning(f"exit;\ttouch input (x->,y\/): {x},{y}")
                            keyboard_interrupt = True
                    else:
                        x = None
                elif keyboard_interrupt: break
        except Exception as e:
            logger.error(traceback.format_tb(e.__traceback__))
        finally:
            stdout.close()
            process.terminate()
        if keyboard_interrupt: break

def get_image():
    width, height = DIM
    usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
    while True:
        try:
            usb_capture_real_path = os.path.realpath(usb_capture_id_path)
            if usb_capture_id_path == usb_capture_real_path:
                logger.error("camera not found!\twaiting...")
                sleep(3)
            else:
                logger.info(f"{usb_capture_id_path} -> {usb_capture_real_path}")
                index = int(usb_capture_real_path.split("video")[-1])
                camera = get_camera(index,width,height)
                size = (int(camera.get(WIDTH)), int(camera.get(HEIGHT)))
                fps = (int(camera.get(FPS)))
                logger.info(f"camera resolution: {size[0]}x{size[1]}\t@ {fps}FPS")
                camera.read()
                try:
                    while camera.isOpened():
                        success, image = camera.read()
                        if success:
                            if ready:
                                display_queue.put(image)
                        elif keyboard_interrupt: break
                        else:
                            logger.error("bad UVC read!")
                finally:
                    logger.warning("release camera resource")
                    camera.release()
        except Exception as e:
            logger.error(traceback.format_tb(e.__traceback__))
        if keyboard_interrupt: break

def sidebar_builder():
    while True:
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
                if keyboard_interrupt: break
        except Exception as e:
            traceback.print_exc()
            logger.error(traceback.format_tb(e.__traceback__))
        finally:
            elm.close()
        if keyboard_interrupt: break
        sleep(2)
    logger.info("leaving")

def dash_cam():
    fps = 15
    width, height = 2592, 1944
    runtime = fps * 60 * 30
    camPath = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    creationFlags = CREATE_NEW_PROCESS_GROUP
    while True:
        try:
            run(f"v4l2-ctl -d {camPath} -v width={width},height={height},pixelformat=MJPG",shell=True)
            filepath = f"/media/usb/dashcam_{time():.0f}.mjpeg"
            command = f"v4l2-ctl -d {camPath} --stream-mmap=3 --stream-count={runtime} --stream-to={filepath}"
            sp = Popen(command,shell=True,stdout=PIPE,stderr=PIPE,creationflags=creationFlags) # +BELOW_NORMAL_PRIORITY_CLASS) # ABOVE_NORMAL_ HIGH_ IDLE_
            while (sp.returncode is None):
                if keyboard_interrupt:
                    sp.send_signal(SIGINT)
                sleep(0.19)
        except Exception as e:
            logger.error(traceback.format_tb(e.__traceback__))
        finally:
            if sp.returncode is None:
                sp.kill()
        if keyboard_interrupt: break

def get_camera(camIndex:int,width,height,apiPreference=cv2.CAP_V4L2,brightness=25) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(cv2.CAP_PROP_BRIGHTNESS,brightness)
    return camera

def undistort(image):
    undistorted = cv2.remap(image,mapx,mapy,interpolation=CUBIC)
    return cv2.resize(undistorted,SDIM,interpolation=CUBIC)[64:556]

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
    logger.addHandler(handler)  # turn off bright red LED
    run('echo none > /sys/class/leds/PWR/trigger',shell=True)
    run('echo 0 > /sys/class/leds/PWR/brightness',shell=True)
    begin()
