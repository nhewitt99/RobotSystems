import sys

sys.path.append("/home/pi/ArmPi")

import cv2
import time
import Camera
import threading

from LABConfig import *
from ArmIK.Transform import *
from ArmIK.ArmMoveIK import *
from CameraCalibration.CalibrationConfig import *
from HiwonderSDK.Board import Board

AK = ArmIK()

range_rgb = {
    "red": (0, 0, 255),
    "blue": (255, 0, 0),
    "green": (0, 255, 0),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
}


class Detector:
    def __init__(self):
        """
        TODO: there's all sorts of parameters in the various
        class methods that could (should) be accesssible on init
        """
        self.camera = Camera.Camera()
        self.camera.camera_open()

    def __del__(self):
        # Cleanup camera on delete
        self.camera.camera_close()

    def get_max_contour(self, mask, min_area=300):
        """
        Perform filtering for contour detection: open, close
        Then find the largest contour by area
        Input a mask of the desired color(s)
        Return the contour and its area, None if invalid
        """
        max_contour = None

        # Filtering
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((6, 6), np.uint8))
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((6, 6), np.uint8))
        contours = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[
            -2
        ]

        # Calculate area for each contour, find largest area
        def area(contour):
            return math.fabs(cv2.contourArea(contour))

        areas = list(map(area, contours))
        max_area = max(areas)

        # Only return contour if max > min
        if max_area > min_area:
            max_contour = contours(areas.index(max_area))

        return max_contour, max_area

    def get_color_contour(self, img_lab, target_colors):
        """
        Find the largest contour by area over all targeted colors,
        returns that contour, its color, and its area
        """
        largest_contour = None
        detected_color = None
        area_max = 0

        for i in color_range:  # color_range from LABConfig
            if i in target_colors:
                # Mask for this color in image
                color_mask = cv2.inRange(
                    img_lab, color_range[detect_color][0], color_range[detect_color][1]
                )

                # Update max
                contour, area = self.get_max_contour(color_mask)
                if contour is not None and area > area_max:
                    largest_contour = contour
                    detected_color = i
                    area_max = area

        return largest_contour, detected_color, area_max

    def get_center(self, contour, img_size=(640, 480)):
        """
        Return the center of a bounding box surrounding the contour,
        and the box itself for plotting later
        """
        rect = cv2.minAreaRect(contour)
        box = np.int0(cv2.boxPoints(rect))

        roi = getROI(box)  # from a * import
        img_x, img_y = getCenter(
            rect, roi, img_size, square_length
        )  # also from a * import
        world_x, world_y = convertCoordinate(img_x, img_y, img_size)  # * import

        return (world_x, world_y), box

    def detect_once(self, img, target_colors=("red",)):
        """
        Find center of largest color contour
        Return center, its area, its color, and the bounding box
        """
        img_lab = cv2.cv2Color(img, cv2.COLOR_BGR2LAB)
        contour, color, area = self.get_color_contour(img_lab, target_colors)

        if contour is None:
            return None, 0, None, None
        else:
            center, box = self.get_center(contour)
            return center, area, color, box

    def draw_detection(self, img, center, color, box):
        img = img.copy()
        img_h, img_w = img.shape[:2]

        # Draw cross over center of image
        cv2.line(img, (0, int(img_h / 2)), (img_w, int(img_h / 2)), (0, 0, 200), 1)
        cv2.line(img, (int(img_w / 2), 0), (int(img_w / 2), img_h), (0, 0, 200), 1)

        if box is not None:
            cv2.drawContours(img, [box], -1, range_rgb[color], 2)
            cv2.putText(
                img,
                f"({center[0]}, {center[1]})",
                (min(box[0, 0], box[2, 0]), box[2, 1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                range_rgb[color],
                1,
            )
        return img

    def tuple_distance(self, t1, t2):
        t11, t12 = t1
        t21, t22 = t2
        return math.sqrt((t21 - t11) ** 2 + (t22 - t12) ** 2)

    def try_detect(
        self,
        min_time=1.5,
        max_distance=0.3,
        min_area=2500,
        timeout=10,
        show=False,
        size=(640, 480),
    ):
        """
        Consolidate detections over multiple frames to "find" a colored box.
        Contours of the same color must be detected repeatedly over the
        interval of min_time, each with a center within max_distance of the previous,
        and only contours > min_area will be counted.
        If conditions not met by timeout seconds, throw TimeoutError.
        Draw details to cv2.show if show is True.
        Returns accumulated x and y on success
        """
        start_t = time.time()
        detect_t = None  # time of first detection
        centers = []
        saved_color = None

        while time.time() - start_t <= timeout:
            img = self.camera.frame
            if img is None:
                continue

            img = cv2.resize(img, size, interpolation=cv2.INTER_NEAREST)
            img = cv2.GaussianBlur(img, (11, 11), 11)

            # Try to detect a box
            center, area, color, box = self.detect_once(img)

            if show:
                frame = self.draw_detection(img, center, color, box)
                cv2.imshow("frame", frame)

            if center is None or area < min_area:
                continue

            # Find distance to previous center
            if len(centers) == 0:
                distance = 0
            else:
                distance = self.tuple_distance(center, centers[-1])

            # Reset if criteria not met
            if distance > max_distance or color != saved_color:
                centers = []
                saved_color = None
                detect_t = None
                continue

            # Append to centers, start detection timer if not yet
            if detect_t is None:
                detect_t = time.time()
                saved_color = color
            centers.append(center)

            # If successfully detected long enough, average and return
            if time.time() - detect_t > min_time:
                centers = np.array(centers)
                x, y = np.mean(centers, axis=0)
                return (x, y), color

        raise TimeoutError


if __name__ == "__main__":
    detector = BoxDetector()

    try:
        while True:
            try:
                (x, y), color = detector.try_detect()
                print(f"Successful detection of color {color} at {x},{y}")
            except TimeoutError:
                print("No detection for 10s")
    except KeyboardInterrupt:
        print("Ending.")

    cv2.destroyAllWindows()
