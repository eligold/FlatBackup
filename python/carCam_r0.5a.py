#!/usr/bin/env python3
import os, traceback, cv2, numpy as np #, asyncio, aiofiles
from subprocess import run, Popen, PIPE
from threading  import Thread
from queue import Queue, Empty
from collections import deque
from time import sleep
from obd import Unit
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
intemp = onboardTemp()
show_graph = False
psi_list = deque()
queue = Queue()

res = 50
ofs = (3,5)
pos = (95,190)
sidebar_base = np.full((480,120),COLOR_LOW,np.uint16)
sidebar_base = cv2.circle(sidebar_base,pos,9,(0xffff),2)
sidebar_base = cv2.circle(sidebar_base,pos,8,(0),2)
sidebar_base = cv2.rectangle(sidebar_base,(pos[0]-ofs[0]-2,pos[1]-ofs[1]-res-2),(pos[0]+ofs[0]+2,pos[1]-ofs[1]),(0xffff),1)
sidebar_base = cv2.rectangle(sidebar_base,(pos[0]-ofs[0],pos[1]-ofs[1]-res),(pos[0]+ofs[0],pos[1]-ofs[1]),(0),1)
sidebar_base = cv2.rectangle(sidebar_base,(pos[0]-ofs[0],pos[1]-ofs[1]-res),(pos[0]+ofs[0],pos[1]-ofs[1]),(0x630c),-1)

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def add_pressure(pressure,deque):
    entry = int(pressure*PPPSI)
    while(len(deque)>=PSI_BUFFER_DEPTH-1):
        deque.pop()
    deque.appendleft(entry)
    return pressure

def begin(): # /dev/disk/by-id/ata-APPLE_SSD_TS128C_71DA5112K6IK-part1
    # dashcam_id_path = \
    #     "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    # dashcam = getCamera(int(os.path.realpath(dashcam_id_path).split("video")[-1]))
    global show_graph
    elm = ELM327()
    camera = None
    usb_capture_id_path = "/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
    index = int(os.path.realpath(usb_capture_id_path).split("video")[-1])
    try:
        camera = getCamera(index)
        cmd = Popen('evtest /dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00',
                    shell=True,stdout=PIPE,stderr=PIPE)
        t = Thread(target=enqueue_output, args=(cmd.stdout, queue))
        t.daemon = True
        t.start()
        res=run('cat /sys/class/net/wlan0/operstate',shell=True,capture_output=True)
        volts = elm.volts()
        if res.stdout == b'up\n' and volts < 12.1:
            #close(elm,camera)
            pass#exit(0)
        if volts > 12.1:
            run('ip link set wlan0 down',shell=True)
        success, img = getUndist(camera)
        with open('/dev/fb0','rb+') as buf:
            while camera.isOpened():
                while(True):
                    try:  
                        line = queue.get_nowait()
                        if(b'POSITION_X' in line and b'value' in line):
                            if int(line.decode().split('value')[-1]) > IMAGE_WIDTH:
                                line = queue.get_nowait()
                                if int(line.decode().split('value')[-1]) < 240:
                                    show_graph = not show_graph
                                else:
                                    bounce(elm,camera)
                    except Empty:
                        break
                success, img = getUndist(camera)
                sidebar = buildSidebar(elm)
                if success:
                    if show_graph:
                        onScreen(buf,combinePerspective(img),sidebar)
                    else:
                        middle = cv2.resize(
                                    img[213:453,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4)
                        img = cv2.cvtColor(img,CVT3TO2B)
                        onScreen(buf,cv2.cvtColor(middle,CVT3TO2B),sidebar,
                                 img[8:488,:220],img[:480,-220:])
                else:
                    errScreen(buf)
        sleep(0.19)
    except KeyboardInterrupt:
        bounce(elm,camera)
    except:
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
    frame_buffer.seek(0)

def getCamera(camIndex:int,apiPreference=cv2.CAP_V4L2) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,720)
    camera.set(HEIGHT,576)
    camera.set(BRIGHTNESS,25)
    return camera

def getUndist(camera): # -> [bool, cv2.UMat or None]:
    success, image = camera.read()
    if success:
        undist = cv2.remap(image,mapx,mapy,interpolation=cv2.INTER_LANCZOS4)
        image = cv2.resize(undist,SDIM,interpolation=cv2.INTER_LANCZOS4)[64:556]
    return success, image

def putText(img, text="you forgot the text idiot", origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,
            thickness=2,
            lineType=cv2.LINE_AA
        ):
    return cv2.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

def newOnScreen(frame_buffer,image,pos=(0,0)):
    h,w,d = image.shape
    if pos < (0,0) or d != 2:
        raise Exception(f"negative position!\n{pos}")
    if w + pos[0] > 1600:       # trim too wide
        image = image[:,:1600-pos[0]]
        h,w,d = image.shape
    if pos[1] > 0:              # vertical offset
        frame_buffer.seek(pos[1]*2*1600)
    for i in range(h):
        if pos[0] > 0:          # horizontal offset
            frame_buffer.seek(pos[0]*2,1)
        frame_buffer.write(image[i])
        if w + pos[0] < 1600:   # if not full width seek end of line
            frame_buffer.seek((1600-w-pos[0])*2,1)
    frame_buffer.seek(0)

def onScreen(frame_buffer,image,sidebar,left=None,right=None):
    for i in range(480):
        if left is not None and right is not None:
            frame_buffer.write(left[i])
            frame_buffer.write(image[i])
            frame_buffer.write(right[i])
        else:
            frame_buffer.write(image[i])
        if i > 320:
            for j in range(120):
                frame_buffer.write(np.uint16(i*2&(i-255-j)))
        else:
            frame_buffer.write(sidebar[i])
    frame_buffer.seek(0)

def combinePerspective(image,inlay=None):
    middle = cv2.resize(image[213:453,220:740],FDIM,interpolation=cv2.INTER_LANCZOS4) \
        if inlay is None else inlay
    combo = cv2.hconcat([image[8:488,:220],middle,image[:480,-220:]])
    if show_graph:
        combo = addOverlay(combo)
    final_image = cv2.cvtColor(combo,CVT3TO2B)
    return final_image

# make boost graph here ~+15psi to ~-1.5bar
# add each point to new deque and increment position by one when reading current deque
def addOverlay(image):
    h,w = image.shape[:2]
    radius,offset = 19,38
    overlay_image = image.copy()
    graph_list = psi_list.copy()
    overlay_image[20:461,39:1442] = COLOR_OVERLAY
    # overlay_image = cv2.rectangle(overlay_image,(offset,offset-radius),(w-offset,h-(offset-radius)),COLOR_OVERLAY,-1)
    overlay_image[39:442,20:1461] = COLOR_OVERLAY
    # overlay_image = cv2.rectangle(overlay_image,(offset-radius,offset),(w-(offset-radius),h-offset),COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(offset,offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(offset,h-offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(w-offset,h-offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv2.circle(overlay_image,(w-offset,offset),radius,COLOR_OVERLAY,-1)
    cv2.addWeighted(overlay_image,ALPHA,image,1-ALPHA,0,image)
    image[25:455,44:46] = BLACK
    image[405:407,25:1456] = BLACK
    image[135:137,38:45] = BLACK
    image = putText(image,"10",(25,133),color=BLACK,fontScale=0.38,thickness=1)
    for x in range(PSI_BUFFER_DEPTH-len(psi_list),PSI_BUFFER_DEPTH):
        try:
            x = x * 2
            y = FDIM[1] - 2 * PPPSI - 15 - graph_list.pop()
            image[y:y+2,x:x+2] = DOT
            image[y+2,x:x+3] = SHADOW
            image[y:y+3,x+2] = SHADOW
        except IndexError:
            pass
    return image

def buildSidebar(elm):
    sidebar = sidebar_base.copy()
    sidebar = putText(sidebar,f"{elm.volts()}V",(19,133),
                    color=COLOR_NORMAL,thickness=1,fontScale=0.5)
    psi = add_pressure(elm.psi(),psi_list)
    sidebar = putText(sidebar,f"{psi:.1f}",(4,57),color=COLOR_NORMAL,fontScale=1.19,thickness=3)
    sidebar = putText(sidebar,"BAR" if psi < 0.0 else "PSI",(60,95),color=COLOR_BAD)
    temp = int(intemp.temperature/2)#*res/100)
    color = 0xf800 # red
    if temp < 20:
        color = 0xc55e # light blue
    # elif temp < 40:
    #    color = COLOR_LAYM # 'frog' green ;)
    elif temp < 60:
        color = 0xc5ca # yellow
    # sidebar = cv2.circle(sidebar,pos,8,(color),-1)
    # sidebar = cv2.rectangle(sidebar,(pos[0]-ofs[0],pos[1]-ofs[1]-temp),
    #                                 (pos[0]+ofs[0],pos[1]),(color),-1)
    sidebar[185-temp:191,90:101] = color
    sidebar[88:104,188:194] = color
    sidebar[89:103,186:196] = color
    sidebar[90:102,185:197] = color
    sidebar[91:101,184:198] = color
    sidebar[93:99,183:199] = color
    return sidebar

def bounce(elm,camera,ec=0,wifi=True):
    elm.close()
    camera.release()
    if wifi:
        run(['bash','-c','ip link set wlan0 up'])
    exit(ec)

if __name__ == "__main__":
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
