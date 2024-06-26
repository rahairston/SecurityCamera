from picamera2 import Picamera2
from general import get_exec_dir
import subprocess
import threading
import datetime
import time
import os
import numpy as np

# Class that handles the recording.
class Recorder:
    def __init__(self, camera, storage, recorder_output,
                 temporary_recordings_output_path="./temp_recordings/",
                 motion_threshold = 7,
                 record_seconds_after_motion=12, max_recording_seconds=600, 
                 ffmpeg_path="/usr/bin/ffmpeg", convert_h264_to_mp4=True):
        self.camera = camera
        self.storage = storage
        self.temporary_recordings_output_path = temporary_recordings_output_path
        self.record_seconds_after_motion = record_seconds_after_motion
        self.max_recording_seconds = max_recording_seconds
        self.timer = 0
        self.motion_threshold = motion_threshold
        self.ffmpeg_path = ffmpeg_path
        self.convert_h264_to_mp4 = convert_h264_to_mp4

        # Create the pre-motion buffer.
        self.delayed_recording_stream = recorder_output

    def detect_motion(self):
        print("Motion Detection Started...")
        w, h = self.camera.video_configuration.lores.size
        prev = None
        while True:
            cur = self.camera.capture_buffer("lores")
            cur = cur[:w * h].reshape(h, w)
            if prev is not None:
                # Measure pixels differences between current and
                # previous frame
                mse = np.square(np.subtract(cur, prev)).mean()
                if mse > self.motion_threshold:
                    print("New Motion", mse)
                    self.report_motion()
            prev = cur

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
        output_file_name = os.path.join(get_exec_dir(), self.temporary_recordings_output_path, current_time_string) + ".h264"
        self.delayed_recording_stream.fileoutput = output_file_name
        self.delayed_recording_stream.start()
        print('Started recording '+output_file_name)
        threading.Thread(target=self._start_countdown, args=(output_file_name,), daemon=True).start()

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