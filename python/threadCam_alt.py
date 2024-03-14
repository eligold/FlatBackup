#!/usr/bin/env python3
import logging, asyncio
from time import time
from queue import Empty, Full, SimpleQueue
from evdev import InputDevice, ecodes
from v4l2py import Device, VideoCapture
from gpiozero import CPUTemperature
from threading  import Thread
from collections import deque

from Constants import *
from ELM327 import ELM327

# communications between threads:
dash_signal_queue = SimpleQueue()
dashcam_queue = SimpleQueue()
display_queue = SimpleQueue()
sidebar_queue = SimpleQueue()
signal_queue = SimpleQueue()

psi_list = deque(maxlen=PSI_BUFFER_DEPTH)
show_graph = False
exit_flag = False

no_signal_frame = np.full((FINAL_IMAGE_HEIGHT, FINAL_IMAGE_WIDTH, 2), COLOR_BAD, np.uint8)
no_signal_frame = putText(no_signal_frame, "No Signal", (500,200))

def _change_sidebar(color=COLOR_LOW):
    global sidebar_base
    sidebar_base = np.full((SIDEBAR_HEIGHT, SIDEBAR_WIDTH, 2), color, np.uint8)
def _sidebar_hot(): _change_sidebar(COLOR_REC)
_change_sidebar()

intemp = CPUTemperature(threshold=65.0,event_delay=1.9)
intemp.when_activated = _sidebar_hot
intemp.when_deactivated = _change_sidebar

frame_buffer = np.memmap("/dev/fb0", dtype='uint8', shape=(SCREEN_HEIGHT, SCREEN_WIDTH, 2))
frame_buffer[:] = np.fromfunction((lambda i,j,k: (np.uint8(j*i*2&(i-199-j)>>8*k))),(480,1600,2),dtype=np.uint8)
frame_buffer[:160,-SIDEBAR_WIDTH:] = sidebar_base
try: frame_buffer[160:,-SIDEBAR_WIDTH:] = cv.cvtColor(cv.imread("/root/newSidebar.png"),BGR565)[1:]
except: pass

def _display_message(text,loc=(500,250),color=COLOR_LAYM,fontScale=3,thickness=4,fb=frame_buffer):
    fb[:,:-SIDEBAR_WIDTH] = putText(fb[:,:-SIDEBAR_WIDTH], text, loc, color,
                                    fontScale=fontScale, thickness=thickness)
_display_message("Welcome back sir", (500,135))

def touch_runner():
    asyncio.run(touch_input())

def data():
    global sidebar_queue, exit_flag, speed, gear
    speed, gear, car_conn = None, None, None
    started_names = []
    start_time = time()
    wifi_flag = False ## DEBUG ######
    try:
        _display_message("Initializing") #                            \\ YOOHOO //
        if bash('cat /sys/class/net/wlan0/operstate').stdout == b'up\n': pass
           # raise KeyboardInterrupt("wifi connected") # else turn off radio to save power
        else: wifi_flag = shell('ip link set wlan0 down').wait() == 0
        for function, name in [
                (touch_runner,"touch"),
                (get_image, "read"),
                (on_screen, "show"),
                (dashcam, "dash"),
                (save_video, "save")]:
            Thread(target=function, name=name, daemon=True).start()
            started_names.append(name)
        _display_message("Stay frosty", (500,380))
        while not exit_flag:
            try:
                car_conn = ELM327()
                while not exit_flag:
                    make_sidebar(car_conn.psi())
                    speed = car_conn.speed()
                    if start_time is not None and time() < start_time + 7:
                        bash("bluetoothctl connect `cat ~/.btmac`")
                        start_time = None
            except Exception as e: logger.exception(e)
            finally:
                if car_conn: car_conn.close()
    except KeyboardInterrupt: exit_flag = True
    except Exception as e: logger.exception(e)
    finally:
        if not exit_flag: exit_flag = True
        if car_conn: car_conn.close()
        if wifi_flag: bash('ip link set wlan0 up')

def make_sidebar(psi, psi_list=psi_list):
    try:
        entry = max(FDIM[1] - 2 * PPPSI - 15 - int(psi*PPPSI),3)
        psi_list.append(entry)
        sidebar = sidebar_base.copy()
        sidebar = \
                putText(sidebar, f"{psi:.1f}",(4,57), color=COLOR_NORMAL, thickness=3)
        sidebar = putText(sidebar, "BAR" if psi < 0.0 else "PSI", (38,95), color=COLOR_BAD)
        sidebar_queue.put(sidebar)
    except Exception as e: logger.exception(e)

def on_screen(display_queue=display_queue):
    _display_message("Initializing..")
    check_time = time() + 5
    while not exit_flag:
        try:
            image = build_output_image(display_queue.get(timeout=0.057))
            if show_graph: image = addOverlay(image)
            image = cv.cvtColor(image, BGR565)
            if exit_flag: break
        except Empty:
            if time() > check_time: logger.error("dropped frame!")
        except Exception as e: logger.exception(e)
        else: display_image(image)
        if exit_flag: break

def build_graph(graph_list, depth=PSI_BUFFER_DEPTH):
    coordinates=np.column_stack((np.array(graph_list),np.arange(depth-len(graph_list)+1,depth+1)))
    for i in range(4): frame_buffer[coordinates[:, 0]-1+i//2, coordinates[:, 1]-1+i%2] = (0xf8,0)
    frame_buffer[coordinates[:, 0]+1, coordinates[:, 1]+1] = (0x30,0x21) # SHADOW
    frame_buffer[coordinates[:, 0]+1, coordinates[:, 1]] = (0x30,0x21)
    frame_buffer[coordinates[:, 0], coordinates[:, 1]+1] = (0x30,0x21)

def display_image(img, frame_buffer=frame_buffer, queue=sidebar_queue, signal_queue=signal_queue):
    try:
        frame_buffer[:,:-SIDEBAR_WIDTH] = img
        try: frame_buffer[:SIDEBAR_HEIGHT,-SIDEBAR_WIDTH:] = queue.get(block=False)
        except Empty: pass
        if show_graph: build_graph(psi_list.copy())
        frame_buffer.flush()
        try: signal_queue.put(None)
        except Full: pass
    except Exception as e: logger.exception(e)

def save_video(queue=dashcam_queue, signal_queue=dash_signal_queue, camera=None,
               width=DASHCAM_IMAGE_WIDTH, height=DASHCAM_IMAGE_HEIGHT,fps=15):
    fourcc = cv.VideoWriter_fourcc(*'H264')
    breakout = False
    output = None
    if camera is None: _display_message("Initializing....")
    while not (exit_flag and breakout):
        try:
            output = cv.VideoWriter(get_video_path(camera), fourcc, fps, (width, height))
            while not exit_flag:
                try:
                    print("here")
                    image = queue.get()
                    try: signal_queue.put(None)
                    except Full: pass
                    if image is None: raise Empty
                except Empty: pass
                else: break
            while not exit_flag:
                try:
                    image = queue.get(timeout=0.076)
                    breakout = (image is None and camera is not None)
                # if speed: pass # (speed,frame_num) -> csv file
                    if image is not None:
                        print("w",end="")
                        output.write(image)
                    if breakout: break
                    if camera is None:
                        try:
                            print("s",end="")
                            signal_queue.put(None)
                        except Full: pass
                except Empty: pass
        except Exception as e: logger.exception(e)
        finally:
            if output is not None: output.release()

def get_image(camera_path=usb_capture_id_path, width=DIM[0], height=DIM[1], video_format="YUYV",
                     queue=display_queue, signal_queue=signal_queue):
    if video_format == "YUYV": _display_message("Initializing.")
    while not exit_flag:
        signal_queue.put(None)
        try:
            with Device.from_id(extract_index(camera_path)) as cam:
                video_capture = VideoCapture(cam)
                video_capture.set_format(width,height,video_format)
                with video_capture as stream:
                    for frame in stream:
                        while not exit_flag:
                            try: signal_queue.get(timeout=0.095)
                            except Empty: pass
                            else: break
                        if exit_flag: break
                        if video_format == "MJPG": image = cv.imdecode(frame.array, COLOR)
                        else: image = cv.cvtColor(frame.array.reshape(height, width, 2), YUYV)
                        queue.put(image)
        except Exception as e: logger.exception(e)

def dashcam(width=DASHCAM_IMAGE_WIDTH, height=DASHCAM_IMAGE_HEIGHT):
    global dash_signal_queue, dashcam_queue
    camPath = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    _display_message("Initializing...")
    get_image(camPath, width, height, "MJPG", dashcam_queue, dash_signal_queue)

async def touch_input(show_graph=show_graph,exit_flag=exit_flag):
    last_time = time()
    x, touch_input_device = None, None
    while not exit_flag:
        try:
            touch_input_device = InputDevice("/dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00")
            async for event in touch_input_device.async_read_loop():
                if time() > last_time + 0.38 and event.type == ecodes.EV_ABS:
                    if event.code == 0 and event.value > FINAL_IMAGE_WIDTH: x = event.value
                    else:
                        if x is not None and event.code == 1:
                            if event.value > SCREEN_HEIGHT/2:
                                raise KeyboardInterrupt(f'touch input(X ⇁,Y ⇃) -> {x},{event.value}')
                            else: show_graph = not show_graph
                        x = None
                        last_time = time()
                if exit_flag: break
                print("here touch")
        except KeyboardInterrupt as kbi:
            exit_flag = True
            logger.info(kbi.msg)
        except Exception as e: logger.exception(e)
        finally:
            print("close touch")
            if touch_input_device: touch_input_device.close()

if __name__ == "__main__":
    fmtString = '%(asctime)s[%(levelname)-4s]%(threadName)s: %(message)s'
    handler = logging.FileHandler("/root/runtime-carCam.log")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(fmtString))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler) # turn off red LED
    bash('echo none > /sys/class/leds/PWR/trigger; echo 0 > /sys/class/leds/PWR/brightness')
    data()
