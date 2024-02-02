import os, traceback, cv2 as cv, numpy as np
from queue import Empty, Full, SimpleQueue
from time import sleep, time, localtime, perf_counter_ns as perf_counter
from threading  import Thread


DIM = (720,576) # PAL video dimensions
SDIM = (600,480) # same ratio at screen height
CDIM = (960,768)
image_queue = SimpleQueue(100)
proc_queue = SimpleQueue()
fp = np.memmap('/dev/fb0',mode='r+',dtype='uint8',shape=(1600,480,2))

finished_flag = False
capture_flag = False
calibrated_flag = False

mapx, mapy = None
mapxf, mapyf = None

def calibrate():
    global image_queue
    global calibrated_flag
    global fp, mapx, mapy, mapxf, mapyf
    CHECKERBOARD = (14,9)
    criteria = cv.TERM_CRITERIA_EPS+cv.TERM_CRITERIA_MAX_ITER
    terms = (criteria, 30, 1e-6)                                                         # skew (alpha) stays zero \/
    calibration_flags = cv.fisheye.CALIB_RECOMPUTE_EXTRINSIC+cv.fisheye.CALIB_CHECK_COND # +cv.fisheye.CALIB_FIX_SKEW
    objp = np.zeros((1,CHECKERBOARD[0]*CHECKERBOARD[1], 3), np.float32)
    objp[0,:,:2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
    objpoints = []
    imgpoints = []
    frames = []
    while not finished_flag:
        try:
            image = image_queue.get(block=False)
            found, corners = cv.findChessboardCornersSB(image, CHECKERBOARD, None, 
                    cv.CALIB_CB_NORMALIZE_IMAGE+cv.CALIB_CB_EXHAUSTIVE+cv.CALIB_CB_ACCURACY)
            if found:
                objpoints.append(objp)
                imgpoints.append(corners)
                frames.append(image)
                disp = cv.resize(cv.drawChessboardCorners(image,CHECKERBOARD,corners,found),SDIM)
                fp[:,400:1000] = disp
        except Empty: pass
    N_OK = len(objpoints)
    K = np.zeros((3,3))
    D = np.zeros((4,1))
    rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
    tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
    rms, K, D, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, DIM, K, D, rvecs, tvecs,
                                                 cv.CALIB_RATIONAL_MODEL,terms)
    print(f"Average error: {rms:.5f}")
    print(f"Found {N_OK} valid images for calibration")
    print(f"DIM = {image.shape[:2][::-1]}")
    print(f"K = np.array({K.tolist()})")
    print(f"D = np.array({D.tolist()})")
    new_K, roi = cv.getOptimalNewCameraMatrix(K,D,DIM,1,CDIM)
    cv.imwrite("rational.model.png",cv.undistort(image,K,D,None,new_K))
    mapx, mapy = cv.initUndistortRectifyMap(K,D,None,new_K,CDIM,cv.CV_32FC1)
    print(f"ROI: {roi}")

    KF = np.zeros((3,3)) # fisheye submodule
    DF = np.zeros((4,1))
    rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
    tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_OK)]
    rms, KF, DF, rvecs, tvecs = cv.fisheye.calibrate(objpoints, imgpoints, DIM, KF, DF, rvecs,
                                                     tvecs, calibration_flags, terms)
    print(f"Fisheye submodule:\nAverage error: {rms:.5f}")
    print(f"Found {N_OK} valid images for fisheye calibration")
    print(f"DIM = {image.shape[:2][::-1]}")
    print(f"K = np.array({KF.tolist()})")
    print(f"D = np.array({DF.tolist()})")
    sK = KF*720/600
    sK[2][2] = 1.0                                                 # DIM HERE?
    new_Kf = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(sK,D,SDIM,np.eye(3),balance=1)
    mapxf, mapyf = cv.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_Kf, SDIM, cv.CV_32FC1)
    calibrated_flag = True

def get_image():
    global image_queue
    global finished_flag, capture_flag
    global fp
    cap = None
    try:
        cap = cv.VideoCapture(0,apiPreference=cv.CAP_V4L)
        cap.set(cv.CAP_PROP_FRAME_WIDTH,720)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT,576)
        cap.set(cv.CAP_PROP_BRIGHTNESS,25)
        h = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        w = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        print(f"camera output size: {w} x {h}")
        counter = 0
        while cap.isOpened():
            success, frame = cap.read()
            if success:
    # processing code
                if capture_flag:
                    if counter > 4: capture_flag = False
                    else: counter += 1
                    try:
                        image_queue.put(frame)
                    except Full: finished_flag = True
    # display code (normals use cv.imwrite(frame) followed by cv.waitKey(0))
                if calibrated_flag:
                    fp[:,-960:] = undistort(frame)[8:488]
                else:
                    fp[:,-600:] = cv.resize(frame,SDIM,iterpolation=cv.INTER_LINEAR)
                # fb.flush()       # doesn't appear to be necessary
            else: pass
    finally:
        if cap: cap.release()

def undistort(image):
   # return cv.remap(image,mapx,mapy,interpolation=cv.INTER_CUBIC)
    return cv.remap(image,mapxf,mapyf,interpolation=cv.INTER_CUBIC)

def start():
    global capture_flag
    Thread(target=get_image,name="show",daemon=True).start()
    Thread(target=calibrate,name="process",daemon=True)
    while True:
        if input() == '':
            capture_flag = True


if __name__ == "__main__":
    start()