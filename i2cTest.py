import sys
sys.path.append('/home/pi/ArmPi')

from MoveImproved import BoxMover
from ArmIK.Transform import convertCoordinate
from RemoteController import RemoteController, JoystickController

from smbus import SMBus
import time
import threading

ADDRESS = 0x08

def main():
    in_range = [40, 80]
    out_range = [0, 640]

    stop_event = threading.Event()
    mover = BoxMover(stop_event)

#    i2cbus = SMBus(1)
#    rc = RemoteController()
    rc = JoystickController()
    rc.gain = 0.2
    rc.max_r = 35

    while True:
        (x, y, z), theta, grip = rc.read()

#        x, y = convertCoordinate(x, y, (640, 480))
#        x, y = convertCoordinate(320, 240, (640, 480))

        print(f'{x:.2f}, {y:.2f}, {z:.2f}, {int(theta)}, {grip}')
        mover._set_gripper('close' if grip else 'open')
        mover._set_wrist_manual(theta)
        ret = mover._move_arm(x, y, z)
        if ret is False:
            print('Bad position!')
            delay = 0.25
        else:
            delay = ret[2] / 2000.0
#        time.sleep(delay)

def range_to_range(val, range1, range2):
    d1 = range1[1] - range1[0]
    d2 = range2[1] - range2[0]

    m1 = (d1 / 2) + range1[0]
    m2 = (d2 / 2) + range2[0]

    in_value = (val - m1) / d1
    out_value = (in_value * d2) + m2
    return out_value

if __name__=="__main__":
    main()
