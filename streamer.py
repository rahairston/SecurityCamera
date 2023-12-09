#!/usr/bin/python3

import socket
import threading
from picamera2.outputs import FileOutput

# Class that is responsible for streaming the camera footage to the web-page.
class Streamer:
    def __init__(self, camera, streamer_output, port=8000):
        self.camera = camera
        self.streamer_output=streamer_output
        self.port = port
   
    # Start streaming.
    def start(self):
        try:
            # Create the stream and detection buffers.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", 10001))
                sock.listen()
                while tup := sock.accept():
                    event = threading.Event()
                    conn, addr = tup
                    stream = conn.makefile("wb")
                    self.streamer_output.fileoutput = stream 
                    self.streamer_output.start()
                    self.streamer_output.connectiondead = lambda _: event.set()  # noqa
                    event.wait()
        except KeyboardInterrupt:
            self.camera.close()
