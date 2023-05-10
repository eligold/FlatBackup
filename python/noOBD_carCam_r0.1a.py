#!/usr/bin/env python3
import time, traceback, subprocess, cv2, numpy as np

DIM=(720, 576)
sDIM=(1200,960) # video upscale dimensions
COLOR_BAD=0x8248
COLOR_NORMAL=0x19ae
CVT3TO2B = cv2.COLOR_BGR2BGR565    # convenience defs \/ \/
WIDTH = cv2.CAP_PROP_FRAME_WIDTH   #
HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT #  /\ /\ /\ /\ /\ /\ /\
K = np.array([[309.41085232860985, 0.0, 355.4094868125207], [0.0, 329.90981352161924, 292.2015284112677], [0.0, 0.0, 1.0]])
D = np.array([[0.013301372417500422], [0.03857464918863361], [0.004117306147228716], [-0.008896442339724364]])
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(K, D, DIM, np.eye(3), balance=1)
mapx, mapy = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), new_K, DIM,cv2.CV_32FC1)

def run(camIndex=0,apiPreference=cv2.CAP_V4L2):
    psi = 19
    ec = 0
    times = []
    while(True):
        try:
            camera = cv2.VideoCapture(camIndex,apiPreference=apiPreference)
            camera.set(WIDTH,720)
            camera.set(HEIGHT,576)
            color = COLOR_NORMAL
            lt = time.time()
            success, img = getUndist(camera)
            with open('/dev/fb0','rb+') as buf:
                while camera.isOpened():
                    try:
                        onScreen(buf,img,color,f"{psi:.1f} PSI")
                        success, img = getUndist(camera)
                        tn = time.time()
                        if success:
                            times.append(tn - lt)
                        else:
                            img = screenPrint(np.full((480,1600),COLOR_BAD,np.uint16),"No Signal!")
                            times = printFPS(times)
                            tn = time.time()
                        lt = tn
                    except KeyboardInterrupt:
                        camera.release()
                        exit()
                    except Exception as e:
                        traceback.print_exc()
                    if len(times) > 100:
                        times = printFPS(times)
            time.sleep(3)
        except KeyboardInterrupt:
            camera.release()
            exit()
        except Exception as e:
            ec += 1
            if ec > 10:
                ec = 0
                raise e
            else:
                traceback.print_exc()
        finally:
            camera.release()

def screenPrint(img,text,color=COLOR_NORMAL,pos=(1209,385)):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 2.5
    if img.shape[1] < 1600:
        img = cv2.copyMakeBorder(img,0,0,0,1600-img.shape[1],cv2.BORDER_CONSTANT,value=color)
    return cv2.putText(img, text, pos, font_face, scale, (0xc4,0xe4), 2, cv2.LINE_AA)

def getUndist(c):
    r, img = c.read()
    if r:
        img = cv2.remap(img, mapx, mapy, interpolation=cv2.INTER_LINEAR)
    return r, img

def printFPS(times):
    print(f"FPS: {len(times)/np.asarray(times).sum():.2f}")
    return []

def onScreen(buf,f,c,t):
    if f is not None:
        if len(f.shape) > 2 and f.shape[2] != 2:
            f = cv2.cvtColor(cv2.resize(f,sDIM),CVT3TO2B)[108:588]
        f = screenPrint(f,t,c)
        buf.write(f)
       # for i in range(480):
       #     buf.write(f[i])
        buf.seek(0,0)

if __name__ == "__main__":
    subprocess.run(['sh','-c','echo 0 | sudo tee /sys/class/leds/PWR/brightness'])
    run()


###############
#  References #
###############
# [1] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
# [2] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
# 