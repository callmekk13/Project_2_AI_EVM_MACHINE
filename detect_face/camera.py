import os
from django.conf import settings

try:
    import cv2
    import numpy as np
    face_detection_videocam = cv2.CascadeClassifier(
        os.path.join(str(settings.BASE_DIR),
            'models', 'opencv_haarcascade_data', 'haarcascade_frontalface_default.xml')
    )
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    face_detection_videocam = None
    CV2_AVAILABLE = False

FACES_COUNT = 0
CAMERA_FAILED = False

def gen(camera, session=None):
    global FACES_COUNT
    while True:
        frame, FACES_COUNT = camera.get_frame(session)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        import time
        time.sleep(0.03)


class VideoCamera:
    def __init__(self):
        global CAMERA_FAILED
        self.video = None
        if not CV2_AVAILABLE:
            CAMERA_FAILED = True
            return
            
        try:
            self.video = cv2.VideoCapture(0)
            if not self.video.isOpened():
                CAMERA_FAILED = True
        except Exception:
            CAMERA_FAILED = True

    def __del__(self):
        if self.video:
            try:
                self.video.release()
            except Exception:
                pass

    def get_frame(self, session=None):
        global CAMERA_FAILED, FACES_COUNT
        
        if CAMERA_FAILED or self.video is None or not CV2_AVAILABLE:
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('detect_face', sim_dict)
            return frame_bytes, 1

        try:
            success, image = self.video.read()
            if not success or image is None:
                raise Exception("Failed to read frame")
                
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces_detected = face_detection_videocam.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
            for (x, y, w, h) in faces_detected:
                cv2.rectangle(image, pt1=(x, y), pt2=(x + w, y + h), color=(255, 0, 0), thickness=2)
            frame_flip = cv2.flip(image, 1)
            ret_enc, jpeg = cv2.imencode('.jpg', frame_flip)
            if not ret_enc:
                raise Exception("Encoding failed")
            return jpeg.tobytes(), len(faces_detected)
            
        except Exception:
            CAMERA_FAILED = True
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('detect_face', sim_dict)
            return frame_bytes, 1
