#!/usr/bin/env python3
import logging, ffmpeg, os
from logging.handlers import RotatingFileHandler
from multiprocessing import Process, Pipe
from threading import Thread
from subprocess import Popen, run
from linuxpy.video.device import Device
from gpiozero import CPUTemperature
from evdev import InputDevice
from queue import SimpleQueue, Empty
from collections import deque
from time import time
# local imports
from Constants import *
from ELM327 import ELM327 # TODO REWORK FOR EXTERNAL GAUGE
# communications between threads:
touch_queue = SimpleQueue()
psi_list = deque(maxlen=PSI_BUFFER_DEPTH)
# communications between processes:
backup_pipe1, backup_pipe2 = Pipe()
sidebar_pipe1, sidebar_pipe2 = Pipe()
# global flag helps coordinate PSI data transmission but is a bad idea with this tenuous, fragile,
show_graph = False # hare-brained construct of Threads and Processes
# height, width, channels = image.shape

with open('/root/.btmac','r') as file: mac = file.readline() # load phone MAC address for BT music
def _sidebar_hot(): _change_sidebar(sidebar_hot)
def _change_sidebar(img=sidebar_fine): # convenience functions change sidebar color with CPU temp
    global sidebar_base # this is rickety at best
    sidebar_base=img.copy()
_change_sidebar() # run it to instantiate a sidebar prototype

# CPU temp tracked with gpio library reading internal ADC
intemp = CPUTemperature(threshold=HIGH_TEMP,event_delay=1.9)
intemp.when_activated = _sidebar_hot
intemp.when_deactivated = _change_sidebar

# Display frame buffer memory mapped with numpy
frame_buffer = np.memmap('/dev/fb0',dtype='uint8',shape=SCREEN_SHAPE)
frame_buffer[:160,-SIDEBAR_WIDTH:] = sidebar_base # display sidebar
frame_buffer[:] = np.fromfunction( # this function generates a cool pattern on the screen
    (lambda i,j,k: (np.uint8(j*i*2&(i-199-j)>>8*k))),SCREEN_SHAPE,dtype=np.uint8)

# get free blocks on drive to calculate utilization and display warning icon if nearly full
stat = os.statvfs(storageRoot)
if int(100*stat.f_bfree/stat.f_blocks) <= 5: frame_buffer[160:280,-SIDEBAR_WIDTH:] = usb5percent
elif int(100*stat.f_bfree/stat.f_blocks) < 10: frame_buffer[160:280,-SIDEBAR_WIDTH:] = usb10percent

def show(back_pipe=backup_pipe1, side_pipe=sidebar_pipe1): # The real meat and potatoes of it
    show_graph, view_flag, exit_flag = False, False, False # flags for managing views, exiting
    dash_proc = None # will need to gracefully end this process only
    lines = [] # empty list for ffmpeg output lines
    Process(target=get_image, name='read').start() # Start reading from the camera first thing
    Popen(f'sleep 5 && bluetoothctl connect {mac}',shell=True) # connect phone, delay req?
    try: inputPath = f'/dev/video{extract_index(dashCamPath)}'
    except AssertionError: logger.error('dashcam not found') # TODO display no dashcam on screen
    else: # construct an asynchronous process for saving dashcam video to external disk
        dash_proc = (ffmpeg.input(inputPath, format='v4l2', input_format='mjpeg', framerate=15,
                                  video_size=(2048,1536)) # The pi chokes at full 2592x1944 output
            .output(get_video_path(), vcodec='copy', framerate=15, format='matroska')
            .overwrite_output().run_async(pipe_stderr=True)) # ,pipe_stdin=True)) # <- b'q'
        stderr_iterator = iter(dash_proc.stderr.readline, b'') # for interpreting ffmpeg output
    while not exit_flag: # main loop to process and display images alongside car performance data
        if side_pipe.poll(): frame_buffer[:SIDEBAR_HEIGHT,-SIDEBAR_WIDTH:] = side_pipe.recv()
        if back_pipe.poll(FRAME_DELAY): # check pipes for sidebars, frames, or messages
            data_msg = back_pipe.recv()
            if isinstance(data_msg,str): # strings must be messages
                if "VIEW" == data_msg: 
                    view_flag = not view_flag
                elif "GRAPH" == data_msg: show_graph = not show_graph
                elif "STOP" == data_msg: exit_flag = True
                else: logger.warning(f'bad message from data pipe: {data_msg}')
            elif not exit_flag: # check if the image is delivered with psi data:
                img_data = data_msg[0] if len(data_msg) == 2 else data_msg
                back_image = cv.cvtColor(img_data,YUV422) # convert raw image to useful format
                if view_flag: image = output_alt(adv(back_image)) # normal view or unbroken image?
                else: image = build_output_image(adv(back_image))
                if show_graph: image = addOverlay(image) # check for display PSI data
                frame_buffer[:,:-SIDEBAR_WIDTH] = cv.cvtColor(image, BGRA) # frame buffer is 32-bit
                if show_graph: build_graph(data_msg[1], frame_buffer) # boost over time
                frame_buffer.flush() # round and round we go to keep OS happy
        if exit_flag: break # idk why i would need this but...
    if dash_proc is not None: # only process we need to handle is dashcam to ensure video is saved
        try: dash_proc.terminate() # need to try sending b'q' to stdin
        except Exception as e: logger.exception(e)
        finally: dash_proc.kill()
        for line in stderr_iterator:
            line = line.decode().strip()
            if line.startswith('frame='): line = line.split('\r')[-1]
            lines.append(line)
        dash_proc.stderr.close()
    for line in lines: logger.info(line)
   # disconnect phone to prevent audio issues. TODO don't stop the music!
    run(f'bluetoothctl disconnect {mac}', shell=True)
    Popen('shutdown -h now', shell=True)

def touch_thread(queue=touch_queue): # Touchscreen Thread runs from get_image process
    touch_input_device = None
    touch_time = time() + 0.19
    while True:
        if time() > touch_time:
            touch_msg = None
            try:
                x = None
                if touch_input_device is None: touch_input_device = InputDevice(touchDevPath)
                for event in touch_input_device.read():
                    if event.type == 3: touch_msg = _touch_logic(event,x)
                    if touch_msg is not None:
                        if isinstance(touch_msg,int): x = touch_msg
                        else: queue.put(touch_msg)
                        touch_msg = None
            except BlockingIOError: pass # no new input
            except (OSError, FileNotFoundError): # janky mcu is ailing
                if touch_input_device is not None: touch_input_device.close()
                touch_input_device = None
                touch_time = time() + 0.38

def _touch_logic(event,x): # logic to be improved for interpreting touchscreen input
    global show_graph # can use global var in threads from cam process. This is not advised.
    if event.code == 0: # Code 0 gives the X coordinate
        if event.value > FINAL_IMAGE_WIDTH: return event.value
        else: return "VIEW" # tap image to change view
    else: # Sidebar actions defined here
        if x is not None and event.code == 1:
            if event.value > SCREEN_HEIGHT/2: # bottom half exits
                logger.info(f'touch input (X ⇁,Y ⇃) -> {x},{event.value}')
                return "STOP"
            else:
                show_graph = not show_graph
                return "GRAPH" # top half displays PSI graph
    return None

def make_sidebar(pipe=sidebar_pipe2,color=COLOR_NORMAL): # OBD Thread runs from get_image process
    global psi_list # deque is thread safe but gets copied before sending to main process
    car_connection, psi = None, None
    try:
        car_connection = ELM327("/dev/ttyS0") # hardware UART, TODO replace with output from gauge
        while True:
            sidebar = sidebar_base.copy() # clone base image set by temp subroutine
            try: psi = car_connection.psi() # Read data channels and calculate latest PSI reading
            except Exception as e: logger.exception(e)
            if psi is not None: # if we have new data build a sidebar and send to main process
                psi_list.append(pixels_psi(psi)) # 30px/PSI on top, /BAR below zero
                sidebar = putText(sidebar,f"{psi:.1f}",(4,57),color=color,fontScale=1.19,thickness=3)
                pipe.send(putText(sidebar, "BAR" if psi < 0.0 else "PSI", (42,95), color=COLOR_BAD))
    except Exception as e: logger.exception(e)

def get_image(pipe=backup_pipe2): # This Process will pull images from the camera
    global show_graph # The below command chain reloads CSI chip driver, seems to work better
    try: run('dtoverlay -r adv728x-m && sleep 0.019 && dtoverlay adv728x-m adv7280m=1',shell=True)
    except Exception as e: logger.exception(e)
    while True: # After successfully opening the camera, run accessory threads here to optimize
        try: #  scheduling of IO-bound operations and isolate from compute-heavy main process
            with Device.from_id(extract_index(backupCamPath)) as cam:
                Thread(target=make_sidebar, name="data", daemon=True).start()
                Thread(target=touch_thread, name="taps", daemon=True).start()
                for frame in cam: # \/ Rearrange buffer data to raw YUV422 frame
                    img = frame.array.reshape(frame.height,frame.width,2)
                    pipe.send((img, psi_list.copy()) if show_graph else img)
                    try: pipe.send(touch_queue.get(block=False)) # Send touch input
                    except Empty: pass # Fail silently if there isn't any new input 
        except Exception as e: logger.exception(e) # Log unexpected error

if __name__ == "__main__":
    fmtString = '%(asctime)s [%(levelname)-4s] %(threadName)s: %(message)s'
    logFilePath = storageRoot + "runtime-carCam.log"
    handler = RotatingFileHandler(logFilePath, maxBytes=209715200, backupCount=2)
    level = logging.INFO # DEBUG
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmtString))
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)
    try: show() # run the program's main method
    except Exception as ex: logger.exception(ex)
