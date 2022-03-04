import sys

sys.path.append("/home/pi/ArmPi")

import cv2
import Camera
import threading
from time import sleep

from LABConfig import *
from ArmIK.Transform import *
from ArmIK.ArmMoveIK import *
from CameraCalibration.CalibrationConfig import *
import HiwonderSDK.Board as Board

DEBUG = False

DEFAULT_COORDS = {
    "red": (-14.5, 11.5, 1.5),
    "green": (-14.5, 5.5, 1.5),
    "blue": (-14.5, -0.5, 1.5),
}


class StopError(Exception):
    """
    Dummy custom error to mark when arm must stop
    """

    pass


class BoxMover:
    def __init__(self, stop_event, coords=DEFAULT_COORDS):
        self.delay = 0.5
        self.stop_event = stop_event
        self.coords = DEFAULT_COORDS
        self.AK = ArmIK()
        self.x, self.y, self.z = 0, 0, 0
        self._init_move()

    def __del__(self):
        self.stop_event.set()

    def _check_stop(f):
        """
        Function wrapper that checks if the calling object
        (an instance of this class)'s stop_event is set,
        raising a StopError if so.
        This means we don't have to write "if not running"
        a million times, just decorate each func.

        AND, it really isn't necessary to call this on higher-level
        functions that only serve to call lower level ones,
        thus I only decorate the most commonly-used ones.
        """

        def wrapper(*args):
            # First arg is the calling object
            obj = args[0]

            # Ensure called on currect type of object
            assert isinstance(obj, BoxMover)

            if obj.stop_event.is_set():
                raise StopError("The stop flag has been raised!")
            else:
                if DEBUG:
                    print(f, args)
                    input()
                return f(*args)

        return wrapper

    @_check_stop
    def _move_arm(self, x, y, z, delay=None):
        """
        Exactly what it says on the label. Return True on success.
        """
        self.x, self.y, self.z = x, y, z  # keep track of current position

        # Set pitch as close to -90 as possible
        ret = self.AK.setPitchRangeMoving((x, y, z), -90, -90, 0, 1500)
        ret = ret is not False  # convert from *stuff/False to True/False

        sleep(self.delay if delay is None else delay)
        return ret

    @_check_stop
    def _set_gripper(self, val_str, delay=None):
        """
        Open or close the gripper (servo 1) based on
        val_str
        """
        assert isinstance(val_str, str)
        if val_str.lower() in ("open", "opened"):
            Board.setBusServoPulse(1, 300, 500)
        elif val_str.lower() in ("close", "closed"):
            Board.setBusServoPulse(1, 500, 500)
        else:
            raise ValueError

        sleep(self.delay if delay is None else delay)

    @_check_stop
    def _set_wrist(self, x, y, theta, delay=None):
        """
        Calculate the wrist angle necessary to
        orient a box to the 2D angle theta at
        spot x,y on the plane
        """
        servo2_angle = getAngle(x, y, theta)
        Board.setBusServoPulse(2, servo2_angle, 500)

        sleep(self.delay if delay is None else delay)

    def _init_move(self):
        self._set_gripper("open")
        self._set_wrist(0, 10, 0)
        return self._move_arm(0, 10, 12)

    def _raise_arm(self, z=12):
        return self._move_arm(self.x, self.y, z)

    def _lower_arm(self, z=2):
        return self._move_arm(self.x, self.y, z)

    def grab_box(self, x, y, theta):
        """
        Move to box at x, y with 2D orientation theta,
        then pick up
        """
        self._raise_arm()
        self._set_gripper("open")
        self._set_wrist(x, y, theta)
        self._move_arm(x, y, self.z)
        self._lower_arm()
        self._set_gripper("closed")
        self._raise_arm()

    def place_box(self, color):
        """
        Assumes box is already in hand. Color is string "red",
        "blue", or "green". Place at corresponding coordinates.
        """
        x, y, z = self.coords[color]
        theta = -90

        self._set_wrist(x, y, theta)
        self._move_arm(x, y, self.z)
        self._lower_arm(z + 3)  # move just above target
        self._lower_arm(z)  # then place
        self._set_gripper("open")
        self._raise_arm()

    def stop_override(self):
        """
        To be called after stop event is set, forcefully moves
        arm to a reset position without checking event
        """
        # Open gripper, reset wrist
        Board.setBusServoPulse(1, 300, 500)
        Board.setBusServoPulse(2, 500, 500)

        # Lift up
        self.AK.setPitchRangeMoving((self.x, self.y, self.x), -90, -90, 0)


if __name__ == "__main__":
    stop_event = threading.Event()
    mover = BoxMover(stop_event)

    # Dummy coord to test with
    mover.coords.update({"red": (-10, -10, 1.5)})

    try:
        mover.grab_box(10, 10, -45)
        mover.place_box("red")

        # Demo the stop event (albeit synchronously)
        # TODO: set up proper threaded loop for moving
        mover.grab_box(10, -10, -30)
        stop_event.set()
        mover.place_box("blue")
    except KeyboardInterrupt:
        print("Ending by user.")
    except StopError:
        print("Stopping!")

