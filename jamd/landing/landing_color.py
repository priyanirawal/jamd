import cv2
import numpy as np
from PIL import Image

def get_limits(color):
    c = np.uint8([[color]])  # BGR values
    hsvC = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
    hue = hsvC[0][0][0]

    if hue >= 165:
        lowerLimit = np.array([hue - 10, 100, 100], dtype=np.uint8)
        upperLimit = np.array([180, 255, 255], dtype=np.uint8)
    elif hue <= 15:
        lowerLimit = np.array([0, 100, 100], dtype=np.uint8)
        upperLimit = np.array([hue + 10, 255, 255], dtype=np.uint8)
    else:
        lowerLimit = np.array([hue - 10, 100, 100], dtype=np.uint8)
        upperLimit = np.array([hue + 10, 255, 255], dtype=np.uint8)

    return lowerLimit, upperLimit

# --- Settings ---
landing_color = [255, 255, 0]  # Cyan pad in BGR
frame_width, frame_height = 640, 480
tolerance = 30  # How close to center before triggering descent

# --- Init ---
cap = cv2.VideoCapture(0)
cap.set(3, frame_width)
cap.set(4, frame_height)

while True:
    ret, frame = cap.read()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower, upper = get_limits(landing_color)

    mask = cv2.inRange(hsv, lower, upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    cx, cy = None, None

    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        if area > 500:  # Minimum size to consider
            x, y, w, h = cv2.boundingRect(largest)
            cx = x + w // 2
            cy = y + h // 2
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # --- Landing Logic ---
            offset_x = cx - frame_width // 2
            offset_y = cy - frame_height // 2

            print(f"Offset: X={offset_x}, Y={offset_y}")

            if abs(offset_x) < tolerance and abs(offset_y) < tolerance:
                print("Centered. Ready to descend")
                # send_land_command()  ← Replace with actual MAVLink/DroneKit command
            else:
                print("Adjusting position...")
                # send_velocity_command(offset_x, offset_y)

    cv2.line(frame, (frame_width//2, 0), (frame_width//2, frame_height), (255, 255, 255), 1)
    cv2.line(frame, (0, frame_height//2), (frame_width, frame_height//2), (255, 255, 255), 1)

    cv2.imshow("Autonomous Landing View", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
