from general import WebSocketHandler
from picamera2 import Picamera2
import numpy as np
import cv2
import io


# Buffer for the live camera feed.
class StreamBuffer(object):
    def __init__(self, camera):
        self.camera = camera
        self.loop = None
        self.buffer = io.BytesIO()

    def setLoop(self, loop):
        self.loop = loop

    def write(self, buf):
        if self.camera.frame.complete and self.camera.frame.frame_type != 2:
            self.buffer.write(buf)
            frame = self.buffer.getvalue()
            if self.loop is not None and WebSocketHandler.hasConnections():
                self.loop.add_callback(callback=WebSocketHandler.broadcast, message=frame)

            self.buffer.seek(0)
            self.buffer.truncate()
        else:
            self.buffer.write(buf)