import cv2 as cv, numpy as np
from cv2 import CAP_PROP_BRIGHTNESS as BRIGHTNESS
from cv2 import CAP_PROP_FRAME_HEIGHT as HEIGHT
from cv2 import CAP_PROP_FRAME_WIDTH as WIDTH
from cv2 import COLOR_YUV2BGR_Y422 as YUV422
from cv2 import COLOR_BGR2BGRA as BGRA
from cv2 import INTER_LINEAR as LINEAR
from cv2 import CAP_PROP_FPS as FPS
from cv2 import FILLED as FILL
from os.path import realpath
from time import localtime

HIGH_TEMP = 55.0
FRAME_DELAY = 0.119
DASHCAM_FPS = 15
DASHCAM_IMAGE_WIDTH = 2592
DASHCAM_IMAGE_HEIGHT = 1944
SCREEN_HEIGHT = 480 # /sys/class/graphics/fb0/{modes,stride}
SCREEN_WIDTH = 1600
SCREEN_DEPTH = 4
SCREEN_SHAPE = (SCREEN_HEIGHT,SCREEN_WIDTH,SCREEN_DEPTH)
FINAL_IMAGE_WIDTH = 1480
FINAL_IMAGE_HEIGHT = SCREEN_HEIGHT
SIDEBAR_WIDTH = SCREEN_WIDTH - FINAL_IMAGE_WIDTH
SIDEBAR_HEIGHT = 160
EDGEBAR_WIDTH = 220
PSI_BUFFER_DEPTH = FINAL_IMAGE_WIDTH - 2
PPPSI = 30      # pixels per PSI and negative Bar
DIM = (720,576) # PAL video dimensions
SDIM = (960,768)
FDIM = (1040,FINAL_IMAGE_HEIGHT)
# BGR 565 bits: BBBB BGGG  GGGR RRRR
COLOR_REC = (0x00,0x58) # 0x00, 0xfa?
COLOR_GOOD = 0x871a
COLOR_LOW = (0xc4,0xe4)
COLOR_NEW = (0x20,0x9c,0xc0,0xff)
COLOR_BAD = (0x10,0x10,0x48,0xff)
COLOR_NORMAL = (0xae,0x19,0x03,0xff) # 0x19ae
COLOR_LAYM = (0xf8,0x94,0xe0,0xff) # 0xbfe4
COLOR_LAYM_INDIGO = (0x99,0x11,0x33,0xff)
COLOR_OVERLAY = (199,199,190) # (0xc7,0xc7,0xbe,0xff)
SHADOW = (0x80,0x24,0x20,0xff) # (0x30,0x21) # (133,38,38)
BLACK = (0,0,0,0xff)
BLUE = (0xff,0,0,0xff)
ALPHA = 0.57

DOT = np.full((3,3,4),SHADOW,np.uint8)
DOT[:-1,:-1] = BLUE
PADDING = cv.cvtColor(np.full((SCREEN_HEIGHT,640,SCREEN_DEPTH),COLOR_NEW,np.uint8),cv.COLOR_BGRA2BGR)
# below values are specific to my backup camera run thru my knock-off easy-cap calibrated with my
K = np.array([[309.41085232860985,              0.0, 355.4094868125207],   # phone screen. YMMV
              [0.0,              329.90981352161924, 292.2015284112677],
              [0.0,                             0.0,               1.0]])
D = np.array([[0.013301372417500422],
              [0.03857464918863361],
              [0.004117306147228716],
              [-0.008896442339724364]])
# calculate camera values to undistort image
new_K = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv.CV_32FC1)
map1, map2 = cv.convertMaps(mapx,mapy,cv.CV_16SC2) # fixed point maps run faster
# important filesystem paths
dashCamPath = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0"
backupCamPath = "/dev/v4l/by-path/platform-fe801000.csi-video-index0"
touchDevPath = "/dev/input/by-id/usb-HQEmbed_Multi-Touch-event-if00"
storageRoot = "/mnt/usb/"
# load up sidebar prototypes for normal and high temp
sidebar_hot = cv.cvtColor(cv.imread("/root/turboSB_hot.png"),BGRA)[-160:,:120]
sidebar_fine = cv.cvtColor(cv.imread("/root/turboSB.png"),BGRA)[-160:,:120]
usb5percent = cv.cvtColor(cv.imread("/root/usb05.png"),BGRA)[-120:,:120]
usb10percent = cv.cvtColor(cv.imread("/root/usb10.png"),BGRA)[-120:,:120]

def putText(img, text, origin=(0,480), #bottom left
            color=(0xc5,0x9e,0x21,0xff),fontFace=cv.FONT_HERSHEY_SIMPLEX,
            fontScale=1.19,thickness=2,lineType=cv.LINE_AA):
    return cv.putText(img,text,origin,fontFace,fontScale,color,thickness,lineType)

no_signal_frame = np.full((FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH,SCREEN_DEPTH),COLOR_BAD,np.uint8)
no_signal_frame = putText(no_signal_frame, "No Signal", (500,200))

def extract_index(fully_qualified_path=dashCamPath):
    usb_capture_real_path = realpath(fully_qualified_path)
    try: assert dashCamPath != usb_capture_real_path
    except: return dashCamPath
    return int(usb_capture_real_path.split("video")[-1])

def addOverlay(image, color=COLOR_OVERLAY):
    h,w = FINAL_IMAGE_HEIGHT,FINAL_IMAGE_WIDTH
    radius,offset = 19,38        # overlay_image[20:461,39:1442] = COLOR_OVERLAY
    overlay_image = image.copy() # overlay_image[39:442,20:1461] = COLOR_OVERLAY \/
    for top_left, bottom_right in (((39,20),(1442,461)),((20,39),(1461,442))):
        overlay_image = cv.rectangle(overlay_image,top_left,bottom_right,color,FILL)
    for center in ((offset,offset),(offset,h-offset),(w-offset,h-offset),(w-offset,offset)):
        overlay_image = cv.circle(overlay_image,center,radius,color,-1)
    cv.addWeighted(overlay_image,ALPHA,image,1-ALPHA,0,image)
    return putText(image,"10",(25,133),color=BLACK,fontScale=0.38,thickness=1)

def pixels_psi(psi): # fancy math converts value to pixel height with 30 pixels per PSI
    return max(FDIM[1] - 2 * PPPSI - 15 - int(psi*PPPSI),1)

def build_graph(graph_list, frame_buffer, depth=PSI_BUFFER_DEPTH):
    frame_buffer[25:455,44:46] = BLACK
    frame_buffer[405:407,25:1456] = BLACK # make boost graph here: ~+15 psi to ~-1 bar
    frame_buffer[135:137,38:45] = BLACK
    coordinates=np.column_stack((np.array(graph_list),np.arange(depth-len(graph_list)+1,depth+1)))
    for i in range(4): frame_buffer[coordinates[:,0]-1+i//2, coordinates[:,1]-1+i%2] = BLUE
    for i in range(1,4): frame_buffer[coordinates[:,0]+i//2, coordinates[:,1]+i%2] = SHADOW

def fullsize(img,y=48): # y=38):
    frame = np.zeros((576,720,3),np.uint8)
    frame[y:img.shape[1]+y] = img # 48:-48
    return frame

def build_output_image(img): # MAYBE ALSO TRY mapx, mapy ?
    height, width = FINAL_IMAGE_HEIGHT, EDGEBAR_WIDTH
    intermediate = cv.remap(img,map1,map2,interpolation=LINEAR)
    image = cv.resize(intermediate,SDIM,interpolation=LINEAR) # [64-y:552-y]?  y=48
    large = cv.resize(image[200:440,width:-width],FDIM,interpolation=LINEAR) # 213:453
    return cv.hconcat([image[:height,:width], large, image[:height,-width:]])

def adv(img):
    img = cv.vconcat([img[27:],img[:27]])
    return fullsize(img) if img.shape[1] < 576 else img

def output_alt(image_backup):
    intermediate = cv.remap(image_backup,map1,map2,interpolation=LINEAR)
    return cv.hconcat([cv.resize(intermediate,(840,672),interpolation=LINEAR)[56:536],PADDING])

def output_waveshare(img):
    if img.shape[1] < 576: img = fullsize(img)
    intermediate = cv.remap(img,map1,map2,interpolation=LINEAR)
    return cv.resize(intermediate,(1440,1152),interpolation=LINEAR)[100:820]

def get_video_path(explicit_camera=None): # e.g. "backup", "cabin"
    local_time = localtime()
    date = f"{local_time.tm_year}-{local_time.tm_mon:02d}-{local_time.tm_mday:02d}"
    clock_time = f"{local_time.tm_hour:02d}.{local_time.tm_min:02d}.{local_time.tm_sec:02d}"
    weekday = (lambda i : ['Mo','Tu','We','Th','Fr','Sa','Su'][i])(local_time.tm_wday)
    join_list = [date,clock_time,weekday]
    if explicit_camera is not None: join_list.append(explicit_camera)
    return storageRoot + f"{'_'.join(join_list)}.mkv"
