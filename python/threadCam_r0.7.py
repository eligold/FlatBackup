#!/usr/bin/env python3
import os, traceback, cv2, logging, numpy as np
from subprocess import run, Popen, PIPE
from signal import SIGINT
from threading  import Thread
from queue import Queue, Empty, Full, SimpleQueue
from time import sleep, ctime
from ELM327 import ELM327

DASHCAM_FPS = 15
DASHCAM_IMAGE_WIDTH = 2592
DASHCAM_IMAGE_HEIGHT = 1944
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

# below values are specific to my backup camera run thru my knock-off easy-cap calibrated with my
K = np.array([                                                               # phone screen. YMMV
        [309.41085232860985,                0.0, 355.4094868125207],
        [0.0,                329.90981352161924, 292.2015284112677],
        [0.0,                               0.0,               1.0]])
D = np.array([
    [0.013301372417500422],
    [0.03857464918863361],
    [0.004117306147228716],
    [-0.008896442339724364]])
# calculate camera values to undistort image
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv2.CV_32FC1)

processing_queue = SimpleQueue()
display_queue = SimpleQueue()
sidebar_queue = Queue(2)

sidebar_base = np.full((FINAL_IMAGE_HEIGHT,120),COLOR_LOW,np.uint16)
for i in range(160,FINAL_IMAGE_HEIGHT):
    for j in range(120):
        sidebar_base[i][j] = np.uint16(i*2&(i-255-j))

no_signal_frame = cv2.putText(
    np.full((FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH),COLOR_BAD,np.uint16),
    "No Signal!",(500,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0xc4,0xe4), 2, cv2.LINE_AA)

keyboard_interrupt_flag = False

def bash(cmd:str,shell=True,capture_output=True,check=False):
    try:
        return run(cmd,shell=shell,capture_output=capture_output,check=check)
    except Exception as e:
        traceback.print_exc()
        logger.exception(e)

def unabashed(cmd:str,shell=True,stdout=PIPE,stderr=PIPE):
    return Popen(cmd,shell=shell,stdout=stdout,stderr=stderr)

def main():
    global keyboard_interrupt_flag # signal for threads to end
    global display_queue, processing_queue
    wifi_flag = False
    threads = []
    dashcam_process = None
    dashcam_counter = 0
    dashcam_switch = True
    try: # is the wifi connected?
        wifi_process = run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        if wifi_process.stdout == b'up\n':
            pass # raise KeyboardInterrupt("wifi connected")
        else: # turn off radio, no need to waste power
           wifi_flag = True 
           bash('ip link set wlan0 down')
           bluetooth_process = bash('bluetoothctl << EOF\nagent NoInputNoOutput\ndefault-agent\n\
                    discoverable on\nconnect 00:00:00:00:00\ndiscoverable off\nEOF',check=True)
           logger.info(bluetooth_process.stdout)
        for function, name in [
                (touch_screen,"touch"),
                (sidebar_builder,"sdbr"),
                (undistort_and_panelize,"proc"),
                (on_screen,"show"),
                (get_image,"read")]:
            thread = Thread(target=function,name=name)
            thread.start()          # start each thread
            threads.append(thread)  # store them for termination later
            logger.info(f"started thread {name}")
        try:
            dashcam_process = start_dash_cam()
        except Exception as e:
            logger.exception(e)
        while not keyboard_interrupt_flag:
            if dashcam_process is not None and dashcam_switch:
                if dashcam_process.returncode is None:
                    line = dashcam_process.stdout.readline().decode()
                    if "dropped" in line:
                        logger.info(line)
                elif not keyboard_interrupt_flag:
                    try:
                        dashcam_process = start_dash_cam()
                    except Exception as e:
                        logger.exception(e)
                        dashcam_counter += 1
                        if dashcam_counter > 2:
                            logger.error("failed to start dashcam 3x, giving up")
                            dashcam_switch = False
    except Exception as ex:
        keyboard_interrupt_flag = True
        traceback.print_exc()
        logger.exception(ex)
    finally:
        keyboard_interrupt_flag = True
        if dashcam_process is not None:
            if dashcam_process.returncode is None:
                dashcam_process.terminate()
                sleep(1.9)
                if dashcam_process.returncode is None:
                    dashcam_process.kill()
        if wifi_flag:
           # manage BT conn here maybe
            bash('ip link set wlan0 up',check=False)
        for thread in threads:
            thread.join()

def touch_screen():
    global keyboard_interrupt_flag
    command = 'evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00'
    stdout = None
    while not keyboard_interrupt_flag:
        try:
            process = unabashed(command)
            stdout = process.stdout   # watch output of evtest for touch coordinates
            if('POSITION_X' in line and 'value' in line):
                x = int(line.split('value')[-1])
                if x >= FINAL_IMAGE_WIDTH:
                    line = stdout.readline().decode()
                    y = int(line.split('value')[-1])
                    if y > 239:
                        logger.warning(f"exit;\ttouch input (X=>,Y=v) {x},{y}")
                        keyboard_interrupt_flag = True
            if keyboard_interrupt_flag: break
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        finally:
            if stdout is not None:
                stdout.close()
            process.terminate()
        if keyboard_interrupt_flag: break
    logger.info("exit touchscreen routine")
    return

def undistort_and_panelize():
    global processing_queue, display_queue
    while not keyboard_interrupt_flag:
        try:
            image = processing_queue.get(timeout=0.04)
            processed = build_reverse_view(undistort(image))
            display_queue.put(processed)
        except Empty:
            pass
    return

def on_screen():
    global display_queue, sidebar_queue
    while not keyboard_interrupt_flag:
        try:
            sidebar = sidebar_base
            with open('/dev/fb0','rb+') as frame_buffer:
                while True:
                    try:
                        image = display_queue.get(timeout=0.04)
                        for i in range(FINAL_IMAGE_HEIGHT):
                            frame_buffer.write(image[i])
                            frame_buffer.write(sidebar[i])
                        frame_buffer.seek(0)
                    except Empty:
                        pass
                    try:
                        sidebar = sidebar_queue.get(block=False)
                    except Empty:
                        pass
                    if keyboard_interrupt_flag: break
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        if keyboard_interrupt_flag: break
    return

def get_image():
    global processing_queue
    width, height = DIM
    usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
    image = None
    while not keyboard_interrupt_flag:
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
                            pass
                finally:
                    logger.warning("release camera resource")
                    camera.release()
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        if success:
            cv2.imwrite("sample.jpg",image)
        if keyboard_interrupt_flag: break
    return

def sidebar_builder():
    global sidebar_queue
    while not keyboard_interrupt_flag:
        try:
            elm = ELM327()
            while not keyboard_interrupt_flag:
                sidebar = sidebar_base.copy()
                psi = elm.psi()
                sidebar = putText(
                        sidebar,f"{psi:.1f}",(4,57),color=COLOR_NORMAL,fontScale=1.19,thickness=3)
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
        else: sleep(2)
    return

def start_dash_cam():    # sets camera attributes for proper output size and format before running
    runtime = DASHCAM_FPS * 60 * 30
    camPath = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    format = f"width={DASHCAM_IMAGE_WIDTH},height={DASHCAM_IMAGE_HEIGHT},pixelformat=MJPG"
    bash(f"v4l2-ctl -d {camPath} -v {format}",check=False)
    filepath = f"/media/usb/dashcam_{ctime()}.mjpeg"
    cmd = f"v4l2-ctl -d {camPath} --stream-mmap=3 --stream-count={runtime} --stream-to={filepath}"
    return unabashed(cmd)

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
    logger.addHandler(handler)      # turn off bright red LED
    run('echo none > /sys/class/leds/PWR/trigger',shell=True)
    run('echo 0 > /sys/class/leds/PWR/brightness',shell=True)
    main()
