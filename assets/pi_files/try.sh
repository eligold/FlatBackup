#!/bin/bash
if [[ "up" != "`cat /sys/class/net/wlan0/operstate`" ]]; then
	echo down
fi
