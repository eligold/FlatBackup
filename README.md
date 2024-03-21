<h1 align="center"> FlatBackup </h1>


<p align="center">
    <img src="./assets/doc/Raspberry_Pi_Logo.ico" alt="pi image failed to load"> <nbsp> <nbsp>
    <img src="./assets/doc/pythonlogo.png" alt="python image failed to load" width="71px" height="64px"> <nbsp> <nbsp>
    <img src="./assets/doc/opencvlogo.png" alt="opencv image failed to load" width="72px" height="64px">
</p>

<h2 align="center"> Fisheye Image Correction and <br>OBDII Boost Gauge <br></h2>



### Overview
What started as a simple effort to upgrade my 2013 Audi A3 with a backup camera quickly spiraled into a deep rabbit hole involving vision processing, creative use of non-standard OEM equipment, and an off the cuff design choice to visualize performance data. After a great deal of iterative design expansions and improvements it occured to me that the hodge-podge of hardware and wiring I've thrown together was quickly converging with a regular old tablet. While this repository is written in an instructional format I can't stress enough that I do not recommend anybody try to replicate it. Hopefully it can be educational for someone, I know I learned a whole lot along the way.

![flip screen image failed to load](./assets/doc/flipscreen.jpg)

Initially I simply wanted a low-effort, surreptitious aftermarket camera to pair with a cheap flip-up screen I got from ebay. The most convenient place to tap power consisted of a cable run from a janky splitter in the dash fuse panel across the steering wheel to where I had centered the screen which did nothing to hold it in place while driving. Apart from being unobtrusive my only real requirement for the camera was not needing to drill any new holes to wire it and options are limited. Since I don't think the 8P generation was offered with an OEM camera it only occured to me to look at Audi parts after exhausting the availble third party options for replacing a license plate light or the rear latch. Basically every other vehicle in Audi's lineup is nicer than mine so I figured if any of their cars were equipped with the same bracket mounting the hatch lever and plate lights as my own there'd be a decent chance a similar part with a camera mount existed. As it happens the A6 and Q7 from that time were both designed to use the same component and of course both of those were offered with a backup camera. I found one on ebay, installed it, ran my wires, turned on the screen and...

![Side by side image of undistortion failed to load!](./assets/doc/Side-by-side.png)

...the distortion is pretty wild. I'm guessing whatever head unit that is installed natively with the camera in an A6 or a Q7 is doing a bit of post-processing under the hood because it is genuinely hard to look at. I've edited it out in these images but most of the rear license plate can be read in the uncropped original. At the time I thought about the possibility of using a Raspberry Pi and OpenCV but the poor mounting solution for the existing screen and no immediately apparent way to seamlessly mount the Pi it seemed like nothing more than a pipedream.

Fast forward many months of annoyance with the warped image and my screen toppling over every time an inattentive driver would cut me off (in VA it's weird when people drive well), I was browsing amazon when I happened upon the perfect screen for the image layout I had in mind with included mounting hardware for the Pi. For only \$70 I realized I had run out of excuses not to try my hand with this OpenCV business. I figured it would be a quick and easy project however as I was working on the core functionality other ideas kept occuring to me and the project sort of snowballed from there. On top of an undistorted backup camera viewer the project now also implements touch input for control, records dashcam footage from an additionally installed camera to an external flash drive, and some visual tweaks just for me. Using a \$15 cable I'm able to pipeline diagnostic data from the car's ECU via the OBD port to continuously calculate and display instantaneous air intake pressure, a metric that means nothing to most people but for which car enthusiasts will pay hundreds of dollars and perform potentially destructive modifications to visualize. I've even run the car's stereo auxiliary connection to the Pi and scripted an automatic connection to my phone so my music switches over from a headset to playing on the car speakers automatically.

With some experimentation and more than a little frustration I figured out how to write directly to the SoC's frame buffer so I could display images on screen without the `imshow` method using a headless system. For a while the images were crazy disco colors until I converted them from OpenCV's native 24-bit BGR format to 16-bit BGR565. There are a number of tutorials online for both conventional and fisheye undistortion using the API, though many target C++ developers rather than python and required a bit of interpretation and some creative debugging to get working. I repeated my results a few times after determining that the fisheye model better suited my camera's lens, improving iteratively on the calibration method as I got more comfortable with how the library is structured though my results varied little from the original output.

The original script ran with very stuttery video and an alarmingly low frame rate so I tried to optimize what I could although reducing the size of the images being processed and switching from floating point to fixed point arithmetic did very little as the OpenCV code is already well optimized C++ under the hood. The largest impact on timing was switching from opening the frame buffer as a file to memory mapping it with `numpy`'s `memmap` funciton though in a sequential execution construct it was still a drop in the bucket. Knowing the bulk of the time was wrapped up in IO operation I initially considered the `asyncio` library but I couldn't get all the components of the project working together despite working individually in my dev setup and lacking the patience to continue debugging that route I switched over to using the python `Threading` library instead. Although I would have to rewrite the code once again to implement `multiprocessing` if I truly want my program to benefit from the multi-core architecure of the ARM CPU, `Threading` appears to handle the low-level OS scheduling well enough to approach the framerate of the unmodified camera image stream while performing image manipulations on each frame.

Bluetooth autoconnect was a tough nut to crack because no matter what method I tried, be it `systemd` or a setup step in my python script the phone would briefly connect before immediately disconnecting again much to my chagrin. After chasing my tail with some creative extra steps meant to pad the connection timing and the switch to `systemd` I discovered while debugging my own service with `journalctl` that another service linked to the system bringing the bluetooth radio online at startup was also directing it to naively power cycle itself after five seconds of operation. Those are a bunch of hours of my life I'll never get back but at least I learned not to assume something isn't working due to my own incompetence. An additional entry in the system `fstab` file mounts the external drive for the dashcam and a custom `systemd` service displays the Audi logo in place of the boring Raspberry Pi splash screen when booting up the Pi and the script will automatically shut off the wifi for power saving unless I connect my phone's hotspot during startup. Touching the top of the sidebar in my final image display layout will superimpose a graph of the calculated boost pressure over time and the bottom half will stop the program and shut down the Pi.

## Background
Opportunity to learn 
1. C++
1. OpenCV
1. python built-in libraries
1. explore inheritence and project organization
1. Automation using systemd services
1. Linux graphics processing

As much as I'd like to say I've done something groundbreaking with this project, after many hours of head-banging and frustration, testing, construction, basically everything I've done could be replicated with some custom code running on an android tablet and an off-the-shelf windshield mount. That being said I was able to use the experience to try out OpenCV and C++ for the first time and I learned a whole lot, mainly that I have much more to learn. This project started with my search for the best backup camera to retrofit onto my last-generation Audi A3. With no visually appealing universal options on the market several attempts were made to fashion custom low-profile solutions. Aftermarket replacements for the stock license plate light fixture as well as the latch actuator module for opening the rear hatch failed to live up to expectaions. More importantly they lacked the seamless integration of an OEM component. My later efforts involved grafting components together following the discovery of an exceptionally cheap but well made camera form factor. It was ruled out due to superimposed range lines that didn't have any obvious means of being turned off however if those don't bother you the camera is linked [here]()__CAMERA LINK__ I was pretty sure that 8P A3 wasn't offered with a backup camera but I didn't give up hope for a factory solution. The rear latch for the A3 is also used on the A6 and Q7, both of which had alternatives that came with a backup camera. After perusing eBay I found a used part that included the camera with both power and signal plug sets intact.
![seamless integration picture failed to load](./assets/doc/IMGrear.jpeg)

The output from my newly installed camera was initially displayed on a cheap flip up display from Amazon or eBay or wherever. It was somehow always too dim in the daytime and too bright at night and had an annoying habit of sliding around despite the thoughtful inclusion of a small square bit of drawer liner for use on the dashboard. I knew I would have to find a better long-term solution. With the distortion from the wide angle lens not much useful detail could be made out on the standard 4:3 ratio screen size and displaying the camera's view of my own license plate seems like kind of a waste of resources. Having already retrofitted my [Scoshe wireless charger](https://www.amazon.com/MCQVP-XTET-MagicMount-Magnetic-Qi-Certified-FreeFlow/dp/B07Z7CYRD2?th=1) and a more stable screen to my [Clearmounts dashboard bracket](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low), an idea began to take shape...


### Project Components

__link to setup__ [Setup](./SETUP.md)
#### > Touchscreen and Raspberry Pi
My solution runs on a Raspberry Pi, serving as the central hub for image correction and OBDII data processing. Python scripts handle the integration of these components with multi-threaded processing to promote seamless operation. In order to maximize the useable regions of the undistorted image this project required an extra wide screen and luckily I found a screen on amazon that provided the optimal aspect ratio and even integrated support for mounting the Pi directly to it. This exact screen is no longer available but [this unit from amazon](https://www.amazon.com/dp/B087CNJYB4/ref=sspa_dk_detail_0) is nearly identical and there are [many](https://www.amazon.com/ElecLab-Touchscreen-Capacitive-1280x480-10-3-inch-hdmi-1280x480/dp/B0BWSSKDV4/ref=sr_1_2) [other](https://www.amazon.com/gp/product/B09SVDCSQJ/ref=ox_sc_act_title_2) [options](https://www.amazon.com/ElecLab-Raspberry-Touchscreen-Capacitive-1280x400/dp/B09YJ37SBH/ref=sr_1_3) to choose from depending on your application. Touch input was the last piece of the puzzle, and after a failed attempt to implement it in pure python using the `async` library I instead opted to pipe the output of the shell command `evtest` through the `Popen` construct of the `Subprocess` python module to a queue that is handled in the main thread.
<img src="./assets/doc/pi.screen.jpg" alt="pi screen image failed to load">

#### > OEM Camera Fisheye Image Correction
Utilizing the power of OpenCV and Python, I've implemented built-in undistortion algorithms to correct fisheye lens-distorted images captured with the replacement OEM backup camera. 
__MORE PROCESS__
A [clone of the EasyCap USB A/V digitizer](https://www.ebay.com/itm/383709416325) facilitates analog video conversion enabling real-time processing on the Raspberry Pi for display in a more natural perspective. Between the regular undistortion method and the fisheye submodule verison, the latter seemed to suit my backup camera lens better with testing. Through some trial and error with a small helper script crafted to generate a set of baseline calibration images, a fairly consistent and replicable list of numbers was produced by the module's undistortion method. This list is used to create a matrix for reconstructing the raw image in a flattened perspective. The calibration script became more complicated yet more precise as additional tutorials and documentation for the fisheye submodule of OpenCV were reviewed.
__threading, 3 vs 4,__
<img src="./assets/doc/easycap.jpeg" alt="easycap image failed to load" width="38%" min-width="240px">

#### > OBDII Data Integration
An extraordinarily wide screen proved to be the most practical way to display the useful viewing area of the undistorted image however after tweaking the final layout some unused space remained to one side. I decided to use this space for displaying the boost pressure from the car's turbocharger. There are a number of ways to measure boost pressure in a forced induction car though most of them require invasive modifications that can compromise the weatherproofing of the interior. Rather than adding an air hose for a mechanical guage or running a wire through the heat shield to the engine bay I opted to use the built in sensors from the factory. The output of these sensors can be accessed through the OBDII port with an ELM327 USB adapter thanks to some handy code from [brendan-w](https://github.com/brendan-w/) with this [python-OBD project](https://github.com/brendan-w/python-OBD/).

My car comes with a Manifold Absolute Pressure (MAP) sensor but Audi in their infinite wisdom decided not to break out values from reading that particular sensor via the standard OBD protocol. Not to worry; using only the total engine displacement volume of 1984$cc$, the RPM, readings from the Intake Air Temperature (IAT) sensor, and readings from the Mass Air Flow (MAF) sensor combined with some fancy high school math the boost pressure can be calculated within a reasonable margin of error:

<p align="center">
    <img src="./assets/doc/eq_r2.png" alt="P x V̇ = ṅ x R x T [1]">
</p>

$$ P \times V̇ = ṅ \times R \times T^{[1]} $$

The above equation is derived from the ideal gas law $PV = nRT$ to relate the volumetric flow rate and molar mass flow rate of the intake air in order to calculate instantaneous boost pressure. All the necessary information is available through the OBDII connection to facilitate calculations as fast as the protocol can supply new data. Breaking down the terms:

1. $P$ is the instantaneous boost pressure we are calculating
1. $V̇$ is the volumetric flow rate of gas through the engine or 1984$cc$ for every two rotations of the crankshaft
1. $ṅ$ is the molar flow rate of air determined by dividing the MAF sensor output ($ṁ$) in $g \over s$ by the molar mass of air, 28.949 $g\over mol$
1. $R$ is the gas constant, helpfully provided by the `Unit` python library
1. $T$ is the absolute temperature read from the IAT sensor and converted to Kelvin

Rather than assume a constant atmospheric pressure the car's barometric pressure sensor (BPS) readings are subtracted from calculated absolute pressure to determine true boost pressure. If the result is negative that means the system is in vacuum and the reading is converted from $PSI$ to $bar$ since I don't really care as much about the magnitude. All of this is handled by the aptly named `Unit` python library.

#### > Wiring and Mounting
<img src="./assets/doc/Fakra.jpg" alt="fakra key chart failed to load" height="240px">
<img src="./assets/doc/fakraBNC.jpeg" alt="fakra bnc image failed to load" height="240px">

Video is carried through a Fakra antenna connector which come with many different key options. This is typically indicated by the housing color according to the internet and I spent much too long on a fruitless search for a high quality adapter specific to the key of the plug for the camera. A plethora of cheap options were forthcoming but the quality of the plug housings on most leave a lot to be desired and I don't look forward to repeating the interior trim disassembly to replace a broken plug. With a deeper dive through my references I realized that a universal "Z" key Fakra variation exists which works with most of the key options including our camera plug. High quality RF cables with custom terminations are typically expensive from reputable suppliers but [Amazon came to the rescue](https://a.co/d/6lxqHxw) with a mass-produced solution. The one from the link is no longer offered but I'm sure there are plenty of similar products available now. I used a small BNC to RCA adapter and slim RCA cable from [monoprice](https://www.monoprice.com/product?p_id=4127) although they no longer appear to offer the latter.

<img src="./assets/doc/hatch_mess.png" alt="torn apart hatch image failed to load" width="75%">
<br>

 __a heatsink with fan to keep things cool. A Meanwell DC/DC converter steps the car voltage down to 5V__

__FIXME__
Wiring involved removing the interior trim of the rear hatch and running wires along the existing harnesses. There exists a channel for routing the factory harness from the roof through a hose protecting them from the elements. The hose was too tight to push a stiff wire through so the power and video cables run out of the trim and through the cabin in a way that is noticeable but unobtrusive. 
<br>although I wasn't able to get the wires through the weatherproof articulated tube in which the stock harnesses are run and I ended up taking out more inner body panels off than I should have. Getting everything back together necessitated pulling all the rest of the trim panels from the trunk before reinstalling everything properly. If I were to go back and do it again I would try to vacuum a string through the existing wire tube to pull my cables with. The Fakra system is essentially an easily removable shell around an SMB connector, which is a small RF connector similar to BNC or SMA but with no retention features.

 As it is a small loop of wires exits the top of the hatch with enough slack to reach the headliner trim while the hatch is fully open. It is visible but unobtrusive and proper cable management helps keep it from moving much while driving.
__picture of progress, picture of final wire arrangement__

I connected the 12V power supply in-line with harness wires for the trunk 12V accesory plug using some high current waterproof connectors I had on hand keeping nearly the entire wire run out of the cabin. I left a small loop with a pair of connectors running through some vent slots in the side panel as a quick disconnect in case any work needs to be done with the wiring down the line. With the trim removed I also took the oppotunity to wire up some high power Philips LEDs on custom-made aluminum PCBs to replace the pathetically dim single incandescent bulb that used to illuminate my trunk. As you might imagine from the below image, I don't think I'll have much trouble finding anything back there ever again.
<img src="./assets/doc/hatch_light_inset.png" alt="trunk light image failed to load" width="57%">

A recently purchased [Clearmounts phone adapter](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low), pictured below, serves to conveniently and robustly secure my homebrew solution between the two centermost vents on my dashboard. After removing the simple magnetic holder that came with it I installed an articulated Scosche handsfree wireless charging mount similar to one that previously mounted to my windshield with a suction cup. I realized this model would be unsuitable for adapting to my project only after disassembling it completely so I purchased the articulated vent-mount model, securing a length of scrap aluminum angle extrusion to the back with the ball joint retaining screw through the Clearmounts adapter. Using a small L-bracket and some fastening hardware I mounted a second length of extrusion with holes drilled out to match the mounting pattern of my new widescreen display. It's practical but I'd like to replace it with something a bit more attractive down the line, perhaps in the vein of the beautiful custom devices built by [DIY Perks on YouTube](https://www.youtube.com/c/diyperks).

<img src="./assets/doc/clearmounts.png" alt="clearmounts image failed to load" width="50%">

## Future Development Goals

1. Async execution!
1. Smoothing upscale with ML using coral TPU
1. Pi 5, nvme drive for cable cleanup and easy access
1. Implement backup battery with smart charging and custom BMS
1. ML object detection support to minimize power and storage use in sentry mode

## Contribution Guidelines

This project is wildly application specific but I welcome any feedback or suggestions you might have! If you were inspired to build your own similar system I would love hear from you as well!

Image source: https://wall.alphacoders.com/big.php?i=474466
[![y u no load 4rings](./assets/pi_files/IMG_5046.PNG)](https://parts.audiusa.com/)
[![python image failed to load](./assets/doc/python.png)](https://www.python.org/)
[![opencv image failed to load](./assets/doc/opencv.png)](https://opencv.org/)