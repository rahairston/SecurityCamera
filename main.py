from general import get_exec_dir, has_internet_connectivity
from picamera2 import Picamera2
from libcamera import controls, Transform
from streamer import Streamer
from recorder import Recorder
from encoder import Encoder
from storage import Storage
from ast import literal_eval
import threading
import datetime
import socket
import json
import time
import sys
import os
import cv2
import numpy as np

# Maximum amount of attempts to connect to the internet.
# Exit if this is exceeded.
MAX_INTERNET_CONNECT_ATTEMPTS = 100

def wait_for_internet():
    current_internet_connect_attempts = 0
    while not has_internet_connectivity():
        time.sleep(1)
        current_internet_connect_attempts += 1
        if current_internet_connect_attempts > 100:
            raise socket.error("No internet connection could be established "
                               "within the first {} seconds of running.".format(MAX_INTERNET_CONNECT_ATTEMPTS))

def tuple_from_resolution(res):
    return tuple(map(int, res.split("x")))

# Run if this script is run on its own.
if __name__ == '__main__':
    # Get the path of the configuration file.
    if len(sys.argv) >= 2:
        config_file_path = sys.argv[1]
    else:
        config_file_path = os.path.join(get_exec_dir(), 'config.json')

    # Exit if the configuration file doesn't exist.
    if not os.path.isfile(config_file_path):
        raise FileNotFoundError("The configuration file can't be found at {}. "
                                "Use 'python3 main.py <PATH_TO_CONFIG_FILE>' "
                                "to use a configuration file from a different directory.".format(config_file_path))

    # Get the configuration data from the config file.
    with open(config_file_path) as file:
        stored_data = json.loads(file.read())

    streamer_active = stored_data["streamer_active"]
    recorder_active = stored_data["recorder_active"]

    if not streamer_active and not recorder_active:
        raise Exception("Did you forget to enable the streamer and/or recorder in config.json?")

    camera_fps = stored_data["camera_fps"]
    camera_resolution = tuple_from_resolution(stored_data["camera_resolution"])
    detection_resolution = tuple_from_resolution(stored_data['detection_resolution'])
    camera_vFlip = stored_data['camera_vFlip']
    camera_HFlip = stored_data['camera_hFlip']
    camera_denoise = stored_data['camera_denoise']
    annotate_time = stored_data['annotate_time']

    # Create and configure the camera.
    camera = Picamera2()
    video_config = camera.create_video_configuration(
        main={"size": camera_resolution, "format": "RGB888"},lores={"size": detection_resolution, "format": "YUV420"},
        transform=Transform(hflip=camera_HFlip, vflip=camera_vFlip)
    )
    camera.configure(video_config)

    # Annotate the current date and time in the recording.
    if annotate_time:
        colour = (0, 255, 0, 255)
        origin = (0, 30)
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1
        thickness = 2
    #     camera.configure(camera.create_preview_configuration())
        camera.start_preview()
        overlay = np.zeros((640, 480, 4), dtype=np.uint8)
        camera.set_overlay(overlay)

        def annotate_time():
            while True:
                time_left = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cv2.putText(overlay, str(time_left), origin, font, scale, colour, thickness)
                time.sleep(1)

        threading.Thread(target=annotate_time).start()

    record_seconds_before_motion = stored_data["record_seconds_before_motion"]

    encoder = Encoder(camera_fps=camera_fps, 
        recorder_active=recorder_active, 
        record_seconds_before_motion=record_seconds_before_motion, 
        streamer_active=streamer_active)

    camera.encoders = encoder.encoder
    camera.start()
    camera.start_encoder()

    # Start the recorder.
    if recorder_active:
        motion_threshold = stored_data["detector_motion_threshold"]
        recordings_output_path = stored_data['local_recordings_output_path']
        temporary_recordings_output_path = stored_data['temporary_local_recordings_output_path']
        ffmpeg_path = stored_data['ffmpeg_path']
        record_seconds_after_motion = stored_data['record_seconds_after_motion']
        max_recording_seconds = stored_data['max_recording_seconds']
        storage_option = stored_data['storage_option']
        max_local_storage_capacity = stored_data['max_local_storage_capacity']

        convert_h264_to_mp4 = stored_data['convert_h264_to_mp4']

        if storage_option != 'local':
            wait_for_internet()

        storage = Storage(storage_option=storage_option,
                          max_local_storage_capacity=max_local_storage_capacity,
                          recordings_output_path=recordings_output_path,
                          )

        recorder = Recorder(camera=camera,
                            storage=storage,
                            temporary_recordings_output_path=temporary_recordings_output_path,
                            record_seconds_after_motion=record_seconds_after_motion,
                            max_recording_seconds=max_recording_seconds,
                            record_seconds_before_motion=record_seconds_before_motion,
                            ffmpeg_path=ffmpeg_path,
                            convert_h264_to_mp4=convert_h264_to_mp4,
                            recorder_output=encoder.recorder_output)

        recorder.start()

        threading.Thread(target=recorder.detect_motion).start()
        if not streamer_active:
            while True:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    camera.stop_recording()
                    camera.close()

    # Start the streamer.
    if streamer_active:
        wait_for_internet()
        stream_resolution = tuple_from_resolution(stored_data["stream_resolution"])
        streamer = Streamer(camera=camera,
                            streaming_resolution=stream_resolution,
                            fps=camera_fps,
                            streamer_output=encoder.streamer_output)
        streamer.start()
