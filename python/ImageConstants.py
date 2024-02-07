from cv2 import CAP_PROP_BRIGHTNESS as BRIGHTNESS
from cv2 import CAP_PROP_FRAME_HEIGHT as HEIGHT
from cv2 import CAP_PROP_FRAME_WIDTH as WIDTH
from cv2 import COLOR_BGR2BGR565 as BGR565
from cv2 import INTER_LINEAR as LINEAR
from cv2 import CAP_PROP_FPS as FPS
import numpy as np

DASHCAM_FPS = 15
DASHCAM_IMAGE_WIDTH = 2592
DASHCAM_IMAGE_HEIGHT = 1944
SCREEN_HEIGHT = 480
SCREEN_WIDTH = 1600
FINAL_IMAGE_WIDTH = 1480
FINAL_IMAGE_HEIGHT = SCREEN_HEIGHT
SIDEBAR_WIDTH = SCREEN_WIDTH - FINAL_IMAGE_WIDTH
EDGEBAR_WIDTH = 220
PSI_BUFFER_DEPTH = FINAL_IMAGE_WIDTH
PPPSI = 30      # pixels per PSI and negative Bar
DIM = (720,576) # PAL video dimensions
SDIM = (960,768)
FDIM = (1040,FINAL_IMAGE_HEIGHT)
EXPECTED_SIZE = (*DIM,30)

COLOR_REC = 0xfa00 # 0x58
COLOR_GOOD = 0x871a
COLOR_LOW = 0xc4e4
COLOR_BAD = 0x8248
COLOR_NORMAL = 0x19ae
COLOR_LAYM = 0xbfe4
COLOR_OVERLAY = (199,199,190)
SHADOW = (133,38,38)
BLACK = (0,0,0)
ALPHA = 0.57

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
