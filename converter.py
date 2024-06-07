#!/usr/bin/env python3
import os
from subprocess import run

fList = []

def convertCurrentDir():
    for f in os.listdir():
        cmd = f"ffmpeg -f mjpeg -r 15 -i {f} -c:v h264 -r 15 {f[:-5]}mkv"
        if f.endswith(".mjpeg"): 
            try:
                run(cmd,shell=True,check=True,text=True)
            except:
                fList.append(f)
    

if __name__ == "__main__":
    convertCurrentDir()
    print(fList)

