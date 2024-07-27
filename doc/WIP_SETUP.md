# SETUP
Project details can be found in the [Readme](../README.md)

[visit this page for helpful references](./REFERENCE.md)

## Project Components

#### > Touchscreen and Raspberry Pi

My solution runs on a Raspberry Pi, serving as the central hub for image correction and OBDII data processing. Python scripts handle the integration of these components with multi-threaded processing to promote seamless operation. In order to maximize the useable regions of the undistorted image this project required an extra wide screen and luckily I found a screen on amazon that provided the optimal aspect ratio and even integrated support for mounting the Pi directly to it. This exact screen is no longer available but  is nearly identical and there are [many](https://www.amazon.com/ElecLab-Touchscreen-Capacitive-1280x480-10-3-inch-hdmi-1280x480/dp/B0BWSSKDV4/ref=sr_1_2) [other](https://www.amazon.com/gp/product/B09SVDCSQJ/ref=ox_sc_act_title_2) [options](https://www.amazon.com/ElecLab-Raspberry-Touchscreen-Capacitive-1280x400/dp/B09YJ37SBH/ref=sr_1_3) to choose from depending on your application. Touch input was the last piece of the puzzle, and after a failed attempt to implement it in pure python using the `async` library I instead opted to pipe the output of the shell command `evtest` through the `Popen` construct of the `Subprocess` python module to a queue that is handled in the main thread.

#### > OEM Camera Fisheye Image Correction

Utilizing the power of OpenCV and Python, I've implemented built-in undistortion algorithms to correct fisheye lens-distorted images captured with the replacement OEM backup camera. A digitizer facilitates analog video conversion enabling real-time processing on the Raspberry Pi for display in a more natural perspective.
`threading`, `queue`s, and `c++` oh my
__FIXME__
Between the regular undistortion method and the fisheye submodule verison, the latter seemed to suit my backup camera lens better with testing. Through some trial and error with a small helper script crafted to generate a set of baseline calibration images, a fairly consistent and replicable list of numbers was produced by the module's undistortion method. This list is used to create a matrix for reconstructing the raw image in a flattened perspective. The calibration script became more complicated yet more precise as additional tutorials and documentation for the fisheye submodule of OpenCV were reviewed.


#### > Camera Selection
Initially the goal was a low-effort, surreptitious aftermarket camera to pair with a cheap flip-up screen I got from ebay. The available solutions broadly fell into three categories: Cameras that install in holes drilled through the sheet metal, cameras that mount to a license plate bracket, and attempts to copy OEM solutions or shoehorn a camera into another part like a license plate light. Intending to keep this car in good condition for as long as possible I made every effort to avoid the first option, and since I find plate brackets garish the third option was what I initially moved forward with. The light replacements were dim and finicky with a poor quality camera so I tried out a module that replaces the handle to open the rear hatch with a smaller one that includes a mounted camera. I found the image quality satisfactory although the field of view was much too narrow. I picked out a couple of the general purpose cameras intended for mounting under an overhang and jerry-rigged them in place of the original camera from the aftermarket latch module. The only camera with a nice enough lens and sensor had annoyingly bright and distracting distance lines superimposed over the image and no means to turn them off which some of the other models offered. The mounting holes also didn't quite line up resulting in a small opening between the camera body and the latch compromising the weatherproofing of the hatch. I had initially dismissed the possibility of looking for an OEM part since I don't think the 8P generation A3 was even offered with a backup camera, however after exhausting the third party solutions it occured to me to look again at Audi parts. Basically every other vehicle in Audi's lineup is nicer than mine so I figured if any of their cars were equipped with the same bracket mounting the hatch lever and plate lights as my own there'd be a decent chance a similar part with a camera mount existed. As it happens the A6 and Q7 from that time were both designed to use the same component and of course both of those were offered with a backup camera. I found one on ebay, installed it, ran my wires, turned on the screen and...

...the distortion is pretty wild. I'm guessing whatever head unit that is installed natively with the camera in an A6 or a Q7 is doing a bit of post-processing under the hood because it is genuinely hard to look at. I've edited it out in these images but most of the rear license plate can be read in the uncropped original. At the time I thought about the possibility of using a Raspberry Pi and OpenCV but the poor mounting solution for the existing screen and no immediately apparent way to seamlessly mount the Pi it seemed like nothing more than a pipedream.


#### > OBDII Data Integration

An extraordinarily wide screen proved to be the most practical way to display the useful viewing area of the undistorted image however after tweaking the final layout some unused space remained to one side. I decided to use this space for displaying the boost pressure from the car's turbocharger. There are a number of ways to measure boost pressure in a forced induction car though most of them require invasive modifications that can compromise the weatherproofing of the interior. Rather than adding an air hose for a mechanical guage or running a wire through the heat shield to the engine bay I opted to use the built in sensors from the factory. The output of these sensors can be accessed through the OBDII port with an ELM327 USB adapter thanks to some handy code from [brendan-w](https://github.com/brendan-w/) with this [python-OBD project](https://github.com/brendan-w/python-OBD/).

My car comes with a Manifold Absolute Pressure (MAP) sensor but Audi in their infinite wisdom decided not to break out values from reading that particular sensor via the standard OBD protocol. Not to worry; using only the total engine displacement volume, the RPM, readings from the Intake Air Temperature (IAT) sensor, and readings from the Mass Air Flow (MAF) sensor combined with some fancy high school math the boost pressure can be calculated within a reasonable margin of error:

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

The most convenient place to tap power consisted of a cable run from a janky splitter in the dash fuse panel across the steering wheel.

<img src="./assets/doc/hatch_mess.png" alt="torn apart hatch image failed to load" width="75%">
<br>

 __a heatsink with fan to keep things cool. A Meanwell DC/DC converter steps the car voltage down to 5V__

__FIXME__
Wiring involved removing the interior trim of the rear hatch and running wires along the existing harnesses. I tried pushing a stiff wire through the factory wiring harness channel that runs between the hatch and the body of the vehicle but I settled on running the power and video connections externally before it occurred to me to try vacuuming a piece of twine thru the tight channel with which to pull cables through. I'll try that if I ever have occaision to take the hatch trim apart again There exists a channel for routing the factory harness from the roof through a hose protecting them from the elements. The hose was too tight to push a stiff wire through so the power and video cables run out of the trim and through the cabin in a way that is noticeable but unobtrusive. 
<br>although I wasn't able to get the wires through the weatherproof articulated tube in which the stock harnesses are run and I ended up taking out more inner body panels off than I should have. Getting everything back together necessitated pulling all the rest of the trim panels from the trunk before reinstalling everything properly. If I were to go back and do it again I would try to vacuum a string through the existing wire tube to pull my cables with. The Fakra system is essentially an easily removable shell around an SMB connector, which is a small RF connector similar to BNC or SMA but with no retention features.

 As it is a small loop of wires exits the top of the hatch with enough slack to reach the headliner trim while the hatch is fully open. It is visible but unobtrusive and proper cable management helps keep it from moving much while driving.
__picture of progress, picture of final wire arrangement__

I connected the 12V power supply in-line with harness wires for the trunk 12V accesory plug using some high current waterproof connectors I had on hand keeping nearly the entire wire run out of the cabin. I left a small loop with a pair of connectors running through some vent slots in the side panel as a quick disconnect in case any work needs to be done with the wiring down the line. With the trim removed I also took the oppotunity to wire up some high power Philips LEDs on custom-made aluminum PCBs to replace the pathetically dim single incandescent bulb that used to illuminate my trunk. As you might imagine from the below image, I don't think I'll have much trouble finding anything back there ever again.
<img src="./assets/doc/hatch_light_inset.png" alt="trunk light image failed to load" width="57%">

A recently purchased [Clearmounts phone adapter](https://www.audiphoneholder.com/product/78/clearmounts-bracket-low-profile-magnetic-holder-part-8p-low), pictured below, serves to conveniently and robustly secure my homebrew solution between the two centermost vents on my dashboard. After removing the simple magnetic holder that came with it I installed an articulated Scosche handsfree wireless charging mount similar to one that previously mounted to my windshield with a suction cup. I realized this model would be unsuitable for adapting to my project only after disassembling it completely so I purchased the articulated vent-mount model, securing a length of scrap aluminum angle extrusion to the back with the ball joint retaining screw through the Clearmounts adapter. Using a small L-bracket and some fastening hardware I mounted a second length of extrusion with holes drilled out to match the mounting pattern of my new widescreen display. It's practical but I'd like to replace it with something a bit more attractive down the line, perhaps in the vein of the beautiful custom devices built by [DIY Perks on YouTube](https://www.youtube.com/c/diyperks).

<img src="./assets/doc/clearmounts.png" alt="clearmounts image failed to load" width="50%">

Fast forward many months of annoyance with the warped image and my screen toppling over every time an inattentive driver would cut me off (in VA it's weird when people drive well), I was browsing amazon when I happened upon the perfect screen for the image layout I had in mind with included mounting hardware for the Pi. For only \$60 I realized I had run out of excuses not to try my hand with this OpenCV business. I figured it would be a quick and easy project however as I was working on the core functionality other ideas kept occuring to me and the project sort of snowballed from there. On top of an undistorted backup camera viewer the project now also implements touch input for control, records dashcam footage from an additionally installed camera to an external flash drive, and some visual tweaks just for me. Using a \$15 cable I'm able to pipeline diagnostic data from the car's ECU via the OBD port to continuously calculate and display instantaneous air intake pressure, a metric that means nothing to most people but for which car enthusiasts will pay hundreds of dollars and perform potentially destructive modifications to visualize. I've even run the car's stereo auxiliary connection to the Pi and scripted an automatic connection to my phone so my music switches over from a headset to playing on the car speakers automatically.

With some experimentation and more than a little frustration I figured out how to write directly to the SoC's frame buffer so I could display images on screen without the `imshow` method using a headless system. For a while the images were crazy disco colors until I converted them from OpenCV's native 24-bit BGR format to 16-bit BGR565. There are a number of tutorials online for both conventional and fisheye undistortion using the API, though many target C++ developers rather than python and required a bit of interpretation and some creative debugging to get working. I repeated my results a few times after determining that the fisheye model better suited my camera's lens, improving iteratively on the calibration method as I got more comfortable with how the library is structured though my results varied little from the original output.

The original script ran with very stuttery video and an alarmingly low frame rate so I tried to optimize what I could although reducing the size of the images being processed and switching from floating point to fixed point arithmetic did very little as the OpenCV code is already well optimized C++ under the hood. The largest impact on timing was switching from opening the frame buffer as a file to memory mapping it with `numpy`'s `memmap` funciton though in a sequential execution construct it was still a drop in the bucket. Knowing the bulk of the time was wrapped up in IO operation I initially considered the `asyncio` library but I couldn't get all the components of the project working together despite working individually in my dev setup and lacking the patience to continue debugging that route I switched over to using the python `Threading` library instead. Although I would have to rewrite the code once again to implement `multiprocessing` if I truly want my program to benefit from the multi-core architecure of the ARM CPU, `Threading` appears to handle the low-level OS scheduling well enough to approach the framerate of the unmodified camera image stream while performing image manipulations on each frame.

Bluetooth autoconnect was a tough nut to crack because no matter what method I tried, be it `systemd` or a setup step in my python script the phone would briefly connect before immediately disconnecting again much to my chagrin. After chasing my tail with some creative extra steps meant to pad the connection timing and the switch to `systemd` I discovered while debugging my own service with `journalctl` that another service linked to the system bringing the bluetooth radio online at startup was also directing it to naively power cycle itself after five seconds of operation. Those are a bunch of hours of my life I'll never get back but at least I learned not to assume something isn't working due to my own incompetence. An additional entry in the system `fstab` file mounts the external drive for the dashcam and a custom `systemd` service displays the Audi logo in place of the boring Raspberry Pi splash screen when booting up the Pi and the script will automatically shut off the wifi for power saving unless I connect my phone's hotspot during startup. Touching the top of the sidebar in my final image display layout will superimpose a graph of the calculated boost pressure over time and the bottom half will stop the program and shut down the Pi.

The connection to the pi is facilitated by setting my phone hotspot credentials to reflect those saved in the `wpa_supplicant.conf` file as defined when flashing new SD card images using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). It is also possible to use plain old wifi or even a UART connection, instructions for which are outside the scope of this document.

1. flash buster or bullseye with pi imager, add login/wifi details
1. Use `sudo` to login as root
    ```
    sudo su
    ```
1. With `raspi-config` change the system locale from en-GB UTF8 to en-US UTF8, and set the keyboard to an American layout.
1. Turn off swap file to spare the SD card from repeated writes and trim some fat by disabling Modem Manager
    ```
    dphys-swapfile swapoff
    systemctl disable dphys-swapfile.service
    systemctl disable ModemManager.service
    apt autoremove -y modemmanager
    ```
1. Get some tools and make sure the system is up to date in the background so you can do other things
    ```
    apt install -y vim screen
    apt update && screen -d -m apt upgrade -y
    ```
1. use `select-editor` and `update-alternatives --config editor` to switch from `nano` to `vim`. I like to use `vim` but you can use `nano` if you're not an elite hacker :shrug:
1. To automate mounting the external drive I added this line to `/etc/fstab`:
    `PARTLABEL=[label] /[mount/location/] [fs type] nofail      0       0`
1. To start the program in a screen instance at boot, add the following to `/etc/rc.local` before the `exit 0` statement:
    `screen -d -m /root/carCam.py`
1. Add the following lines to `config.txt`:
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
1. By default `\etc\cmdline.txt` will look something like this:
    `console=serial0,115200 console=tty1 root=PARTUUID=[xxxxxxxx]-0[n] rootfstype=ext4 fsck.repair=yes rootwait quiet splash plymouth.ignore-serial-consoles`
    After `rootwait` add `logo.nologo` to turn off the pi icon at boot, and `consoleblank=0` to shut off screen blanking and keep the display on. replace `splash` with `vt.global_cursor_default=0` for no blinky cursor and turn off default rainbow splash screen.
1. Install dependencies:
    ```
    apt install -y python3-opencv python3-pip python3-gpiozero python3-scipy fim git pulseaudio-module-bluetooth bluez-tools
    pip3 install obd
    ssh-keygen -t ed25519 # public key ~/.ssh/id_ed25519.pub must be added to github account manually
    git clone git@github.com:eligold/FlatBackup.git
    ```
1. Use `bluetoothctl` to scan for bluetooth devices. Make sure the phone is on and discoverable. Commands are preceded by a `#`, output from bluetootchtl is also shown below:
    ```
    root@{hostname}:~# bluetoothctl
    Agent registered
    [CHG] Controller 11:22:33:44:55:66 Pairable: yes
    [bluetooth]# discoverable on
    Changing discoverable on succeeded
    [bluetooth]# scan on
    Discovery started
    [CHG] Controller 11:22:33:44:55:66 Discovering: yes
    [NEW] Device AA:BB:CC:DD:EE:FF {phone name}
    [NEW] Device FF:EE:DD:CC:BB:AA FF-EE-DD-CC-BB-AA
    ...
    [NEW] Dev...
    ```
    At this point the console will spew out inforation about all broadcasting bluetooth devices in range. When the name of the phone appears next to it's address in the list, turn of the scan. Type the first one or two hex digits in the address and hit `tab` to autocomplete. Follow any onscreen prompts for the device and the pi when pairing, for example confirming a code displayed on the phone screen:
    ```
    [bluetooth]# scan off
    [bluetooth]# pair aa:bb:cc:dd:ee:ff
    [CHG] Device AA:BB:CC:DD:EE:FF Connected: yes
    [CHG] Device AA:BB:CC:DD:EE:FF Modalias: bluetooth:{some alphanumeric string}
    [CHG] Device AA:BB:CC:DD:EE:FF UUIDs: 00001000-0000-1000-8000-00805f9b34fb
    ...
    [CHG] Device AA:BB:CC:DD:EE:FF UUIDs: 00001801-0000-1000-8000-00805f9b34fb
    [CHG] Device AA:BB:CC:DD:EE:FF ServicesResolved: yes
    [CHG] Device AA:BB:CC:DD:EE:FF Paired: yes
    Pairing successful
    [CHG] Device AA:BB:CC:DD:EE:FF ServicesResolved: no
    [CHG] Device AA:BB:CC:DD:EE:FF Connected: no
    [bluetooth]# trust aa:bb:cc:dd:ee:ff
    [bluetooth]# exit
    ```
1. Create a new file to store the MAC address of your phone for automatically connecting to it later. Be sure to use your actual address and not the stand-in below. Make it readable to the root user only with `chmod`:
    ```
    echo aa:bb:cc:dd:ee:ff > /root/.btmac
    chmod 600 !$
    ```
1. Run `` bluetoothctl trust `cat /root/.btmac` `` to ensure a smooth connection with the phone
1. __JUST COPY IT__ With`vim` edit `/etc/bluetooth/main.conf` to uncomment and modify the following lines as below:
    ```
    [...]
    Class=0x408
    [...]
    AlwaysPairable=true
    [...]
    ```
    Hit `esc` and type `:` followed by `wq` and mash that `enter` key to write the file and exit.
1. To override the default commands used while bringing up the bluetooth interface and squash some pesky errors in the output status, use `systemctl edit bluetooth.service`. The default command includes the `-C` flag for improved compatibility __is this better or worse???__ These changes will disregard drivers needed to load bluetooth profile information from a SIM card. Since there is no SIM card in the pi and it causes an annoying and angrily red error message in the status log it just seems superfluous. Follow the onscreen instructions and enter the below lines between the comments specified. Changing or vacating a command requires clearing it with this syntax:
    ```
    ExecStart=
    ExecStart=/usr/libexec/bluetooth/bluetoothd --noplugin=sap,avrcp
    ExecStartPost=
    ```
1. Copy the `splashscreen.service` from `assets/pi_files/` to `/etc/systemd/system/`
    ```
    cp /assets/pi_files/splashscreen.service /etc/systemd/system/
    ```

1. Run `systemctl daemon-reload` before enabling the splash screen with:
    `systemctl enable splashscreen`

1. Copy the necessary files over from the repo to the root directory:
    ```
    cp /home/lando/FlatBackup/python/{ImageConstants,OBDData,ELM327,carCam}.py /root/
    cp /home/lando/FlatBackup/python/{splashscreen,newSidebar}.png /root/
    ```
1. Hit `ctrl + d` to exit the root shell. Replace `~/.profile` with our version by running the following command:
    ```cp assets/pi_files/dot.profile ~/.profile```
1. Copy the `bluetooth-connect.service` from `assets/pi_files/` to `/etc/systemd/user/`
1. Run `systemctl --user enable pulseaudio bluetooth-connect` to enable an audio endpoint for the bluetooth connection

1. --bt-agent.service--ExecStartPost=
