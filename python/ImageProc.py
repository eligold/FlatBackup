import traceback, cv2, os, numpy as np
from collections import deque
from time import sleep, perf_counter
from threading import Empty, Full, SimpleQueue
from cv2 import CAP_PROP_BRIGHTNESS as BRIGHTNESS
from cv2 import CAP_PROP_FRAME_WIDTH as WIDTH
from cv2 import COLOR_BGR2BGR565 as BGR565
from cv2 import INTER_LINEAR as LINEAR
from cv2 import CAP_PROP_FPS as FPS

DASHCAM_FPS = 15
DASHCAM_IMAGE_WIDTH = 2592
DASHCAM_IMAGE_HEIGHT = 1944
FINAL_IMAGE_WIDTH = 1480
FINAL_IMAGE_HEIGHT = 480
PSI_BUFFER_DEPTH = 740
PPPSI = 30      # pixels per PSI and negative Bar
DIM = (720,576) # PAL video dimensions
SDIM = (960,768)
FDIM = (1040,FINAL_IMAGE_HEIGHT)

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


# camera index by device mapper path
usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
usb_capture_real_path = os.path.realpath(usb_capture_id_path)
assert usb_capture_id_path != usb_capture_real_path
cameraIndex = int(usb_capture_real_path.split("video")[-1])
expected_size = (DIM[:],30)

# communications between threads:
display_queue = SimpleQueue()
signal_queue = SimpleQueue()
sidebar_queue = SimpleQueue()
psi_list = deque()
show_graph = False
exit_flag = False

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
map1, map2 = cv2.convertMaps(mapx,mapy,cv2.CV_16SC2) # fixed point maps run faster

def putText(img, text, origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,thickness=2,lineType=cv2.LINE_AA):
    return cv2.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

no_signal_frame = putText(
        np.full((FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH,2),COLOR_BAD,np.uint8),
        "No Signal",(500,200))
frame_buffer = np.memmap("/dev/fb0",dtype='uint8', shape=(480,1600,2))
sidebar_base = np.full((FINAL_IMAGE_HEIGHT,120,2),COLOR_LOW,np.uint8)
for i in range(160,FINAL_IMAGE_HEIGHT):
    for j in range(120):
        color = i*2&(i-255-j)
        high = np.uint8(color>>8)
        low = np.uint8(color)
        sidebar_base[i][j] = low, high
frame_buffer[:,-120:,:] = sidebar_base

cam_times = []
proc_times = []
display_times = []

def sidebar_hot():
    _change_sidebar(COLOR_REC)
def sidebar_cool():
    _change_sidebar(COLOR_LOW)
def _change_sidebar(color):
    global sidebar_base
    sidebar_base[:160]=np.full((),color,np.uint8)

def project_reverse_view(image):
    global frame_buffer
    global sidebar_queue
    global display_times

    start = perf_counter()

    if show_graph: addOverlay(image)
    frame_buffer[:,:-120,:] = image
    try:
        frame_buffer[:,-120:] = sidebar_queue.get(block=False)
    except Empty: pass
    frame_buffer.flush()

    display_times.append(perf_counter()-start)

def on_screen():
    global display_queue, signal_queue
    global proc_times
    while not exit_flag:
        try:

            start = perf_counter()

            image = undistort(display_queue.get(timeout=0.057))

            proc_times.append(perf_counter()-start)

            if signal_queue.empty():
                try: signal_queue.put(None)
                except Full: pass
            if exit_flag: break
            project_reverse_view(image)
        except Empty: pass

def get_image():
    global display_queue, signal_queue
    global cam_times
    signal_queue.put(None)
    width, height = DIM
    camera = None
    read_fail_count = 0
    while not exit_flag:
        try:
            camera = get_camera(cameraIndex,width,height)
            assert expected_size == (int(camera.get(WIDTH)), int(camera.get(HEIGHT)), int(camera.get(FPS)))
            camera.read()
            while camera.isOpened() and not exit_flag:
                if exit_flag: break
                try:
                    start = perf_counter()

                    signal_queue.get(timeout=0.095)
                    success, image = camera.read()
                    if success:
                        try:
                            display_queue.put(image)
                        except Full:
                            project_reverse_view(image)
                            signal_queue.put(None)

                        cam_times.append(perf_counter()-start)

                    else:
                        perf_counter()

                        read_fail_count += 1
                except Empty: pass
        finally:
            if camera: camera.release()

# make boost graph here ~+15psi to ~-1.5bar
# add each point to new deque and increment position by one when reading current deque
def addOverlay(image):
    h,w = image.shape[:2]
    radius,offset = 19,38
    overlay_image = image.copy()
    graph_list = psi_list.copy()
    overlay_image[20:461,39:1442] = COLOR_OVERLAY
    overlay_image[39:442,20:1461] = COLOR_OVERLAY
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
        except IndexError: traceback.print_exc()
    return image

def get_camera(camIndex:int,width,height,apiPreference=cv2.CAP_V4L2,brightness=25) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(BRIGHTNESS,brightness)
    return camera

def undistort(img): # MAYBE ALSO TRY mapx, mapy ?
    intermediate = cv2.remap(img,map1,map2,interpolation=LINEAR)
    image = cv2.resize(intermediate,SDIM,interpolation=LINEAR)[64:556]
    large = cv2.resize(image[213:453,220:-220],FDIM,interpolation=LINEAR)
    return cv2.cvtColor(cv2.hconcat([image[8:488,:220],large,image[:480,-220:]]),BGR565)

def make_sidebar(psi):
    sidebar = sidebar_base.copy()
    sidebar = putText(sidebar,f"{psi:.1f}",(4,57),color=COLOR_NORMAL,fontScale=1.19,
            thickness=3)
    sidebar = putText(sidebar,"BAR" if psi < 0.0 else "PSI",(60,95),color=COLOR_BAD)
    sidebar_queue.put(sidebar)