####  References

1. ] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
1. ] https://github.com/brendan-w/python-OBD/
1. ] https://thinkingtoasters.com/2021/05/24/yuv422-to-rgb/
1. ] https://github.com/wjwwood/serial/
1. ] https://github.com/nholthaus/units
1. ] https://github.com/tmckay1/pi_bluetooth_auto_connect
1. ] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
1. ] https://github.com/waveform80/picamera/issues/335#issuecomment-252662503
    ```
    v4l2-ctl -v width=2592,height=1944,pixelformat=MJPG
    v4l2-ctl --stream-mmap=3 --stream-count=100 --stream-to=unique_path.mjpeg
    cvlc --demux=mjpeg --mjpeg-fps=15 unique_path.mjpeg
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
1. ] [https://13945096965777909312.googlegroups.com/attach/d7c59fe234298ded/minicom.cpp](https://13945096965777909312.googlegroups.com/attach/d7c59fe234298ded/minicom.cpp?part=0.1&view=1&view=1&vt=ANaJVrGAA71JEVEd4XEuxt4VG5FwYI41tF0sUnwR5UahihIrjmiCfS_xpkNKyNVPVjY8P9OESmx3ShNeygnof3162UaTuSNlbdUcoqu1T7HRyUoyHgYL-nc)
1. ] https://people.eecs.ku.edu/~jrmiller/Courses/JavaToC++/BasicPointerUse.html
1. ] https://cplusplus.com/reference/cstdio/scanf/
1. ] https://opencvexamples.blogspot.com/2013/09/creating-matrix-in-different-ways.html
1. ] https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
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

Additional resources regarding the generation of python bindings for custom C++ OpenCV modules using OpenCV4 can be found [in the cpp subdirectory](./cpp/README.md)

 git clone --single-branch --branch code --depth 1 git@github.com:eligold/FlatBackup.git