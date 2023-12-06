from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import cv2

# Class that handles the detection of motion in the live camera feed.
class Detector:
    def __init__(self, camera, recorder):
        self.camera = camera
        self.recorder = recorder
        # The motion threshold. Higher number = less detection.
        self.encoder = recorder.encoder

    # Start the detector.
    def start(self):
        # Start recording to the detection buffer.
        self.camera.start()
        # Let the user know that the detector started successfully.
        print("Motion detector started successfully!")

    # Calculates the difference between previous_frame and current_frame.
    # Reports motion to the recorder if the difference exceeds the threshold.
    def detect_motion(self):
        w, h = self.camera.video_configuration["lores"]["size"]
        prev = None
        encoding = False
        ltime = 0

        while True:
            cur = self.camera.capture_buffer("lores")
            cur = cur[:w * h].reshape(h, w)
            if prev is not None:
                # Measure pixels differences between current and
                # previous frame
                mse = np.square(np.subtract(cur, prev)).mean()
                if mse > 7:
                    encoding = True
                    self.recorder.report_motion()
                    print("New Motion", mse)
            prev = cur
