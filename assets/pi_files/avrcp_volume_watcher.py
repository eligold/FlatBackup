#!/usr/bin/env python3

import os
import sys
import logging
import logging.handlers
import signal
import dbus
import dbus.service
import dbus.mainloop.glib # maybe after below import?

try:
    import gobject
except ImportError:
    from gi.repository import GObject as gobject

LOG_NAME = 'avrcp-volume-watcher'
LOG_LEVEL = logging.INFO
#LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(name)s[%(process)d]: %(message)s'

# Increase VOLUME_MAX if you experience saturation issues. Standard value is 127
#VOLUME_MAX = 127
VOLUME_MAX = 141
#VOLUME_MAX = 159

def shutdown(signum, frame):
    mainloop.quit()

def pa_source_number(address):
    """ Returns the Pulseaudio source number matching bluetooth address

    Args:
        address(string) : bluetooth address formatted as AA:BB:CC:DD:EE:FF

    Returns:
        int: pulseaudio source number

    """

    stream = os.popen('pactl list short sources | grep bluez_source.{}'.format(address.replace(':', '_')))
    pulseaudio_source = stream.read()

    if pulseaudio_source == '':
        # Cannot find source in pulseaudio source list
        logger.debug(u'Cannot find pulseaudio A2DP source {}'.format(address))
        return

    # Pulseaudio source number is the first field in a \t seperated string
    pa_source_number = pulseaudio_source.split('\t')[0]
    logger.debug(u'Pulseaudio A2DP source {} is #{}'.format(address, pa_source_number))
    return pa_source_number

def pa_set_volume(address, volume):
    """ Set the volume of the pulseaudio source bound to the A2DP interface

    If A2DP interface is idle, pulseaudio source does not exist, do nothing

    Args:
        address(string) : bluetooth address formatted as AA:BB:CC:DD:EE:FF
        volume(int) : volume level 0-127

    """

    # Let's find the pulseaudio source matching address and set its volume
    pa_source = pa_source_number(address)
    if pa_source:
        logger.debug(u'Running pactl set-source-volume {} {}'.format(pa_source, format(float(volume) / VOLUME_MAX, '.2f')))
        os.system('pactl set-source-volume {} {}'.format(pa_source, format(float(volume) / VOLUME_MAX, '.2f')))
    else:
        logger.debug(u'Skipping volume change')

def device_property_changed(interface, properties, invalidated, path):
    """ Check for changes in org.bluez object tree

    Check for Volume change event and State = active event
    Retrieve the volume value and set pulseaudio source accordingly

    Args:
        interface(string) : name of the dbus interface where changes occured
        properties(dict) : list of all parameters changed and their new value
        invalidated(array) : list of properties invalidated
        path(string) : path of the dbus object that triggered the call
    """

    if interface == 'org.bluez.MediaTransport1':
        bus = dbus.SystemBus()
        mediatransport_object = bus.get_object('org.bluez', path)
        mediatransport_properties_interface = dbus.Interface(mediatransport_object, 'org.freedesktop.DBus.Properties')
        device_path = mediatransport_properties_interface.Get('org.bluez.MediaTransport1', 'Device')
        device_object = bus.get_object('org.bluez', device_path)
        device_properties_interface = dbus.Interface(device_object, 'org.freedesktop.DBus.Properties')
        name = device_properties_interface.Get('org.bluez.Device1', 'Name')
        address = device_properties_interface.Get('org.bluez.Device1', 'Address')
        if 'State' in properties:
            state = properties['State']
            logger.info(u'Bluetooth A2DP source: {} ({}) is now {}'.format(name, address, state))
            if state == 'active':
                codec =  mediatransport_properties_interface.Get('org.bluez.MediaTransport1', 'Codec')
                logger.debug(u'Bluetooth A2DP source: {} ({}) codec is {}'.format(name, address, int(codec)))
                volume = mediatransport_properties_interface.Get('org.bluez.MediaTransport1', 'Volume')
                logger.debug(u'Bluetooth A2DP source: {} ({}) volume is {}'.format(name, address, volume))
                pa_set_volume(address, volume)
        elif 'Volume' in properties:
            volume = properties['Volume']
            logger.debug(u'Bluetooth A2DP source: {} ({}) volume is now {}'.format(name, address, volume))
            pa_set_volume(address, volume)
        elif 'Codec' in properties:
            codec = properties['Codec']
            logger.debug(u'Bluetooth A2DP source: {} ({}) codec is {}'.format(name, address, int(codec)))


if __name__ == '__main__':

    # shut down on a TERM signal
    signal.signal(signal.SIGTERM, shutdown)

    # Create logger
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(LOG_LEVEL)

    # Choose between /var/log/syslog or current stdout
    ch = logging.handlers.SysLogHandler(address = '/dev/log')
#    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(fmt=LOG_FORMAT))
    logger.addHandler(ch)
    logger.info('Started')

    # Get the system bus
    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
    except Exception as ex:
        logger.error('Unable to get the system dbus: "{0}". Exiting. Is dbus running?'.format(ex.message))
        sys.exit(1)

    # listen for PropertyChanged signal on org.bluez
    bus.add_signal_receiver(
        device_property_changed,
        bus_name='org.bluez',
        signal_name='PropertiesChanged',
        dbus_interface='org.freedesktop.DBus.Properties',
        path_keyword='path'
        )

    try:
        mainloop = gobject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        logger.error('Unable to run the gobject main loop')
        sys.exit(1)

    logger.info('Shutting down')
    sys.exit(0)

