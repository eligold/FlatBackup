#!/usr/bin/env python3
from time import sleep
import time, cv2, numpy as np

def run():
    try:
        c = cv2.VideoCapture(0, apiPreference=cv2.CAP_V4L2)
        c.set(cv2.CAP_PROP_FRAME_WIDTH,720)
        c.set(cv2.CAP_PROP_FRAME_HEIGHT,576)
        CHECKERBOARD = (14,9)
        criteria = cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER
        calibration_flags = cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC+cv2.fisheye.CALIB_CHECK_COND+cv2.fisheye.CALIB_FIX_SKEW
        objp = np.zeros((1,CHECKERBOARD[0]*CHECKERBOARD[1], 3), np.float32)
        objp[0,:,:2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
        objpoints = []
        imgpoints = []
        count = False
        frames = []
        DIM = (720,576)
        sDIM = (600,480)
        while(c.isOpened()):
            r,img = c.read()
            if r:
                found, corners = cv2.findChessboardCornersSB(img, CHECKERBOARD, None, 
                        cv2.CALIB_CB_NORMALIZE_IMAGE+cv2.CALIB_CB_EXHAUSTIVE+cv2.CALIB_CB_ACCURACY)
                onScreen(cv2.resize(cv2.drawChessboardCorners(img, CHECKERBOARD, corners, found),sDIM))
                if found: # keyboard input?
                    if count:
                        objpoints.append(objp)
                        imgpoints.append(corners)
                        frames.append(img)
                        if len(frames) > 14:
                            break
                        else:
                            print(f"found {len(frames)}!")
                        count = False
                    else:
                        count = True
            else:
                count = False
        N_OK = len(objpoints)
        K = np.zeros((3, 3))
        D = np.zeros((4, 1))
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(objpoints, imgpoints, DIM, K, D, rvecs, tvecs, calibration_flags, (criteria, 30, 1e-6))
        print(f"Average error: {rms:.5f}")
        print(f"Found {N_OK} valid images for calibration")
        print(f"DIM = {img.shape[:2][::-1]}")
        print(f"K = np.array({K.tolist()})")
        print(f"D = np.array({D.tolist()})")
        sK = K*5/6
        sK[2][2] = 1.0
        new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(sK,D,sDIM,np.eye(3),balance=1)
        map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, sDIM, cv2.CV_32FC1)
        while(c.isOpened()):
            r,img = c.read()
            if r:
                uimg = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                onScreen2(cv2.resize(img,sDIM),uimg)
    finally:
        c.release()

def onScreen(f):
    f = cv2.cvtColor(f,cv2.COLOR_BGR2BGR565)
    with open('/dev/fb0','rb+') as buf:
        for i in range(480):
            buf.write(f[i])
            buf.write(np.full(1600-f.shape[1],0x19ae,np.uint16))

def onScreen2(f,f2):
    f = cv2.cvtColor(f,cv2.COLOR_BGR2BGR565)
    f2 = cv2.cvtColor(f2,cv2.COLOR_BGR2BGR565)
    with open('/dev/fb0','rb+') as buf:
        for i in range(480):
            buf.write(f[i])
            buf.write(f2[i])
            buf.write(np.full(1600-f.shape[1]-f2.shape[1],0x19ae,np.uint16))

if __name__ == "__main__":
    run()
