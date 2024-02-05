import traceback, cv2, os
from queue import Empty, Full, SimpleQueue
from collections import deque
from time import perf_counter
from ImageConstants import *

DOT = np.full((3,3,3),SHADOW,np.uint8)
DOT[:2,:2] = (0xFF,0,0)
# camera index by device mapper path
usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"
usb_capture_real_path = os.path.realpath(usb_capture_id_path)
assert usb_capture_id_path != usb_capture_real_path
cameraIndex = int(usb_capture_real_path.split("video")[-1])

# communications between threads:
display_queue = SimpleQueue()
signal_queue = SimpleQueue()
sidebar_queue = SimpleQueue()
psi_list = deque(maxlen=PSI_BUFFER_DEPTH)
show_graph = False
exit_flag = False

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
frame_buffer = np.memmap("/dev/fb0",dtype='uint8',shape=(SCREEN_HEIGHT,SCREEN_WIDTH,2))
sidebar_base = np.full((FINAL_IMAGE_HEIGHT,SCREEN_WIDTH-FINAL_IMAGE_WIDTH,2),COLOR_LOW,np.uint8)
for i in range(160,FINAL_IMAGE_HEIGHT):
    for j in range(120):
        color = i*2&(i-255-j)
       # high = np.uint8(color>>8)
       # low = np.uint8(color)
       # sidebar_base[i][j] = low, high
        sidebar_base[i][j] = np.uint16(color)

frame_buffer[:,-SIDEBAR_WIDTH:] = sidebar_base
frame_buffer[:,:-SIDEBAR_WIDTH] = \
    putText(frame_buffer[:,:-120],"Initializing",(500,250),fontScale=3,thickness=4)

############## DEBUG #############
display_times = deque(maxlen=1000)
proc_times = deque(maxlen=1000)
cam_times = deque(maxlen=1000)

def sidebar_hot():
    _change_sidebar(COLOR_REC)
def sidebar_cool():
    _change_sidebar(COLOR_LOW)
def _change_sidebar(color):
    global sidebar_base
    sidebar_base[:160]=np.full((),color,np.uint8)

def make_sidebar(psi):
    global psi_list
    entry = int(psi*PPPSI)
    psi_list.append(entry)

    sidebar = sidebar_base.copy()
    sidebar = putText(sidebar,f"{psi:.1f}",(4,57),color=COLOR_NORMAL,fontScale=1.19,
            thickness=3)
    sidebar = putText(sidebar,"BAR" if psi < 0.0 else "PSI",(60,95),color=COLOR_BAD)
    sidebar_queue.put(sidebar)

def display_image(image):
    global frame_buffer
    global sidebar_queue
    global display_times

    start = perf_counter()

    frame_buffer[:,:-SIDEBAR_WIDTH] = image
    try: frame_buffer[:,-SIDEBAR_WIDTH:] = sidebar_queue.get(block=False)
    except Empty: pass
    frame_buffer.flush()
    try: signal_queue.put(None)
    except Full: pass

    display_times.append(perf_counter()-start)

def on_screen():
    global display_queue, signal_queue
    global frame_buffer
    global proc_times
    frame_buffer[:,:-SIDEBAR_WIDTH] = \
        putText(frame_buffer[:,:-SIDEBAR_WIDTH],"Initializing..",(500,250),fontScale=3,thickness=4)
    while not exit_flag:

        start = perf_counter()
        try:
            image = build_output_image(display_queue.get(timeout=0.057))
            if show_graph: addOverlay(image)
            image = cv2.cvtColor(image, BGR565)

            proc_times.append(perf_counter()-start)

            if exit_flag: break

        except Empty:perf_counter()# pass

        else: display_image(image)

    print("leaving onscreen")

def get_image():
    global display_queue, signal_queue
    global cam_times
    global logger
    signal_queue.put(None)
    width, height = DIM
    camera = None
    read_fail_count = 0
    frame_buffer[:,:-SIDEBAR_WIDTH] = \
        putText(frame_buffer[:,:-SIDEBAR_WIDTH],"Initializing.",(500,250),fontScale=3,thickness=4)
    while not exit_flag:
        try:
            camera = get_camera(cameraIndex,width,height)
            camera.read()
            while camera.isOpened() and not exit_flag:

                start = perf_counter()

                try: signal_queue.get(timeout=0.095)

                except Empty: perf_counter() # pass

                else:
                    success, image = camera.read()
                    if success:
                        try: display_queue.put(image)
                        except Full: display_image(image)

                        cam_times.append(perf_counter()-start)
                    else: # read_fail_count += 1
                        perf_counter()
                        read_fail_count += 1
        except Exception as e:
            traceback.print_exc()
            logger.exception(e)
        finally:
            if camera: camera.release()

    print("leaving get_image")

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
    for x in range(PSI_BUFFER_DEPTH-len(graph_list),PSI_BUFFER_DEPTH):
        try:
            y = FDIM[1] - 2 * PPPSI - 15 - graph_list.popleft()
            image[y:y+3,x-3:x] = DOT
        except IndexError: traceback.print_exc()
    return image

def get_camera(camIndex:int,width,height,apiPreference=cv2.CAP_V4L2,brightness=25) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(BRIGHTNESS,brightness)
    assert EXPECTED_SIZE == (int(camera.get(WIDTH)),int(camera.get(HEIGHT)),int(camera.get(FPS)))
    return camera

def build_output_image(img): # MAYBE ALSO TRY mapx, mapy ?
    intermediate = cv2.remap(img,map1,map2,interpolation=LINEAR)
    image = cv2.resize(intermediate,SDIM,interpolation=LINEAR)[66:558]
    large = cv2.resize(image[213:453,EDGEBAR_WIDTH:-EDGEBAR_WIDTH],FDIM,interpolation=LINEAR)
    return cv2.hconcat([
            image[6:FINAL_IMAGE_HEIGHT+6,:EDGEBAR_WIDTH],
            large,
            image[:FINAL_IMAGE_HEIGHT,-EDGEBAR_WIDTH:]])