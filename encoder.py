from picamera2.outputs import CircularOutput, FfmpegOutput
from picamera2.encoders import H264Encoder
from general import WebSocketHandler, get_exec_dir, get_file_content
from threading import Condition
import io

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

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