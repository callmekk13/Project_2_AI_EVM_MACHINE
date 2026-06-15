import os
import pickle
from django.conf import settings

try:
    import cv2
    import numpy as np
    import face_recognition
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    face_recognition = None
    CV2_AVAILABLE = False

models_dir = os.path.join(str(settings.BASE_DIR), 'models', 'recognize_face_models')
faces_encodings = []
faces_names = []

try:
    with open(os.path.join(models_dir, 'dataset_faces.dat'), 'rb') as f:
        faces_encodings = pickle.load(f)
    with open(os.path.join(models_dir, 'name_faces.dat'), 'rb') as f:
        faces_names = pickle.load(f)
except (FileNotFoundError, IOError, pickle.PickleError):
    faces_encodings = []
    faces_names = []

face_locations = []
face_encodings = []
face_names = []

FACE_NAME = 'Unknown'
CAMERA_FAILED = False

def gen(camera, session=None):
    global FACE_NAME
    while True:
        frame, FACE_NAME = camera.get_frame(session)
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
        global CAMERA_FAILED, FACE_NAME
        
        if CAMERA_FAILED or self.video is None or not CV2_AVAILABLE:
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('phase_3', sim_dict)
            sim_face_name = sim_dict.get('sim_face_name', 'Ankit')
            return frame_bytes, sim_face_name

        try:
            ret, frame = self.video.read()
            if not ret or frame is None:
                raise Exception("Failed to read frame")
                
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            face_names = []
            name = "Unknown"
            
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(faces_encodings, face_encoding)
                face_distances = face_recognition.face_distance(faces_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = faces_names[best_match_index]
                face_names.append(name)

            frame = cv2.flip(frame, 1)
            
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (0, 0, 0), 1)

            ret_enc, jpeg = cv2.imencode('.jpg', frame)
            if not ret_enc:
                raise Exception("Encoding failed")
            return jpeg.tobytes(), name
            
        except Exception:
            CAMERA_FAILED = True
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('phase_3', sim_dict)
            sim_face_name = sim_dict.get('sim_face_name', 'Ankit')
            return frame_bytes, sim_face_name
