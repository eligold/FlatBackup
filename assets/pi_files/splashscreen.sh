#!/bin/bash
[ -e /dev/fb0 ] && /usr/bin/fbi -d /dev/fb0 --noverbose -a /root/splash_img.png || sleep 0.19 && /root/splashscreen.sh
