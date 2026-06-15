import os
from django.conf import settings

try:
    import cv2
    import imutils
    import numpy as np
    from imutils.video import VideoStream
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    from tensorflow.keras.preprocessing.image import img_to_array
    from tensorflow.keras.models import load_model

    prototxtPath = os.path.sep.join([str(settings.BASE_DIR), 'models', 'face_detector', 'deploy.prototxt'])
    weightsPath = os.path.sep.join([str(settings.BASE_DIR), 'models', 'face_detector', 'res10_300x300_ssd_iter_140000.caffemodel'])
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)
    maskNet = load_model(os.path.join(str(settings.BASE_DIR), 'models', 'face_detector', 'mask_detector.model'))
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    imutils = None
    np = None
    VideoStream = None
    preprocess_input = None
    img_to_array = None
    load_model = None
    faceNet = None
    maskNet = None
    CV2_AVAILABLE = False

HAS_MASK = False
CAMERA_FAILED = False

def gen(camera, session=None):
    global HAS_MASK
    while True:
        frame, HAS_MASK = camera.get_frame(session)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        import time
        time.sleep(0.03)

class MaskDetect:
    def __init__(self):
        global CAMERA_FAILED
        self.vs = None
        if not CV2_AVAILABLE:
            CAMERA_FAILED = True
            return
            
        try:
            self.vs = VideoStream(src=0).start()
            # Try to read a frame to confirm it works
            import time
            time.sleep(0.5) # Give camera time to warm up
            frame = self.vs.read()
            if frame is None:
                CAMERA_FAILED = True
        except Exception:
            CAMERA_FAILED = True

    def __del__(self):
        if self.vs:
            try:
                self.vs.stop()
            except Exception:
                pass
        if cv2:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

    def detect_and_predict_mask(self, frame, faceNet, maskNet):
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))

        faceNet.setInput(blob)
        detections = faceNet.forward()

        faces = []
        locs = []
        preds = []

        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                (startX, startY) = (max(0, startX), max(0, startY))
                (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

                face = frame[startY:endY, startX:endX]
                face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
                face = cv2.resize(face, (224, 224))
                face = img_to_array(face)
                face = preprocess_input(face)

                faces.append(face)
                locs.append((startX, startY, endX, endY))

        if len(faces) > 0:
            faces = np.array(faces, dtype="float32")
            preds = maskNet.predict(faces, batch_size=32)

        return (locs, preds)

    def get_frame(self, session=None):
        global CAMERA_FAILED, HAS_MASK
        
        if CAMERA_FAILED or self.vs is None:
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('phase_2', sim_dict)
            sim_has_mask = sim_dict.get('sim_has_mask', False)
            return frame_bytes, sim_has_mask

        try:
            frame = self.vs.read()
            if frame is None:
                raise Exception("Failed to read frame")
                
            frame = imutils.resize(frame, width=650)
            frame = cv2.flip(frame, 1)
            (locs, preds) = self.detect_and_predict_mask(frame, faceNet, maskNet)

            has_mask = False
            for (box, pred) in zip(locs, preds):
                (startX, startY, endX, endY) = box
                (mask, withoutMask) = pred

                has_mask = bool(mask > withoutMask)
                label = "Mask" if mask > withoutMask else "No Mask"
                color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

                label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

                cv2.putText(frame, label, (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
                cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
                
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                raise Exception("Encoding failed")
            return jpeg.tobytes(), has_mask
            
        except Exception:
            CAMERA_FAILED = True
            from ai_evm.simulator import get_simulated_frame
            sim_dict = dict(session) if session else {}
            frame_bytes = get_simulated_frame('phase_2', sim_dict)
            sim_has_mask = sim_dict.get('sim_has_mask', False)
            return frame_bytes, sim_has_mask
