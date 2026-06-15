import os
from django.conf import settings

try:
    import cv2
    import numpy as np
    prototxt = os.path.join(str(settings.BASE_DIR), 'models', 'MobileNetSSD', 'MobileNetSSD_deploy.prototxt')
    weights = os.path.join(str(settings.BASE_DIR), 'models', 'MobileNetSSD', 'MobileNetSSD_deploy.caffemodel')
    thr = 0.4
    classNames = {15: 'person'}
    net = cv2.dnn.readNetFromCaffe(prototxt, weights)
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    net = None
    classNames = {}
    thr = 0.4
    CV2_AVAILABLE = False

PERSON_COUNT = 0
CAMERA_FAILED = False

def gen(camera, session=None):
    global PERSON_COUNT
    while True:
        frame, PERSON_COUNT = camera.get_frame(session)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        # Tiny delay to limit CPU usage in the streaming loop
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
        global CAMERA_FAILED, PERSON_COUNT
        
        # If camera has failed or is unavailable, use the simulator
        if CAMERA_FAILED or self.video is None:
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('phase_1', sim_dict)
            sim_persons = int(sim_dict.get('sim_persons', 1))
            return frame_bytes, sim_persons

        try:
            ret, frame = self.video.read()
            if not ret or frame is None:
                raise Exception("Failed to read frame")
                
            frame_resized = cv2.resize(frame, (300, 300))
            blob = cv2.dnn.blobFromImage(frame_resized, 0.007843, (300, 300), (127.5, 127.5, 127.5), False)

            net.setInput(blob)
            detections = net.forward()

            cols = frame_resized.shape[1] 
            rows = frame_resized.shape[0]
            person = 0

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > thr:
                    class_id = int(detections[0, 0, i, 1])
                    if class_id == 15:
                        person += 1
                        
                        xLeftBottom = int(detections[0, 0, i, 3] * cols) 
                        yLeftBottom = int(detections[0, 0, i, 4] * rows)
                        xRightTop   = int(detections[0, 0, i, 5] * cols)
                        yRightTop   = int(detections[0, 0, i, 6] * rows)
                        
                        heightFactor = frame.shape[0]/300.0  
                        widthFactor = frame.shape[1]/300.0 

                        xLeftBottom = int(widthFactor * xLeftBottom) 
                        yLeftBottom = int(heightFactor * yLeftBottom)
                        xRightTop   = int(widthFactor * xRightTop)
                        yRightTop   = int(heightFactor * yRightTop)
            
                        cv2.rectangle(frame, (xLeftBottom, yLeftBottom), (xRightTop, yRightTop), (0, 255, 0), 2)
                        
            frame_flip = cv2.flip(frame, 1)
            ret_enc, jpeg = cv2.imencode('.jpg', frame_flip)
            if not ret_enc:
                raise Exception("Encoding failed")
            return jpeg.tobytes(), person
            
        except Exception:
            CAMERA_FAILED = True
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('phase_1', sim_dict)
            sim_persons = int(sim_dict.get('sim_persons', 1))
            return frame_bytes, sim_persons
