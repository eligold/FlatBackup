#!/usr/bin/env python3
import cv2 as cv, numpy as np, code

def color(r,g,b):
    a = cv.cvtColor(np.full((1600,480,3),[b,g,r],np.uint8),cv.COLOR_BGR2BGR565)
    b = a[0][0]
    print(f"0x {b[0]:02X} {b[1]:02X}")
    with open('/dev/fb0','rb+') as buf:
        buf.write(a)

if __name__ == "__main__":
    code.interact(local=globals())
