# SETUP
Project details can be found in the [Readme](./README.md)
[visit this page for helpful references](./REFERENCE.md)

The connection to the pi is facilitated by setting my phone hotspot credentials to reflect those saved in the `wpa_supplicant.conf` file as defined when flashing new SD card images using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). It is also possible to use plain old wifi or even a UART connection, instructions for which are outside the scope of this document.

1. flash buster or bullseye with pi imager, add login/wifi details
1. Use `sudo` to login as root
    ```
    sudo su -
    ```
1. With `raspi-config` I changed the system locale from en-GB UTF8 to en-US UTF8, and set the keyboard to an American layout.
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
1. To automate mounting the external drive I added this line to `/etc/fstab`. I like to use `vim` but you can use `nano` if you're not an elite hacker:
    ```
    LABEL=[label] /[mount/location/] [fs type] nofail      0       0
    ```
1. To start the program in a screen instance at boot, add the following to `/etc/rc.local` before the `exit 0` statement:
    ```
    screen -d -m /root/carCam.py
    ```
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
    apt install -y python3-opencv python3-pip python3-gpiozero fim git
    pip3 install obd
    ssh-keygen -t ed25519
    git clone git@github.com:eligold/FlatBackup.git
    ```
1. Copy the new systemctl services `splashscreen.service` and `bluetooth_connect.service` from `assets/pi_files/` to 
1. Install a new service to show the splashscreen at boot. Make sure to copy the image to the root directory. `vim /etc/systemctl/system/splashscreen.service` opens an editor to create the service. Press the `i` key and type the following lines:
    ```
    [Unit]
    Description=custom splash screen
    DefaultDependencies=no
    After=local-fs.target
    Requires=local-fs.target

    [Service]
    ExecStart=/usr/bin/fim -d /dev/fb0 -q /root/splash_img.png 
    StandardInput=tty
    StandardOutput=tty

    [Install]
    WantedBy=sysinit.target
    ```
    Hit `esc` and type `:` followed by `wq` and mash that `enter` key to write the service file. A quick `systemctl enable splashscreen` and `systemctl start splashscreen` are all that remains to register and, well, "start" the service. To confirm everything is set correctly run `systemctl status splashscreen` and bask in the radiant output of the daemon preparing your custom splashscreen image at boot.