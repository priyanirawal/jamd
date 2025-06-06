import cv2
import numpy as np
from PIL import Image
from util import get_limits  # assumes it works with BGR input

cyan = [255, 255, 0]  # cyan in BGR
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    hsvImage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lowerLimit, upperLimit = get_limits(color=cyan)  # or manually set as below
    # lowerLimit = np.array([80, 100, 100])
    # upperLimit = np.array([100, 255, 255])

    mask = cv2.inRange(hsvImage, lowerLimit, upperLimit)
    mask_ = Image.fromarray(mask)
    bbox = mask_.getbbox()

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        frame = cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 5)

    cv2.imshow('frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
