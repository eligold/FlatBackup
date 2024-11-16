<h1 align="center"> FlatBackup </h1>


<p align="center">
    <img src="./assets/doc/opencvlogo.png" alt="opencv image failed to load" width="72px" height="64px"> <nbsp> <nbsp>
    <img src="./assets/doc/Raspberry_Pi_Logo.ico" alt="pi image failed to load"> <nbsp> <nbsp>
    <img src="./assets/doc/pythonlogo.png" alt="python image failed to load" width="71px" height="64px">
</p>

<h2 align="center"> Fisheye Image Correction and <br>OBDII Boost Gauge <br></h2>

<p align="center">
    <img src="./assets/doc/flipscreen.jpg" width=67% alt="flip screen image failed to load">
    <br>Yeah, this was never going to cut it
</p>


## Overview
This project originated from my attempts to fit a backup camera on my 2013 Audi A3 and started to balloon in scope from there. Audi didn’t offer the 8P generation of A3 with a backup camera but the A6 and the Q7 from then were both offered with them and conveniently also use the exact same component for mounting license plate lights and the trunk latch as my car. After tracking one down on eBay with an intact camera I wired it all up and found a simple flip-up display for the image. I quite like the OEM fitment of the camera however it’s output is highly distorted from a wide-angle fisheye lens that made accurately gauging distances while parking impossible. I have to assume the Audi system these cameras are meant to connect to does some sort of post-processing on the image and I often wondered if I could achieve a similar effect with software running on a cheap Single Board Computer such as the Raspberry Pi.

<p align="center">
    <img src="./assets/doc/IMGrear.jpeg" width=76% alt="seamless integration picture failed to load">
    <br>See the camera? Me neither.

</p>

I had an unused Pi 4 in my electronics collection that paired perfectly with this extra wide touchscreen display module that even included mounting hardware to install a pi directly onboard found on Amazon. I've never worked with OpenCV before however I was able to leverage this powerful library to calibrate my camera and employ the derived coefficients to flatten every image I read from the backup cam before showing it on the screen. I assembled a simple frame out of scrap aluminum L brackets and attached it using the screw mounting my [wireless phone charger](https://www.amazon.com/MCQVP-XTET-MagicMount-Magnetic-Qi-Certified-FreeFlow/dp/B07Z7CYRD2?th=1) to this [Clearmounts](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low) product secured between the center dashboard vents. My efforts to avoid modifying the interior were for naught because I had to rip apart most of the floor and trunk trim running the video cable once I validated my camera installation then drilled a big hole in the center console for the system power button. I soon added an OBDII reader for communication with the car, allowing me to project real-time engine information such as intake boost pressure on the screen. A second USB camera module mounted to a DIN rail that also supports the 12V to 5V converter acts as a dash cam which should come in handy in the event of a traffic incident.

<p align="center">
    <img src="./assets/doc/pi.screen.jpg" alt="screen image failed to load" width="57%"><img src="./assets/doc/clearmounts.png" alt="" width="32%">
    <img src="./assets/doc/Side-by-side.png" alt="Side by side image of undistortion failed to load!" width=95%>
</p>

## Implementation
Existing all-in-one systems for backup and dash cameras were either too cheap to be good or too good to be in my price range so I decided to split the difference and build my own expensive model with an excruciatingly limited feature set 🙃

Starting with a simple loop to read the camera and write the image on screen it quickly became apparent that a bit more nuance was required. Now the script employs the `multiprocessing` library for true multi-core execution and `threading` to maximize resource usage while limiting downtime during IO-bound operations like sensor reads. The touch panel control and interface with an OBD reader gave me the opportunity to work with new open source libraries and releasing myself from the limitations of a single GIL gave rise to the added dashcam feature which for the most part works but seems to drop frames and might benefit from the addition of a queue. Bluetooth music with autoconnect to my phone rounded out the project although an upgrade from the Pi's native 10-bit PDM audio output is sorely needed.

All told I think the project came together nicely and provided me with a platform to work on a number of new and existing skillsets. I have some background in linux but there’s still plenty for me to learn and nearly every facet of this project touched on stuff I was not familiar with. In my efforts to automate bluetooth connection for playing music thru the car stereo I got to learn about `systemd` for task automation. I fleshed out my knowlege of the `fstab` file to mount drives by label supporting storage expansion on which to save dashcam recordings. Slimming down the OS to fit everything on a high endurance 4GB SD card introduced me to tools like `localepurge` and better strategies for package manager caching. The `evtest` command line tool and later the `evdev` python module provided an implementation for the touchscreen protocol, giving me control over different features and a handy shutdown shortcut. I got to dive deep into USB protocols and the sparse publicly available schematics of the Pi itself when I ran into hardware connection issues. Too many devices plugged into the Pi’s native USB ports overloads something and shuts it down, presumably due to running for long periods in the harsh environment of my car’s windshield so I needed to find a workaround. The OBD connection is facilitated by a simple serial to USB chip, and it was trivial to remove that and instead wire the output connection directly to a UART on the Pi’s GPIO header. This in turn offered me the opportunity to learn more about the device tree which I had to use to enable that hardware module on the Pi’s side.

<p align="center">
    <img src="./assets/doc/ADVcap.jpg" alt="custom board image failed to load!" width=38%>
    <img src="./assets/doc/easycap.jpeg" alt="easycap image failed to load" width="33%" min-width="160px">
</p>

I dove even further into that rabbit hole when implementing a replacement for the USB video digitizer originally underlying the whole project. After initially considering a CSI-2 pi camera module to replace the USB dashcam I instead opted to try my hand at implementing a converter chip to utilize the MIPI connection on a custom PCB. The `ADV7280A-M` can convert any one of up to 8 single-ended analog video signals to a single CSI-2 lane with format auto-detection and is conveniently supported by a native driver and device tree overlay in the Pi OS. Heavily referencing the schematics for Analog Device’s own `ADV7280A-M` evaluation module made it possible to design a proof of concept in just over a week and thanks to DigiKey and OSHPark/OSH Stencils I was able to go from concept to having boards in-hand over the span of a month. There are a few issues with the output that my reading seems to indicate are the result of a buffer configuration within the Pi’s media backend. The converter driver was originally written for chips that are two generations older than what I’m using and many onboard features are not broken out to controls accessible from the OS. The driver has a lot of room for improvement and has taken over my attention from further development of this project for the time being. Stay tuned for updates!

The code continues to improve and I've already benefitted on more than one occaision from having this system installed. Hopefully soon I'll have the time and resources to rework the hardware into a single board for a Pi Compute Module 4 and all the peripherals to directly connect or backpack onto the driver board for an appropriate screen since the module is big and heavy posing a safety risk in the event of a collision. Possible new hardware design coming soon...

##### Some of the topics I had a chance to familiarize myself with throughout the course of this project, in no particular order:

1. C++
1. OpenCV
1. Python built-in libraries
1. The GIL and parallelism in Python
1. Inheritence and Python project organization
1. Automation in linux using `systemd` services
1. Linux graphics processing

### Future Development Goals

1. ~~Multiprocessing parallel execution!~~ ✓
1. Smoothing upscale with ML using coral TPU
1. Compute module 4 with custom HaT for power conversion and camera/sensor input
1. nvme drive for cable cleanup and easy access
1. Custom PCB to consolidate power, ~~digitization~~, OBD connection, and wiring
1. Implement backup battery with smart charging and fail-safe BMS
1. ML object detection support to minimize power and storage use in sentry mode

### Contribution Guidelines

This project is wildly application specific but I welcome any feedback or suggestions you might have! If you were inspired to build your own similar system I would love hear from you as well!

Image source: https://wall.alphacoders.com/big.php?i=474466
[![y u no load 4rings](./assets/pi_files/IMG_5046.PNG)](https://parts.audiusa.com/)
[![python image failed to load](./assets/doc/python.png)](https://www.python.org/)
[![opencv image failed to load](./assets/doc/opencv.png)](https://opencv.org/)