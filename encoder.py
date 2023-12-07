from picamera2.outputs import CircularOutput, FileOutput
from picamera2.encoders import H264Encoder
from general import WebSocketHandler, get_exec_dir, get_file_content
from threading import Condition
import io

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self.loop = None
        self.buffer = io.BytesIO()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
            if self.camera.frame.complete and self.camera.frame.frame_type != 2:
                self.buffer.write(buf)
                frame = self.buffer.getvalue()
                if self.loop is not None and WebSocketHandler.hasConnections():
                    self.loop.add_callback(callback=WebSocketHandler.broadcast, message=frame)

                self.buffer.seek(0)
                self.buffer.truncate()
            else:
                self.buffer.write(buf)

    def setLoop(self, loop):
        self.loop = loop

class Encoder:
    def __init__(self, camera_fps, recorder_active, record_seconds_before_motion, streamer_active):

        self.encoder = H264Encoder(1000000, repeat=True, iperiod=camera_fps, framerate=camera_fps, enable_sps_framerate=True)
        outputs = []
        if recorder_active:
            buffersize = record_seconds_before_motion * camera_fps
            self.recorder_output = CircularOutput(buffersize=int(buffersize))
            outputs.append(self.recorder_output)
        
        if streamer_active:
            self.streamer_output = FileOutput(StreamingOutput())
            outputs.append(self.streamer_output)

        self.encoder.output = outputs