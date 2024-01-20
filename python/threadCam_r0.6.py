#!/usr/bin/env python3
import os, traceback, cv2, logging, numpy as np
from subprocess import run, Popen, PIPE
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
COLOR_LOW = (0xc4,0xe4)
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

processing_queue = SimpleQueue()
display_queue = SimpleQueue()
sidebar_queue = Queue(2)

sidebar_base = np.full((FINAL_IMAGE_HEIGHT,120,2),COLOR_LOW,np.uint8)
for i in range(160,FINAL_IMAGE_HEIGHT):
    for j in range(120):
        color = np.uint16(i*2&(i-255-j))
        high = np.uint8(color >> 8)
        low = np.uint8(color)
        sidebar_base[i][j] = low, high

no_signal_frame = cv2.putText(
    np.full((FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

keyboard_interrupt_flag = False

def begin():
    global keyboard_interrupt_flag # signal for threads to end
    global display_queue, processing_queue
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
        for function in [touch_screen,on_screen,get_image,dash_cam,sidebar_builder]:
            thread = Thread(target=function,name=function.__name__)
            thread.start()
            threads.append(thread)
            logger.info(f"started thread {function.__name__}")
        sidebar = sidebar_base
        while not keyboard_interrupt_flag:
            try:
                image = processing_queue.get(block=False)
                processed = build_reverse_view(undistort(image),sidebar)
                display_queue.put(processed)
            except Empty:
                logger.warning("no frame from camera thread")
            try:
                sidebar = sidebar_queue.get_nowait()
            except Empty:
                pass
    except Exception as ex:
        keyboard_interrupt_flag = True
        traceback.print_exc()
        logger.exception(ex)
    finally:
        msg = f'processing: {processing_queue.qsize()}, display: {display_queue.qsize()}'
        print(msg)
        logger.info(msg)
        if wifi_flag:
            run('ip link set wlan0 up',shell=True)
        for thread in threads:
            thread.join()

def touch_screen():
    global keyboard_interrupt_flag
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
                            keyboard_interrupt_flag = True
                    else:
                        x = None
                elif keyboard_interrupt_flag: break
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        finally:
            stdout.close()
            process.terminate()
        if keyboard_interrupt_flag: break
    logger.info("exit touchscreen routine")

def on_screen():
    global display_queue
    while True:
        try:
            with open('/dev/fb0','rb+') as frame_buffer:
                while True:
                    try:
                        image = display_queue.get_nowait()
                        frame_buffer.write(image)
                        frame_buffer.seek(0)
                    except:
                        logger.warning("no image from display queue")
                    if keyboard_interrupt_flag: break
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        if keyboard_interrupt_flag: break
    logger.info("exit onscreen routine")

def get_image():
    global processing_queue
    width, height = DIM
    usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
    while True:
        try:
            usb_capture_real_path = os.path.realpath(usb_capture_id_path)
            if usb_capture_id_path == usb_capture_real_path:
                logger.error("camera not found!\twaiting...")
                sleep(2)
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
                        if keyboard_interrupt_flag: break
                        success, image = camera.read()
                        if success:
                            processing_queue.put(image)
                        else:
                            logger.error("bad UVC read!")
                finally:
                    logger.warning("release camera resource")
                    camera.release()
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        if keyboard_interrupt_flag: break
    logger.info("exit camera routine")

def sidebar_builder():
    global sidebar_queue
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
                if keyboard_interrupt_flag: break
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        finally:
            elm.close()
        if keyboard_interrupt_flag: break
        sleep(2)
    logger.info("exit sidebar routine")

def dash_cam():
    fps = 15
    width, height = 2592, 1944
    runtime = fps * 60 * 30
    camPath = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    while True:
        try:
            run(f"v4l2-ctl -d {camPath} -v width={width},height={height},pixelformat=MJPG",shell=True)
            filepath = f"/media/usb/dashcam_{time():.0f}.mjpeg"
            command = f"v4l2-ctl -d {camPath} --stream-mmap=3 --stream-count={runtime} --stream-to={filepath}"
            sp = Popen(command,shell=True,stdout=PIPE,stderr=PIPE) # ,creationflags=BELOW_NORMAL_PRIORITY_CLASS) # ABOVE_NORMAL_ HIGH_ IDLE_
            while (sp.returncode is None):
                if keyboard_interrupt_flag:
                    sp.send_signal(SIGINT)
                sleep(0.19)
        except Exception as e:
            logger.exception(e)
        finally:
            if sp.returncode is None:
                sp.kill()
        if keyboard_interrupt_flag: break
    logger.info("exit dashcam routine")

def get_camera(camIndex:int,width,height,apiPreference=cv2.CAP_V4L2,brightness=25) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(cv2.CAP_PROP_BRIGHTNESS,brightness)
    return camera

def undistort(image):
    undistorted = cv2.remap(image,mapx,mapy,interpolation=CUBIC)
    return cv2.resize(undistorted,SDIM,interpolation=CUBIC)[64:556]

def build_reverse_view(image,sidebar):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=CUBIC)
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    return cv2.hconcat(cv2.cvtColor(combo,cv2.COLOR_BGR2BGR565),sidebar)

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
