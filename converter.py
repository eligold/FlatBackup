#!/usr/bin/env python3
import os
from subprocess import run

def convertCurrentDir():
    for f in os.listdir():
        cmd = f"ffmpeg -f mjpeg -r 15 -i {f} -c:v h264 -r 15 {f[:-5]}mkv"
        if f.endswith(".mjpeg"): run(cmd,shell=True,check=False,text=True)
    

if __name__ == "__main__":
    convertCurrentDir()

