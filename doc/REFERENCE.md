####  References

1. ] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
1. ] https://github.com/brendan-w/python-OBD/
1. ] https://thinkingtoasters.com/2021/05/24/yuv422-to-rgb/
1. ] https://github.com/wjwwood/serial/
1. ] https://github.com/nholthaus/units
1. ] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
1. ] https://github.com/waveform80/picamera/issues/335#issuecomment-252662503
    ```
    v4l2-ctl -v width=2592,height=1944,pixelformat=MJPG
    v4l2-ctl --stream-mmap=3 --stream-count=100 --stream-to=unique_path.mjpeg
    [c]vlc --demux=mjpeg --mjpeg-fps=15 unique_path.mjpeg
    ```
1. ] https://stackoverflow.com/questions/58772943/how-to-show-an-image-direct-from-memory-on-rpi
    ```
    import numpy as np
    # Map the screen as Numpy array
    # N.B. Numpy stores in format HEIGHT then WIDTH, not WIDTH then HEIGHT!
    # c is the number of channels, 4 because BGRA
    h, w, c = 1024, 1280, 4
    fb = np.memmap('/dev/fb0', dtype='uint8',mode='w+', shape=(h,w,c)) 
    ```
1. ] https://forums.raspberrypi.com/viewtopic.php?t=343341
    ```
    # restart USB, needs uhubctl?
    if not {conditions}:
        cmd = "echo '1-1' > /sys/bus/usb/drivers/usb/unbind"
        p = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        time.sleep(2)
        cmd = "echo '1-1' > /sys/bus/usb/drivers/usb/bind"
        p = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    ```
1. ] https://stackoverflow.com/questions/59772765/how-to-turn-usb-port-power-on-and-off-in-raspberry-pi-4
    ```
    echo '0' | sudo tee /sys/devices/platform/soc/3f980000.usb/buspower # turn off
    echo '1' | sudo tee /sys/devices/platform/soc/3f980000.usb/buspower # on
    ```
1. ] https://stackoverflow.com/questions/11436502/closing-all-threads-with-a-keyboard-interrupt h/t [Paul Seeb](https://stackoverflow.com/a/11436603)
    ```
    from threading import Thread, Event
    from time import sleep

    def thready_boi(data, run_event):
        while run_event.is_set():
            do stuff...


    def main():
        run_event = Event()
        run_event.set()
        thread = Thread(target=thready_boi,args=(data,run_event))
        thread.start()
        
        try:
            while 1:
                time.sleep(.1)
        except KeyboardInterrupt:
            run_event.clear()
            thread.join()
    ```
AptX > A2DP
1. ] https://github.com/tmckay1/pi_bluetooth_auto_connect
1. ] https://github.com/lukasjapan/bt-speaker
1. ] https://github.com/elsampsa/btdemo
1. ] https://github.com/RPi-Distro/pi-bluetooth/blob/master/usr/bin/bthelper
1. ] https://github.com/nicokaiser/rpi-audio-receiver/
1. ] https://github.com/Douglas6/blueplayer/
    This script will come in handy for using touch input to control iphone audio, calls, etc.
1. ] https://forums.raspberrypi.com/viewtopic.php?t=235519
    first attempt at bluetooth auto-connect for car audio involved following the steps laid out in this forum post
1. ] https://raspberrypi.stackexchange.com/questions/50496/automatically-accept-bluetooth-pairings/55589#55589
    ```
    sudo bluetoothctl <<EOF
    power on
    discoverable on
    pairable on
    agent NoInputNoOutput
    default-agent
    EOF
    ```
1. ] https://gist.github.com/mill1000/74c7473ee3b4a5b13f6325e9994ff84c
1. ] https://www.sigmdel.ca/michel/ha/rpi/bluetooth_in_rpios_02_en.html
1. ] https://pythonhosted.org/BT-Manager/config.html
1. ] https://github.com/pauloborges/bluez/blob/master/lib/uuid.h
1. ] https://www.csselectronics.com/pages/obd2-pid-table-on-board-diagnostics-j1979
1. ] https://raspberry-projects.com/pi/programming-in-c/uart-serial-port/using-the-uart
    Great breakdown of serial access in C++
1. ] https://stackoverflow.com/questions/19790570/using-a-global-variable-with-a-thread
    ```
    def thread1(threadname):
        while True:
        lock_a.acquire()
        if a % 2 and not a % 2:
            print "unreachable."
        lock_a.release()

    def thread2(threadname):
        global a
        while True:
            lock_a.acquire()
            a += 1
            lock_a.release()
    ```
1. ] https://pythonforthelab.com/blog/handling-and-sharing-data-between-threads/
1. ] https://stackoverflow.com/questions/65923410/how-to-execute-synchronous-cv2-in-async-app
1. ] https://rotational.io/blog/spooky-asyncio-errors-and-how-to-fix-them/
1. ] https://peps.python.org/pep-0492/#why-stopasynciteration
1. ] https://learn.adafruit.com/adding-a-real-time-clock-to-raspberry-pi/overview
1. ] https://forums.balena.io/t/disable-console-over-serial-in-dev-on-rpi3/1412/7
1. ] [https://13945096965777909312.googlegroups.com/attach/d7c59fe234298ded/minicom.cpp](https://13945096965777909312.googlegroups.com/attach/d7c59fe234298ded/minicom.cpp?part=0.1&view=1&view=1&vt=ANaJVrGAA71JEVEd4XEuxt4VG5FwYI41tF0sUnwR5UahihIrjmiCfS_xpkNKyNVPVjY8P9OESmx3ShNeygnof3162UaTuSNlbdUcoqu1T7HRyUoyHgYL-nc)
1. ] https://people.eecs.ku.edu/~jrmiller/Courses/JavaToC++/BasicPointerUse.html
1. ] https://cplusplus.com/reference/cstdio/scanf/
1. ] https://opencvexamples.blogspot.com/2013/09/creating-matrix-in-different-ways.html
1. ] https://medium.com/@nullbyte.in/part-1-exploring-the-data-types-in-opencv4-a-comprehensive-guide-29b452a95e15
1. ] https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
1. ] https://longervision.github.io/2017/03/18/ComputerVision/OpenCV/opencv-internal-calibration-circle-grid/
1. ] https://www.linkedin.com/pulse/linux-framebuffer-all-you-need-soumya-basak/
1. ] https://stackoverflow.com/questions/600079/how-do-i-clone-a-subdirectory-only-of-a-git-repository/73254328#73254328
    ```
    $ git clone --filter=blob:none --sparse  %your-git-repo-url%
    $ cd %the repository directory%
    $ git sparse-checkout add %subdirectory-to-be-cloned%
    $ cd %your-subdirectory%
    ```
1. ] https://stackoverflow.com/a/5354644
    `git config --global alias.tree "log --graph --decorate --pretty=oneline --abbrev-commit"`
1. ] https://github.com/opencv/opencv/issues/18461#issuecomment-750523958
    `export DISPLAY=:0.0`
1. ] https://forums.raspberrypi.com/viewtopic.php?t=291358
    `select-editor`
    `update-alternatives --config editor`
1. ] https://askubuntu.com/questions/237963/how-do-i-rotate-my-display-when-not-using-an-x-server
    `echo 3 | sudo tee /sys/class/graphics/fbcon/rotate`
1. ] https://stackoverflow.com/a/52398424
    `ffmpeg -pix_fmt yuv420p [...]` to convert mjpeg into playable mkv
1. ] https://www.reddit.com/r/podman/comments/12931nx/enabling_services_as_the_nonssh_user_systemctl/
    `sudo systemctl --user -M dietpi@ restart {service}`

Additional resources regarding the generation of python bindings for custom C++ OpenCV modules using OpenCV4 can be found [in the cpp subdirectory](./cpp/README.md)

 git clone --single-branch --branch code --depth 1 git@github.com:eligold/FlatBackup.git