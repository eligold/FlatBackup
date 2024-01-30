#!/usr/bin/env python3
import numpy as np, cv2 as cv, code
#K=np.array([
#    [313.30178138822794,                0.0, 356.02518253081223],
#    [               0.0, 333.51402262357607, 290.35990191065844],
#    [               0.0,                0.0,                1.0]])
#D=np.array([
#    [0.0468345760181369],
#    [-0.0018991832207017748],
#    [0.009947859275560718],
#    [-6.907251074975234e-05]])
# c = cv.VideoCapture(0,apiPreference = cv.CAP_V4L2)
# c.release()

DIM = (720, 576)
SDIM = (600,480)
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
new_K = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv.CV_32FC1)
new_sK = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, SDIM, np.eye(3), balance=1)
mapx2, mapy2 = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_sK, SDIM, cv.CV_32FC1)
def get_camera():
    c = cv.VideoCapture(0,apiPreference = cv.CAP_V4L2)
    c.set(cv.CAP_PROP_FRAME_WIDTH,720)
    c.set(cv.CAP_PROP_FRAME_HEIGHT,576)
    c.set(cv.CAP_PROP_BRIGHTNESS,25)
    print(f"height of the image: {c.get(cv.CAP_PROP_FRAME_HEIGHT)}px")
    return c

def onScreen(f):
    if not f.shape[2] == 2:
        f = cv.cvtColor(f,cv.COLOR_BGR2BGR565)
    with open('/dev/fb0','rb+') as buf:
        for i in range(480):
            buf.write(f[i])
            buf.write(np.full(1600-f.shape[1],0x19ae,np.uint16))

def make_view(f):
    f = cv.resize(
        cv.remap(f, mapx, mapy, interpolation=cv.INTER_CUBIC),
        (960,768),interpolation=cv.INTER_CUBIC)
    f2 = cv.cvtColor(f,cv.COLOR_BGR2BGR565)
    f1 = f2[76:556,:160]
    f2 = f2[68:548,-160:]
    f = cv.cvtColor(
        cv.resize(f[284:524,160:800],(1280,480),interpolation=cv.INTER_CUBIC),
        cv.COLOR_BGR2BGR565)
    return cv.hconcat([f1,f,f2])

def saveImage(f):
    o = f.copy()
    f = cv.remap(f, mapx, mapy, interpolation=cv.INTER_CUBIC)
    final = cv.hconcat([o,f])
    cv.imwrite("sidebyside.png",final)
    fb = np.memmap("/dev/fb0",dtype="uint8",shape=(480,1600,2))
    fb[:,:,:] = make_view(f)
    code.interact(local=dict(globals(), **locals()))

def run(t = (600,480)):
    try:
        c = get_camera()
        for _ in range(100):
            c.read()
        saveImage(c.read()[1])
        #while(c.isOpened()): onScreen(cv.resize(c.read()[1],t))
    finally:
        c.release()

if __name__ == "__main__":
    run()
    code.interact(local=globals())
