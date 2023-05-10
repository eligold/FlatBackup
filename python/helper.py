#!/usr/bin/env python3
import numpy as np, cv2 as cv, code
#for obd to import properly on mac:
import collections
collections.MutableMapping = collections.abc.MutableMapping
collections.Mapping = collections.abc.Mapping
# end mac obd import req
import obd

DIM = (600,480)
K=np.array([
    [313.30178138822794,                0.0, 356.02518253081223],
    [               0.0, 333.51402262357607, 290.35990191065844],
    [               0.0,                0.0,                1.0]])
D=np.array([
    [0.0468345760181369],
    [-0.0018991832207017748],
    [0.009947859275560718],
    [-6.907251074975234e-05]])
# c = cv.VideoCapture(0,apiPreference = cv.CAP_V4L2)
# c.release()
sK = K * 5.0 / 6.0
sK[2][2] = 1.0
scaled_K = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(sK, D, DIM, np.eye(3), balance=1)
mapSx, mapSy = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), scaled_K, DIM, cv.CV_16SC2)
new_K = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, (720,576), np.eye(3), balance=1)
mapx, mapy = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM, cv.CV_16SC2)

def init():
    c = cv.VideoCapture(0,apiPreference = cv.CAP_V4L2)
    c.set(cv.CAP_PROP_FRAME_WIDTH,720)
    c.set(cv.CAP_PROP_FRAME_HEIGHT,576)
    print(f"height of the image: {c.get(cv.CAP_PROP_FRAME_HEIGHT)}px")
    return c

def onScreen(f):
    if not f.shape[2] == 2:
        f = cv.cvtColor(f,cv.COLOR_BGR2BGR565)
    with open('/dev/fb0','rb+') as buf:
        for i in range(480):
            buf.write(f[i])
            buf.write(np.full(1600-f.shape[1],0x19ae,np.uint16))

def onScreen2(f):
    f = cv.remap(f, mapSx, mapSy, interpolation=cv.INTER_LINEAR)
    f2 = cv.remap(f, mapx, mapy, interpolation=cv.INTER_LINEAR)
    f2 = cv.cvtColor(cv.resize(f,(600,480)),cv.COLOR_BGR2BGR565)
    f = cv.cvtColor(f,cv.COLOR_BGR2BGR565)
    with open('/dev/fb0','rb+') as buf:
        for i in range(480):
            buf.write(f[i])
            buf.write(f2[i])
            buf.write(np.full(1600-f.shape[1]-f2.shape[1],0x19ae,np.uint16))

def runDual():
    try:
        c = init()
        c.read()
        while(c.isOpened()): onScreen2(c.read()[1])
    finally:
        c.release()

def run(t = (600,480)):
    try:
        c = init()
        c.read()
        while(c.isOpened()): onScreen(cv.resize(c.read()[1],t))
    finally:
        c.release()

if __name__ == "__main__":
    code.interact(local=globals())
