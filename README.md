<h1 align="center"> FlatBackup </h1>


<p align="center">
    <img src="./assets/doc/Raspberry_Pi_Logo.ico" alt="pi image failed to load"> <nbsp> <nbsp>
    <img src="./assets/doc/pythonlogo.png" alt="python image failed to load" width="71px" height="64px"> <nbsp> <nbsp>
    <img src="./assets/doc/opencvlogo.png" alt="opencv image failed to load" width="72px" height="64px">
</p>

<h2 align="center"> Fisheye Image Correction and <br>OBDII Boost Gauge <br></h2>

### Overview

__SIDE BY SIDE OF FLATTENED AND ORIGINAL TO INTRODUCE PROJECT__
Welcome to my fisheye backup camera image correction and automotive data processing project! This GitHub repository contains the code underlying my efforts to develop a solution for enhancing my custom car backup camera installation. The project evolved from a desire to cut my teeth with a powerful tool I had only had peripheral experience with both academically and professionally, OpenCV. When I installed an Audi original backup camera into my car, the image projected to a standard 4:3 ration NTSC resolution screen was heavily distorted from the fisheye lens and I knew that was something I could rectify using the power of Python and OpenCV. With a knock-off Easy-Cap adapter to digitize the signal I am able to process it on a Raspberry Pi and display the corrected image on an HDMI screen. An ELM327 USB OBDII adapter allows me to calculate and display turbocharger boost pressure from real-time car sensor data.

## Background
This project started with my search for the best backup camera to retrofit onto my last-generation Audi A3. With no visually appealing universal options on the market several attempts were made to fashion custom low-profile solutions. Aftermarket replacements for the stock license plate light fixture as well as the latch actuator module for opening the rear hatch failed to live up to expectaions. More importantly they lacked the seamless integration of an OEM component. I was pretty sure that 8P A3 wasn't offered with a backup camera but I didn't give up hope for a factory solution. The rear latch for the A3 is also used on the A6 and Q7, both of which had alternatives that came with a backup camera. After perusing eBay I found a used part that included the camera with both power and signal plug sets intact. Score!

![seamless integration picture failed to load](./assets/doc/IMGrear.jpeg)
Doesn't get much more seamless than that 👌

The output from my newly installed camera was initially displayed on a cheap flip up display from Amazon or eBay or wherever. It was somehow always too dim in the daytime and too bright at night and had an annoying habit of sliding around despite the thoughtful inclusion of a small square bit of drawer liner for use on the dashboard. I knew I would have to find a better long-term solution. With the distortion from the wide angle lens not much useful detail could be made out on the standard 4:3 ratio screen size and displaying the camera's view of my own license plate seems like kind of a waste of resources. Having already retrofitted my [Scoshe wireless charger](https://www.amazon.com/MCQVP-XTET-MagicMount-Magnetic-Qi-Certified-FreeFlow/dp/B07Z7CYRD2?th=1) and a more stable screen to my [Clearmounts dashboard bracket](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low), an idea began to take shape...

<img src="./assets/doc/flipscreen.jpg" alt="flip screen image failed to load" width="54.5%"><img src="./assets/doc/compare.jpg" alt="comparison image failed to load" width="45.5%">

### Project Components
#### > Touchscreen and Raspberry Pi
My solution runs on a Raspberry Pi, serving as the central hub for image correction and OBDII data processing. Python scripts handle the integration of these components with multi-threaded processing to promote seamless operation. In order to maximize the useable regions of the undistorted image this project required an extra wide screen and luckily I found a screen on amazon that provided the optimal aspect ratio and even integrated support for mounting the pi directly to it. This exact screen is no longer available but [this unit from amazon](https://www.amazon.com/dp/B087CNJYB4/ref=sspa_dk_detail_0) is nearly identical and there are [many](https://www.amazon.com/ElecLab-Touchscreen-Capacitive-1280x480-10-3-inch-hdmi-1280x480/dp/B0BWSSKDV4/ref=sr_1_2) [other](https://www.amazon.com/gp/product/B09SVDCSQJ/ref=ox_sc_act_title_2) [options](https://www.amazon.com/ElecLab-Raspberry-Touchscreen-Capacitive-1280x400/dp/B09YJ37SBH/ref=sr_1_3) to choose from depending on your application. Touch input was the last piece of the puzzle, and after a failed attempt to implement it in pure python using the `async` library I instead opted to pipe the output of the shell command `evtest` through the `Popen` construct of the `Subprocess` python module to a queue that is handled in the main thread.
<img src="./assets/doc/pi.screen.jpg" alt="pi screen image failed to load">

#### > OEM Camera Fisheye Image Correction
Utilizing the power of OpenCV and Python, I've implemented built-in undistortion algorithms to correct fisheye lens-distorted images captured with the replacement OEM backup camera. 
__MORE PROCESS__
A [clone of the EasyCap USB A/V digitizer](https://www.ebay.com/itm/383709416325) facilitates analog video conversion enabling real-time processing on the Raspberry Pi for display in a more natural perspective. Between the regular undistortion method and the fisheye submodule verison, the latter seemed to suit my backup camera lens better with testing. Through some trial and error with a small helper script crafted to generate a set of baseline calibration images, a fairly consistent and replicable list of numbers was produced by the module's undistortion method. This list is used to create a matrix for reconstructing the raw image in a flattened perspective. The calibration script became more complicated yet more precise as additional tutorials and documentation for the fisheye submodule of OpenCV were reviewed.
__threading, 3 vs 4,__
<img src="./assets/doc/easycap.jpeg" alt="easycap image failed to load" width="38%">

#### > OBDII Data Integration
An extraordinarily wide screen proved to be the most practical way to display the useful viewing area of the undistorted image however after tweaking the final layout some unused space remained to one side. I decided to use this space for displaying the boost pressure from the car's turbocharger. There are a number of ways to measure boost pressure in a forced induction car though most of them require invasive modifications that can compromise the weatherproofing of the interior. Rather than adding an air hose for a mechanical guage or running a wire through the heat shield to the engine bay I opted to use the built in sensors from the factory. The output of these sensors can be accessed through the OBDII port with an ELM327 USB adapter thanks to some handy code from [brendan-w](https://github.com/brendan-w/) with this [python-OBD project](https://github.com/brendan-w/python-OBD/).

My car comes with a Manifold Absolute Pressure (MAP) sensor but Audi in their infinite wisdom decided not to break out values from reading that particular sensor via the standard OBD protocol. Not to worry; using only the total engine displacement volume of 1984$cc$, the RPM, readings from the Intake Air Temperature (IAT) sensor, and readings from the Mass Air Flow (MAF) sensor combined with some fancy high school math the boost pressure can be calculated within a reasonable margin of error:

$$ P \times V_{f} = m_{f} \times RT^{[1]} $$

The above equation is derived from the ideal gas law $ PV = nRT $ to relate the volumetric flow rate and molar mass flow rate of the intake air in order to calculate instantaneous boost pressure. All the necessary information is available through the OBDII connection to facilitate calculations as fast as the protocol can supply new data. Breaking down the terms:

1. $P$ is the instantaneous boost pressure we are calculating
1. $V_{f}$ is the volumetric flow rate of gas through the engine or 1984$cc$ for every two rotations of the crankshaft
1. $m_{f}$ is the molar flow rate of air determined by dividing the MAF sensor output in $g \over s$ by the molar mass of air, 28.949$g\over mol$
1. $R$ is the gas constant, helpfully provided by the Unit python library
1. $T$ is the absolute temperature read from the IAT and converted to Kelvin

Rather than assume a constant atmospheric pressure the car's barometric pressure sensor (BPS) readings are subtracted from calculated absolute pressure to determine true boost pressure. If the result is negative that means the system is in vacuum and the reading is converted from $PSI$ to $bar$ since I don't really care as much about the magnitude. All of this is handled by the aptly named `Unit` python library.

#### > Wiring and Mounting
<img src="./assets/doc/Fakra.jpg" alt="fakra key chart failed to load" height="240px">
<img src="./assets/doc/fakraBNC.jpeg" alt="fakra bnc image failed to load" height="240px">

Video is carried through a Fakra antenna connector which come with many different key options. This is typically indicated by the housing color according to the internet and I spent much too long on a fruitless search for a high quality adapter specific to the key of the plug for the camera. A plethora of cheap options were forthcoming but the quality of the plug housings on most leave a lot to be desired and I don't look forward to repeating the interior trim disassembly to replace a broken plug. With a deeper dive through my references I realized that a universal "Z" key Fakra variation exists which works with most of the key options including our camera plug. High quality RF cables with custom terminations are typically expensive from reputable suppliers but [Amazon came to the rescue](https://a.co/d/6lxqHxw) with a mass-produced solution. The one from the link is no longer offered but I'm sure there are plenty of similar products available now. I used a small BNC to RCA adapter and slim RCA cable from [monoprice](https://www.monoprice.com/product?p_id=4127) although they no longer appear to offer the latter.

<img src="./assets/doc/hatch_mess.png" alt="torn apart hatch image failed to load" width="75%">
<br>

 __a heatsink with fan to keep things cool. A Meanwell DC/DC converter steps the car voltage down to 5V__

__FIXME__
Wiring involved removing the interior trim of the rear hatch and running wires along the existing harnesses. There exists a channel for routing the factory harness from the roof through a hose protecting them from the elements. The hose was too tight to push a stiff wire through so the power and video cables run out of the trim and through the cabin in a way that is noticeable but unobtrusive
although I wasn't able to get the wires through the weatherproof articulated tube in which the stock harnesses are run and I ended up taking out more inner body panels off than I should have. Getting everything back together necessitated pulling all the rest of the trim panels from the trunk before reinstalling everything properly. If I were to go back and do it again I would try to vacuum a string through the existing wire tube to pull my cables with. The Fakra system is essentially an easily removable shell around an SMB connector, which is a small RF connector similar to BNC or SMA but with no retention features.

 As it is a small loop of wires exits the top of the hatch with enough slack to reach the headliner trim while the hatch is fully open. It is visible but unobtrusive and proper cable management helps keep it from moving much while driving.
__picture of progress, picture of final wire arrangement__

I connected the 12V power supply in-line with harness wires for the trunk 12V accesory plug using some high current waterproof connectors I had on hand keeping nearly the entire wire run out of the cabin. A second small loop of the power cable was routed through a vent in the trunk trim with a redundant set of connectors as a failsafe quick disconnect. With the trim removed I also took the oppotunity to wire up some high power Philips LEDs on custom-made aluminum PCBs to replace the pathetically dim single incandescent bulb that used to illuminate my trunk. Even at night it's always bright and sunny in there now!
<img src="./assets/doc/hatch_light_inset.png" alt="trunk light image failed to load" width="75%">

A recently purchased [Clearmounts phone adapter](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low), pictured below, serves to conveniently and robustly secure my homebrew solution between the two centermost vents on my dashboard. After removing the simple magnetic holder that came with it I installed an articulated Scosche handsfree wireless charging mount similar to one that previously mounted to my windshield with a suction cup. I realized this model would be unsuitable for adapting to my project only after disassembling it completely so I purchased the articulated vent-mount model, securing a length of scrap aluminum angle extrusion to the back with the ball joint retaining screw through the Clearmounts adapter. Using a small L-bracket and some fastening hardware I mounted a second length of extrusion with holes drilled out to match the mounting pattern of my new widescreen display. It's practical but I'd like to replace it with something a bit more attractive down the line, perhaps in the vein of the beautiful custom devices built by [DIY Perks on YouTube](https://www.youtube.com/c/diyperks).

<img src="./assets/doc/clearmounts.png" alt="clearmounts image failed to load" width="50%">

## Future Development Goals

1. convert code to C++
1. implement backup battery with smart charging and custom BMS
1. smoothing upscale with ML using coral TPU
1. ML object detection support to minimize power and storage use in sentry mode
1. Bluetooth audio endpoint with autoconnect
1. Apple CarPlay
1. Pi 5, nvme drive

## Contribution Guidelines

This project is wildly application specific but I welcome any feedback or suggestions you might have! If you were inspired to build your own similar system or would like some guidance to replicate this specific solution I would love hear from you as well!

__SETUP__
1. flash buster or bullseye with pi imager, add login/wifi details
1. enter god mode
    chaos ensues
    ```
    sudo su -
    ```
1. do I have to mess with program?
    ```
    raspi-config -> locale, keyboard
    ```
1. Turn off swap file to spare the SD card and trim some fat
    ```
    dphys-swapfile swapoff
    systemctl disable dphys-swapfile.service
    systemctl disable ModemManager.service
    apt autoremove -y modemmanager
    ```
1. get some tools and make sure the system is up to date in the background so you can do other things
    ```
    apt install -y vim screen
    apt update && screen -d -m apt upgrade -y
    ```
1. add this line to `/etc/fstab`. I like to use `vim` but you can use `nano` if you're not an elite hacker:
    ```
    LABEL=[label] /[mount/location/] [fs type] nofail      0       0
    ```
1. add the following to rc.local:
    ```
    screen -d -m /root/carCam.py
    ```
1. add the following lines to config.txt
    ```
    disable_splash=1
    dtparam=i2c_arm=on
    framebuffer_width=1600
    framebuffer_height=480
    hdmi_force_hotplug=1
    hdmi_group=2
    hdmi_mode=87
    hdmi_ignore_edid=0xa5000080
    hdmi_cvt 1600 480 60 6 0 0 0
    hdmi_drive=2
    hdmi_enable_4kp60=1
    gpu_mem=128
    dtoverlay=gpio-fan,gpiopin=14,temp=60000
    ```
1. add the following to the end of cmdline.txt
    ```
    
    ```
1. Install some tasty tasty dependencies
    ```
    apt install -y python3-opencv python3-pip v4l-utils
    pip3 install obd
    ```
1. 


####  References

1. ] https://www.first-sensor.com/cms/upload/appnotes/AN_Massflow_E_11153.pdf
1. ] https://github.com/brendan-w/python-OBD/
1. ] https://github.com/wjwwood/serial/
1. ] https://github.com/nholthaus/units
1. ] https://github.com/tmckay1/pi_bluetooth_auto_connect
1. ] https://towardsdatascience.com/circular-queue-or-ring-buffer-92c7b0193326
1. ] https://github.com/waveform80/picamera/issues/335#issuecomment-252662503
    ```
    v4l2-ctl -v width=2592,height=1944,pixelformat=MJPG
    v4l2-ctl --stream-mmap=3 --stream-count=100 --stream-to=unique_path.mjpeg
    vlc --demux=mjpeg --mjpeg-fps=10 unique_path.mjpeg
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




[ ![y u no load 4rings](./assets/pi_files/IMG_5046.PNG) ](https://parts.audiusa.com/)
source: https://wall.alphacoders.com/big.php?i=474466

[ ![python image failed to load](./assets/img/python.png) ](https://www.python.org/)

[ ![opencv image failed to load](./assets/img/opencv.png) ](https://opencv.org/)