#!/usr/bin/env python3
import cv2 as cv, code, traceback
from v4l2py import Device, VideoCapture
from multiprocessing import Process, Pipe
from Constants import extract_index

count = 0
p1,p2 = Pipe()
#p3,p4 = Pipe()
leave = False
fourcc = cv.VideoWriter_fourcc(*"mp4v")
fps = 30
size = (1920,1080)

def run():
    Process(target=save_video,daemon=True).start()
    get_video()

def save_video(p=p2):
    o = None
    leave = False
    while not leave:
        if leave: break
        try:
            o = cv.VideoWriter(f"/media/usb/test{count}.mp4",cv.CAP_FFMPEG,fourcc,fps,size)
            while not leave:
                try:
                    if p.poll(0.19): o.write(cv.imdecode(p.recv(),cv.IMREAD_COLOR))
                    else: print('convert pipe empty')
                except:
                    leave = True
                    break
        finally:
            if o is not None: o.release()

def get_video(p=p1):
    global leave
    vc = None
    while not leave:
        try:
            with Device.from_id(extract_index("/dev/v4l/by-id/usb-HD_USB_Camera_HD_USB_Camera-video-index0")) as c:
                c.controls.brightness.value = 25
                vc = VideoCapture(c)
                vc.set_format(size[0],size[1],"MJPG")
                with vc as stream:
                    for frame in stream:
                        if leave: break
                        p.send(frame.array)
        except: 
            traceback.print_exc()
            leave = True
            break
        finally:
            if vc is not None: vc.release()

if __name__ == "__main__":
    run()
    code.interact(local=dict(globals(), **locals()))
