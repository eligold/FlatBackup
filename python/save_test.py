#!/usr/bin/env python3
import cv2 as cv, code, traceback
from v4l2py import Device, VideoCapture
from threading import Thread
from queue import SimpleQueue, Empty
from Constants import extract_index

count = 0
q = SimpleQueue()
leave = False
fourcc = cv.VideoWriter_fourcc(*"HEVC")
fps = 6
size = (1920,1080)

def run():
    Thread(target=save_video,daemon=True).start()
    get_video()

def save_video(q=q):
    global leave
    leave = False
    o = None
    while not leave:
        if leave: break
        try:
            o = cv.VideoWriter(f"/media/usb/test{count}.mkv",cv.CAP_FFMPEG,fourcc,fps,size)
            while not leave:
                try: o.write(cv.cvtColor(q.get(timeout=1.19/fps),cv.COLOR_YUV2BGR_YUYV))
                except Empty: print('empty')
                except:
                    leave = True
                    break
        finally:
            if o is not None: o.release()

def get_video(q=q):
    global leave
    while not leave:
        try:
            with Device.from_id(extract_index("/dev/v4l/by-id/usb-HD_USB_Camera_HD_USB_Camera-video-index0")) as c:
                vc = VideoCapture(c)
                vc.set_format(size[0],size[1],"YUYV")
                with vc as stream:
                    for frame in stream:
                        if leave: break
                        q.put(frame.array.reshape(size[1], size[0], 2))
        except: 
            traceback.print_exc()
            leave = True
            break

if __name__ == "__main__":
    run() # code.interact(local=dict(globals(), **locals()))