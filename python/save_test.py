#!/usr/bin/env python3
import cv2 as cv, code, traceback
from v4l2py import Device, VideoCapture
from multiprocessing import Process, Pipe
from Constants import extract_index

count = 0
p1,p2 = Pipe()
p3,p4 = Pipe()
leave = False
fourcc = cv.VideoWriter_fourcc(*"H264")
fps = 6
size = (1920,1080)

def run():
    Process(target=save_video,daemon=True).start()
    Process(target=convert_video,daemon=True).start()
    get_video()

def convert_video(pin=p2,pout=p3):
    leave = False
    while not leave:
        try:
            if pin.poll(0.19): pout.send(cv.cvtColor(pin.recv(),cv.COLOR_YUV2BGR_YUYV))
            else: print("cam pipe empty")
        except:
            leave = True
            break

def save_video(p=p4):
    o = None
    leave = False
    while not leave:
        if leave: break
        try:
            o = cv.VideoWriter(f"/media/usb/test{count}.mkv",cv.CAP_FFMPEG,fourcc,fps,size)
            while not leave:
                try:
                    if p.poll(0.19): o.write(p.recv())
                    else: print('convert pipe empty')
                except:
                    leave = True
                    break
        finally:
            if o is not None: o.release()

def get_video(p=p1):
    global leave
    while not leave:
        try:
            with Device.from_id(extract_index("/dev/v4l/by-id/usb-HD_USB_Camera_HD_USB_Camera-video-index0")) as c:
                c.controls.brightness.value = 25
                vc = VideoCapture(c)
                vc.set_format(size[0],size[1],"YUYV")
                with vc as stream:
                    for frame in stream:
                        if leave: break
                        p.send(frame.array.reshape(size[1], size[0], 2))
        except: 
            traceback.print_exc()
            leave = True
            break

if __name__ == "__main__":
    run()
    code.interact(local=dict(globals(), **locals()))
