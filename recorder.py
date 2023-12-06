from picamera2 import Picamera2
from picamera2.outputs import CircularOutput
from picamera2.encoders import H264Encoder
from general import get_exec_dir
import subprocess
import threading
import datetime
import time
import os


# Class that handles the recording.
class Recorder:
    def __init__(self, camera, storage, camera_fps,
                 temporary_recordings_output_path="./temp_recordings/",
                 record_seconds_after_motion=12, max_recording_seconds=600,
                 record_seconds_before_motion=5, ffmpeg_path="/usr/bin/ffmpeg", convert_h264_to_mp4=True):
        self.camera = camera
        self.storage = storage
        self.temporary_recordings_output_path = temporary_recordings_output_path
        self.record_seconds_after_motion = record_seconds_after_motion
        self.max_recording_seconds = max_recording_seconds
        self.timer = 0
        self.record_seconds_before_motion = record_seconds_before_motion
        self.ffmpeg_path = ffmpeg_path
        self.convert_h264_to_mp4 = convert_h264_to_mp4
        self.encoder = H264Encoder(1000000, repeat=True, framerate=camera_fps)

        # Make sure CircularOutput contains at least 20 seconds of footage. Since this is the minimum for it work.
        if record_seconds_before_motion > 20:
            delayed_storage_length_seconds = record_seconds_before_motion
        else:
            delayed_storage_length_seconds = 20
        # Create the delayed frames stream.
        buffersize = delayed_storage_length_seconds * camera.controls.FrameRate[0]
        filename = os.path.join(get_exec_dir(), self.temporary_recordings_output_path, "temp.h264")
        self.delayed_recording_stream = CircularOutput(buffersize=int(buffersize), file=filename)
        self.encoder.output = [self.delayed_recording_stream]
        self.camera.encoders = self.encoder
        self.camera.start_encoder()

    # Method to call when there is motion.
    # This will start the recording if it hadn't already been started.
    # Extend the recording if the recording has already started.
    def report_motion(self):
        if self.timer == 0:
            self.timer = self.record_seconds_after_motion
            self._start_recording()
        else:
            self.timer = self.record_seconds_after_motion

    # Starts the recording.
    def _start_recording(self):
        # Create the filename and path.
        current_time_string = str(datetime.datetime.now())[11:13] + "-" + str(datetime.datetime.now())[14:16] \
                              + '-' + str(datetime.datetime.now())[17:19]
        if not os.path.isdir(os.path.join(get_exec_dir(), self.temporary_recordings_output_path)):
            os.mkdir(os.path.join(get_exec_dir(), self.temporary_recordings_output_path))
        output_file_name = os.path.join(get_exec_dir(), self.temporary_recordings_output_path, current_time_string)
        print('Started recording '+output_file_name)
        circ.fileoutput = output_file_name
        self.delayed_recording_stream.start()

        threading.Thread(target=self._start_countdown, args=(output_file_name), daemon=True).start()

    # Starts counting down from record_seconds_after_movement after movement is detected.
    # Stop recording if the timer gets to 0.
    def _start_countdown(self, output_file_name):
        self.timer = self.record_seconds_after_motion
        recorded_time = 0
        while self.timer > 0 and not recorded_time > self.max_recording_seconds:
            time.sleep(1)
            recorded_time += 1
            self.timer -= 1

        # Stop the delayed stream
        self.delayed_recording_stream.stop()
        # Put the h264 recording into an mp4 container.
        if self.convert_h264_to_mp4:
            output_file_name = self._put_in_mp4_container(output_file_name)
        # Store the recording in the right place.
        self.storage.store(output_file_name)

    # Put the h264 recording into an mp4 container.
    def _put_in_mp4_container(self, file_path):
        output_file_path = file_path.replace("h264", "mp4")
        # ffmpeg -i "before.h264" -c:v copy -f mp4 "myOutputFile.mp4"
        subprocess.call(['{}'.format(self.ffmpeg_path), '-i', '{}'.format(file_path), '-c:v', 'copy',
                         '-f', 'mp4', '{}'.format(output_file_path)], stdin=subprocess.PIPE)
        # Remove h264 file
        try:
            os.remove(file_path)
        except Exception as e:
            print(e)
        return output_file_path