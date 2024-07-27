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
This project arose from my frustration with the distortion apparent in the output of the OEM Audi backup camera I installed in my 8P generation A3. After trying a few home-brew solutions cobbled together from generic eBay cameras and aftermarket housings replacing the license plate light and the trunk latch itself, it occurred to me that there might be an Audi part that would drop in with no modification as auto manufacturers tend to reuse parts across models. Although my car was not offered with a backup camera option, a quick jaunt to the parts website revealed that the same trunk latch and license plate light mounting component in my car was also used in the A6 and Q7. Both of these higher end models were offered with a backup camera mounted in an equivalent component and it wasn’t long before I located one on eBay pulled from a Q7 that included the camera for around \$100. 
![Side by side image of undistortion failed to load!](./assets/doc/Side-by-side.png)
The distortion was bad enough but using this generic flip-up screen with nothing but a small section of shelf liner to steady it invariably meant it would go flying off the dashboard from hard brakes or sharp turns, further adding to my frustration. The lens of the OEM camera is a wide-angle fisheye style which heavily distorts the view at the edges of the frame where most of the objects I wanted to avoid would show up. I often found myself thinking that with the capabilities offered in open source libraries like OpenCV something that might have been impossibly complex for me to code myself like flattening a fisheye image had become a trivial task using minimal hardware resources available in a $35 Raspberry Pi, but the physical aspects such as mounting and powering the device seemed to preclude the possibility of implementation. After several months of being grumpy with myself for not coming up with a better solution and a few serendipitous discoveries online I had run out of excuses not to try this project out.

I had been using a poorly fitted vent-mount phone holder for handsfree music in the car but after launching my phone into my lap or the back seat along with the screen I knew I had to come up with a better alternative. I was reluctant to stick anything to my dashboard permanently and started to think I might just be SOL when I stumbled on a post in a Facebook group for 8P A3 owners about custom aftermarket mounts designed to seat in the OEM dashboard vent covers produced by a company called [Clearmounts](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low). The vents can be easily removed without damaging any interior components or leaving double-sided tape residue upon removal. Around the same time Amazon started advertising screens to me including one with an ultra wide aspect ratio that I thought would suit the project well. It featured a built-in touchscreen and mounting hardware for a pi to sit directly on the device and was exactly what I needed. Although the link is to the product page of what I ordered it has since been switched out for a smaller, lower resolution one. I removed the generic phone holder magnet from the Clearmounts bracket and installed a [Scoshe wireless charger](https://www.amazon.com/MCQVP-XTET-MagicMount-Magnetic-Qi-Certified-FreeFlow/dp/B07Z7CYRD2?th=1) in its place, affixing a length of scrap aluminum extrusion behind it and all of a sudden I had the perfect base from which to build out my project idea.

<img src="./assets/doc/clearmounts.png" alt="clearmounts image failed to load" width="36%"><img src="./assets/doc/pi.screen.jpg" alt="pi screen image failed to load" width="64%">

While the actual code to flatten an image pulled from my backup camera is only a single line of my python script, getting everything up and running correctly was anything but simple. To project points in space from the spherical view from the camera lens onto a flat plane I had to first calibrate the camera with an image of a checkerboard. This image is helpfully provided in the OpenCV documentation but it took me a fair bit of tinkering to get the detection code running and showing the image on screen at the same time. Using the difference between the expected relative positions of the grid vertices with their appearance in the captured image allows the program to develop a mapping to project flattened images. These are basically just coefficients plugged into an equation involving the pixel location on the starting image to translate it to the proper undistorted coordinates. While this was challenging in and of itself things like determining the pixel layout of the screen I was using, understanding the quirks of how OpenCV handles color, and trying to follow the spotty guidance of documentation geared towards people using OpenCV in its native C++ API stymied my earliest efforts.

<p align="center">
    <img src="./assets/doc/IMGrear.jpeg" width=60% alt="seamless integration picture failed to load">
    <img src="./assets/doc/easycap.jpeg" alt="easycap image failed to load" width="30%" min-width="240px">
</p>

Barring a loop for power and signal by the hatch hinge all camera wiring runs underneath to the interior trim until the video cable breaks out of the moulding in the passenger footwell with a fairly surreptitious exterior profile as well. The cable crosses under the floor mat and connects up to the [USB digitizer](https://www.ebay.com/itm/383709416325) so the Pi can read it. Power for the screen comes from the center console, breaking out from an unused button port above the climate controls. After messing around with a few different screen configurations and cropping levels I settled on a high zoom for the center of the view and half the magnification at the outer edges to give a general sense of other cars on the road in my blind spots at a glance. Doing so minimized the dead space inherent in the remapped image which has a large black semicircle in the top center and also includes a large portion of the bumper and my entire license plate at the bottom based on the geometry and placement of the lens. 

With those video panels making the most of my wide screen I still had a bit of room at the edge for a sidebar that could be used to present user interaction controls and additional data. An OBDII serial adapter facilitates communication with the car to read sensor data and display it on the screen such as battery voltage or engine RPM. The most interesting sensor to me was of course the intake pressure sensor which would report how much additional air the turbocharger is forcing into my peppy 2.0L engine at any given moment but for some reason those values are only accessible though a proprietary VW/Audi connection protocol rather than the internationally standardized interface. Undeterred I instead shifted gears <img width="7%" src="./assets/doc/peter.png"> and started looking for examples of people using the output of another common sensor that measures air mass flowing into the intake for calculations of boost pressure since that sensor was available to me via the ISO connection. I eventually found what I was looking for in a tutorial employing the ideal gas law I learned about in high school duly modified to account for the flow of mass and volume rather than discrete quantities. Further explanation can be found in [SETUP.md](./doc/SETUP.md) although suffice it to say if the expression $PV̇=ṅRT$ makes one’s eyes glaze over they’re unlikely to find it interesting.

##### Some of the topics I had a chance to familiarize myself with throughout the course of this project, in no particular order:
1. C++
1. OpenCV
1. Python built-in libraries
1. The GIL and parallelism in Python
1. Inheritence and Python project organization
1. Automation in linux using `systemd` services
1. Linux graphics processing

<style></style>

### Future Development Goals

1. ~~Multiprocessing parallel execution!~~ ✓
1. Smoothing upscale with ML using coral TPU
1. Compute module 4 with custom HaT for power conversion and camera/sensor input
1. nvme drive for cable cleanup and easy access
1. Custom PCB to consolidate power, digitization, OBD connection, and wiring
1. Implement backup battery with smart charging and fail-safe BMS
1. ML object detection support to minimize power and storage use in sentry mode

### Contribution Guidelines

This project is wildly application specific but I welcome any feedback or suggestions you might have! If you were inspired to build your own similar system I would love hear from you as well!

Image source: https://wall.alphacoders.com/big.php?i=474466
[![y u no load 4rings](./assets/pi_files/IMG_5046.PNG)](https://parts.audiusa.com/)
[![python image failed to load](./assets/doc/python.png)](https://www.python.org/)
[![opencv image failed to load](./assets/doc/opencv.png)](https://opencv.org/)