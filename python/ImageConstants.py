from cv2 import CAP_PROP_BRIGHTNESS as BRIGHTNESS
from cv2 import CAP_PROP_FRAME_HEIGHT as HEIGHT
from cv2 import CAP_PROP_FRAME_WIDTH as WIDTH
from cv2 import COLOR_YUV2BGR_YUYV as YUYV
from cv2 import COLOR_BGR2BGR565 as BGR565
from cv2 import INTER_LINEAR as LINEAR
from cv2 import IMREAD_COLOR as COLOR
from cv2 import CAP_PROP_FPS as FPS
from cv2 import CAP_V4L2 as V4L2

from subprocess import run, Popen, PIPE, STDOUT
from os.path import realpath
from time import localtime
import traceback, cv2 as cv, numpy as np

DASHCAM_FPS = 15
DASHCAM_IMAGE_WIDTH = 2592
DASHCAM_IMAGE_HEIGHT = 1944
# /sys/class/graphics/fb0/modes
# /sys/class/graphics/fb0/stride
SCREEN_HEIGHT = 480
SCREEN_WIDTH = 1600
FINAL_IMAGE_WIDTH = 1480
FINAL_IMAGE_HEIGHT = SCREEN_HEIGHT
SIDEBAR_WIDTH = SCREEN_WIDTH - FINAL_IMAGE_WIDTH
SIDEBAR_HEIGHT = 160
EDGEBAR_WIDTH = 220
PSI_BUFFER_DEPTH = FINAL_IMAGE_WIDTH
PPPSI = 30      # pixels per PSI and negative Bar
DIM = (720,576) # PAL video dimensions
SDIM = (960,768)
FDIM = (1040,FINAL_IMAGE_HEIGHT)
EXPECTED_SIZE = (*DIM,30) # 25?

COLOR_REC = (0x00,0x58) # 0x00, 0xfa?
COLOR_GOOD = 0x871a
COLOR_LOW = (0xc4,0xe4)
COLOR_NEW = (0xe4,0xc4)
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
COLOR_LAYM = 0xbfe4
COLOR_OVERLAY = (199,199,190)
SHADOW = (133,38,38)
BLACK = (0,0,0)
ALPHA = 0.57

DOT = np.full((3,3,3),SHADOW,np.uint8)
DOT[:2,:2] = (0xFF,0,0) # Blue (B,G,R)
DOT = cv.cvtColor(DOT, BGR565)

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
new_K = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv.CV_32FC1)
map1, map2 = cv.convertMaps(mapx,mapy,cv.CV_16SC2) # fixed point maps run faster

usb_capture_id_path="/dev/v4l/by-id/usb-MACROSIL_AV_TO_USB2.0-video-index0"

### Example evtest touch input frame:
# Event: time 1707153627.150887, type 3 (EV_ABS), code 53 (ABS_MT_POSITION_X), value 1057
# Event: time 1707153627.150887, type 3 (EV_ABS), code 54 (ABS_MT_POSITION_Y), value 253
# Event: time 1707153627.150887, type 3 (EV_ABS), code 0 (ABS_X), value 1057
# Event: time 1707153627.150887, type 3 (EV_ABS), code 1 (ABS_Y), value 253
# Event: time 1707153627.150887, type 4 (EV_MSC), code 5 (MSC_TIMESTAMP), value 0
# Event: time 1707153627.150887, -------------- SYN_REPORT ------------
class touchEvent():
    isX = False
    isY = False
    valid = False

    def __init__(self, line):
            try:
                self._line = line
                segments = line.strip().split(", ")
                self.time = float(segments[0].lstrip("Eventim: "))
                frame = segments[1:]
                if len(frame) > 1:
                    event = self._sep_field(frame[0],"type")
                    self.event_id = int(event[0])
                    self.event = event[1]
                    code = self._sep_field(frame[1],"code")
                    self.code = code[1]
                    self.code_id = int(code[0])
                    if self.code_id == 0: self.isX = True
                    elif self.code_id == 1: self.isY = True
                    self.value = int(frame[-1].lstrip("value ").rstrip())
                    self.valid = True
                else: self.code = frame[0]
            except: self.code = f'error for line:\n{line}'

    def _sep_field(self, text, key):
        return text.lstrip(f"{key} ").rstrip(")").split(" (")

    def pretty(self):
        if self.valid:
            return f'{self.event}[{self.event_id}]: {self.code}[#{self.code_id}] -> {self.value}'
        return self._line

def putText(img, text, origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21),fontFace=cv.FONT_HERSHEY_SIMPLEX,
            fontScale=1.19,thickness=2,lineType=cv.LINE_AA):
    return cv.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

def extract_index(fully_qualified_path=usb_capture_id_path):
    usb_capture_real_path = realpath(fully_qualified_path)
    assert usb_capture_id_path != usb_capture_real_path
    return int(usb_capture_real_path.split("video")[-1])

# make boost graph here ~+15psi to ~-1.5bar
# add each point to new deque and increment position by one when reading current deque
def addOverlay(image):
    h,w = image.shape[:2]
    radius,offset = 19,38
    overlay_image = image.copy()
    overlay_image[20:461,39:1442] = COLOR_OVERLAY
    overlay_image[39:442,20:1461] = COLOR_OVERLAY
    overlay_image = cv.circle(overlay_image,(offset,offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv.circle(overlay_image,(offset,h-offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv.circle(overlay_image,(w-offset,h-offset),radius,COLOR_OVERLAY,-1)
    overlay_image = cv.circle(overlay_image,(w-offset,offset),radius,COLOR_OVERLAY,-1)
    cv.addWeighted(overlay_image,ALPHA,image,1-ALPHA,0,image)
    image[25:455,44:46] = BLACK
    image[405:407,25:1456] = BLACK
    image[135:137,38:45] = BLACK
    return putText(image,"10",(25,133),color=BLACK,fontScale=0.38,thickness=1)

def get_camera(cam_index:int,width,height,apiPreference=V4L2,brightness=25) -> cv.VideoCapture:
    camera = cv.VideoCapture(cam_index,apiPreference=apiPreference)
    camera.set(WIDTH,width)
    camera.set(HEIGHT,height)
    camera.set(BRIGHTNESS,brightness)
    assert EXPECTED_SIZE == (int(camera.get(WIDTH)),int(camera.get(HEIGHT)),int(camera.get(FPS)))
    return camera

def build_output_image(img): # MAYBE ALSO TRY mapx, mapy ?
    height, width = FINAL_IMAGE_HEIGHT, EDGEBAR_WIDTH
    intermediate = cv.remap(img,map1,map2,interpolation=LINEAR)
    image = cv.resize(intermediate,SDIM,interpolation=LINEAR)[64:556]
    large = cv.resize(image[213:453,width:-width],FDIM,interpolation=LINEAR)
    return cv.hconcat([image[8:height+8,:width], large, image[4:height+4,-width:]])

def output_alt(image_backup, image_dash):
    intermediate = cv.remap(image_backup,map1,map2,interpolation=LINEAR)
    flat = cv.resize(intermediate,(840,672),interpolation=LINEAR)[56:536]
    return cv.hconcat([flat,cv.resize(image_dash,(640,480),interpolation=LINEAR)])

def start_dash_cam(): # sets camera attributes for proper output size and format before running
    runtime = DASHCAM_FPS * 60 * 30
    camPath = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
    format = f"width={DASHCAM_IMAGE_WIDTH},height={DASHCAM_IMAGE_HEIGHT},pixelformat=MJPG"
    bash(f"v4l2-ctl -d {camPath} -v {format}")
    local_time = localtime()
    date = f"{local_time.tm_year}-{local_time.tm_mon:02d}-{local_time.tm_mday:02d}"
    clock_time = f"{local_time.tm_hour:02d}.{local_time.tm_min:02d}.{local_time.tm_sec:02d}"
    weekday = (lambda i : ['Mo','Tu','We','Th','Fr','Sa','Su'][i])(local_time.tm_wday)
    filepath = f"/media/usb/{'_'.join([date,clock_time,weekday])}.mjpeg"
    cmd = f"v4l2-ctl -d {camPath} --stream-mmap=3 --stream-count={runtime} --stream-to={filepath}"
    return shell(cmd,stderr=STDOUT,text=True)

def get_video_path(explicit_camera=None):
    local_time = localtime()
    date = f"{local_time.tm_year}-{local_time.tm_mon:02d}-{local_time.tm_mday:02d}"
    clock_time = f"{local_time.tm_hour:02d}.{local_time.tm_min:02d}.{local_time.tm_sec:02d}"
    weekday = (lambda i : ['Mo','Tu','We','Th','Fr','Sa','Su'][i])(local_time.tm_wday)
    join_list = [date,clock_time,weekday]
    if explicit_camera is not None: join_list.append(explicit_camera) # e.g. "backup", "cabin"
    return f"/media/usb/{'_'.join(join_list)}.mkv"

def bash(cmd:str,shell=True,capture_output=True,check=False):
    return run(cmd,shell=shell,capture_output=capture_output,check=check)

def shell(cmd:str,shell=True,stdout=PIPE,stderr=PIPE,**kwargs):
    return Popen(cmd,shell=shell,stdout=stdout,stderr=stderr,**kwargs)
