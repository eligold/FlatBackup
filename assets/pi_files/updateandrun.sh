#!/bin/bash
DIR="/root/"
EXT_DRIVE="/mnt/usb"
# Ensure the external drive is mounted
if ! mountpoint -q "$EXT_DRIVE"; then
    echo "External drive is not mounted: $EXT_DRIVE"
    echo "exiting..."
else # Check for matching files and update
    for FILE in "$DIR"*; do
        BASENAME=$(basename "$FILE")
        EXT_FILE="$EXT_DRIVE/$BASENAME"

        if [ -f "$EXT_FILE" ]; then
            echo "Updating $FILE from $EXT_FILE"
            mv -f "$FILE" "$EXT_DRIVE/old-$BASENAME"
            mv -f "$EXT_FILE" "$DIR"
        fi
    done
    gpioset 0 25=1
    sleep 0.019
    dt-overlay adv728x-m adv7280m=1
    /usr/bin/screen -d -m /root/CarCam.py
fi

exit 0