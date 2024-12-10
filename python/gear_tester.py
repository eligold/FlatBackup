import traceback
from obd import OBD, OBDCommand
from obd.utils import bytes_to_int
from obd.protocols import ECU

elm = None
portstr= "/dev/ttyS0" # "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"
def _gear(messages):
    """ decoder for gear select """
    return bytes_to_int(messages[0].data[2:]) / 1000.0
gear_command = OBDCommand("GEAR","Gear Select",b"01A4",4,_gear,ECU.ENGINE,False)
if __name__ == "__main__":
    try:
        elm = OBD(portstr)
        print(elm.query(gear_command,force=True))
    except: traceback.print_exc()
    if elm is not None: elm.close()
