# SETUP
Project details can be found in the [Readme](./README.md)

[visit this page for helpful references](./REFERENCE.md)

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
