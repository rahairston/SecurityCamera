from picamera2.outputs import CircularOutput, FfmpegOutput
from picamera2.encoders import H264Encoder
from general import WebSocketHandler, get_exec_dir, get_file_content
from threading import Condition
import io

class StreamingOutput(io.BufferedIOBase):
    def __init__(self, camera):
        self.frame = None
        self.condition = Condition()
        self.loop = None
        self.buffer = io.BytesIO()
        self.camera = camera

    def write(self, buf):
        with self.condition:
            # self.frame = buf
            # self.condition.notify_all()
            # if self.camera.frames.complete and self.camera.frames.frame_type != 2:
            self.buffer.write(buf)
            frame = self.buffer.getvalue()
            if self.loop is not None and WebSocketHandler.hasConnections():
                self.loop.add_callback(callback=WebSocketHandler.broadcast, message=frame)

            self.buffer.seek(0)
            self.buffer.truncate()

    def setLoop(self, loop):
        self.loop = loop

class Encoder:
    def __init__(self, camera, camera_fps, recorder_active, record_seconds_before_motion, streamer_active):

        self.encoder = H264Encoder(1000000, repeat=True, iperiod=camera_fps, framerate=camera_fps, enable_sps_framerate=True)
        outputs = []
        if recorder_active:
            buffersize = record_seconds_before_motion * camera_fps
            self.recorder_output = CircularOutput(buffersize=int(buffersize))
            outputs.append(self.recorder_output)
        
        if streamer_active:
            self.streamer_output = FfmpegOutput("-f hls -hls_time 4 -hls_list_size 5 -hls_flags delete_segments -hls_allow_cache 0 stream.m3u8")
            outputs.append(self.streamer_output)

        self.encoder.output = outputs