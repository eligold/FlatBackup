#!/usr/bin/env python3
import code, cv2, numpy as np

def run():
    try:
        c = cv2.VideoCapture(0, apiPreference=cv2.CAP_V4L2)
        c.set(cv2.CAP_PROP_FRAME_WIDTH,720)
        c.set(cv2.CAP_PROP_FRAME_HEIGHT,576)
    # CHECKERBOARD = (8,6)
        CHESSBOARD = (14,9)
        criteria = cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER
    # subpix_criteria = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    # cal_criteria = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6)
        fisheye_calib_flags = cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC \
                        + cv2.fisheye.CALIB_CHECK_COND \
                        + cv2.CALIB_FIX_PRINCIPAL_POINT #\
                        #+ cv2.CALIB_FIX_FOCAL_LENGTH # +cv2.fisheye.CALIB_FIX_SKEW
        calib_flags = cv2.CALIB_FIX_PRINCIPAL_POINT # \
                   # + cv2.CALIB_THIN_PRISM_MODEL
       #             + cv2.CALIB_FIX_FOCAL_LENGTH \
       #             + cv2.CALIB_RATIONAL_MODEL 
        # objp = np.zeros((1,CHECKERBOARD[0]*CHECKERBOARD[1], 3), np.float32)
        # objp[0,:,:2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
        objp = np.zeros((1,CHESSBOARD[0]*CHESSBOARD[1], 3), np.float32)
        objp[0,:,:2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2)
        objpoints = []
        imgpoints = []
        count = False
        frames = []
        while(c.isOpened()):
            r, img = c.read()
        # gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        # found, corners = cv2.findChessboardCorners(gray, CHECKERBOARD,# None)
        #         cv2.CALIB_CB_ADAPTIVE_THRESH+cv2.CALIB_CB_FAST_CHECK+cv2.CALIB_CB_NORMALIZE_IMAGE+cv2.CALIB_CB_FILTER_QUADS)
            if r:
                foundSB, cornersSB = cv2.findChessboardCornersSB(img, CHESSBOARD, None, cv2.CALIB_CB_NORMALIZE_IMAGE+cv2.CALIB_CB_EXHAUSTIVE+cv2.CALIB_CB_ACCURACY)
                onScreen(cv2.drawChessboardCorners(img, CHESSBOARD, cornersSB, foundSB))#CHECKERBOARD, corners, found))
                if foundSB: # keyboard input?
                    if count:
                        objpoints.append(objp)
                        imgpoints.append(cornersSB) # corners2)
                        frames.append(img)
                        if len(frames) > 9: # 14:
                            break
                        else:
                            print(f"found {len(frames)}!")
                        count = False
                    else:
                        count = True
                else:
                    count = False
        DIM = (720,576)
        N_OK = len(objpoints)
        K=np.array([
                [313.30178138822794,                0.0, 356.02518253081223],
                [               0.0, 333.51402262357607, 290.35990191065844],
                [               0.0,                0.0,                1.0]])
        D=np.array([
                [0.0468345760181369],
                [-0.0018991832207017748],
                [0.009947859275560718],
                [-6.907251074975234e-05]])
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
        sK = K*5/6
        sK[2][2] = 1.0
    # rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(objpoints, imgpoints, DIM, K, D, rvecs, tvecs, calibration_flags, (criteria, 30, 1e-6))
        rms, K_SB, D_SB, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, DIM, None, None, rvecs, tvecs, calib_flags, (criteria, 30, 1e-6))
        print(f"Average error: {rms:.5f}")
        print(f"Found {N_OK} valid images for calibration")
        print(f"DIM = {img.shape[:2][::-1]}")
        print(f"K = np.array({K_SB.tolist()})")
        print(f"D = np.array({D_SB.tolist()})\n")
        print(f"rvecs: {rvecs}")
        print(f"tvecs: {tvecs}")
        
        sK = K_SB*5/6
        sK[2][2] = 1.0
        sDIM = (600,480)
        scale,map1SB,map2SB = cv2.initWideAngleProjMap(K_SB,D_SB,DIM,1080,cv2.CV_32FC2,projType=cv2.PROJ_SPHERICAL_ORTHO,alpha=1)
        code.interact(locals=locals())
        while(c.isOpened()):
            r,img = c.read()
            if r:
                simg = cv2.remap(img, map1SB, map2SB, interpolation=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
                onScreen(simg)
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
            size = 1600 - f.shape[1]
            if i < f2.shape[0]:
                buf.write(f2[i])
                size = size-f2.shape[1]
            buf.write(np.full(size,0x19ae,np.uint16))

if __name__ == "__main__":
    run()
