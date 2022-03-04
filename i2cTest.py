from MoveImproved import BoxMover
from ArmIK.Transform import convertCoordinate

from smbus import SMBus
import time
import threading

ADDRESS = 0x08

def main():
    in_range = [40, 80]
    out_range = [0, 640]

    stop_event = threading.Event()
    mover = BoxMover(stop_event)

    i2cbus = SMBus(1)

    while True:
        in_val = i2cbus.read_i2c_block_data(ADDRESS,0)[0]
        out_val = range_to_range(in_val, in_range, out_range)

        print(f'{in_val} --> {out_val}')

        x, y = convertCoordinate(out_val, 240, (640, 480))

        mover._move_arm(x, y, 10)
        time.sleep(0.2)

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
