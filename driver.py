#!/usr/bin/env python

"""Driver.py: A Python Display Driver for an ESP32 WIFI Display."""

__author__ = "Tristan Day"
__version__ = "0.2"

import multiprocessing
import queue
import socket
import time

from PIL import Image, ImageDraw


def subsample(colour) -> str:
    """Converts 24-bit colour tuple to a 16-bit hex value"""

    red_u8 = "{0:08b}".format(colour[0])
    green_u8 = "{0:08b}".format(colour[1])
    blue_u8 = "{0:08b}".format(colour[2])

    channels = (
        bin(int(red_u8, base=2) >> 3).replace("0b", "").zfill(5),
        bin(int(green_u8, base=2) >> 2).replace("0b", "").zfill(6),
        bin(int(blue_u8, base=2) >> 3).replace("0b", "").zfill(5),
    )

    return hex(int("".join(channels), base=2)).replace("0x", "")


class Display:

    VERBOSE = False

    WIDTH = 160
    HEIGHT = 80

    PIPE_TIMEOUT = 0.1  # In Secconds
    MAX_FRAME_TIME = 0.1  # In Secconds
    REFRESH_RATE = 50  # Updates Per Seccond In Hertz
    MAX_BLOCK_SIZE = 200  # Pixels Per Upload

    def __init__(self, ip: str, port: int) -> None:
        self._ip = ip
        self._port = port

        self.buffer = multiprocessing.Queue(maxsize=1)
        self._cache = ["" for pixel in range(Display.WIDTH * Display.HEIGHT)]
        self._pipe = multiprocessing.Queue()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._flag = False

    def _push_updates(self) -> None:
        while not self._flag:
            try:
                timestamp = time.process_time()
                block = []
                while (
                    time.process_time() - timestamp < Display.MAX_FRAME_TIME
                    and len(block) < Display.MAX_BLOCK_SIZE
                ):
                    block.append(self._pipe.get(timeout=Display.PIPE_TIMEOUT))

            except queue.Empty:
                if Display.VERBOSE:
                    print("[WARNING] Pipe Underflow Detected")

            finally:
                self._sock.sendto(
                    bytes("#".join(block), "ASCII"),
                    (self._ip, self._port),
                )
                time.sleep(1 / Display.REFRESH_RATE)

    def _scan_frames(self) -> None:
        while not self._flag:
            similarity = 0
            frame = self.buffer.get()

            for index, value in enumerate(zip(self._cache, frame)):
                if value[0] != value[1]:
                    self._pipe.put(
                        "{}.{}.{}".format(
                            hex(index % Display.WIDTH),
                            hex(index // Display.WIDTH),
                            value[1],
                        ).replace("0x", "")
                    )
                    self._cache[index] = frame[index]
                else:
                    similarity += 1

            if Display.VERBOSE:
                print(
                    round(
                        (similarity / (Display.WIDTH * Display.HEIGHT)) * 100,
                        2,
                    ),
                    "%",
                )

    def begin(self) -> None:
        multiprocessing.Process(target=self._push_updates, daemon=True).start()
        multiprocessing.Process(target=self._scan_frames, daemon=True).start()
        if Display.VERBOSE:
            print("[INFO] Verbose Enabled")
            print("[INFO] Display Driver Started")

    def stop(self) -> None:
        self._flag = False


class Renderer:

    DOWNSCALE_METHOD = Image.BOX

    def __init__(
        self, framerate: int, display: Display, template: Image = None
    ) -> None:
        self._min_frametime = 1 / framerate
        self._display = display

        if template is None:
            self._frame_template = Image.new(
                mode="RGBA", size=(self._display.WIDTH, self._display.HEIGHT)
            )
        else:
            self._frame_template = template.resize(
                (Display.WIDTH, Display.HEIGHT),
                resample=Renderer.DOWNSCALE_METHOD,
            )

        self._flag = False

    def _render(self) -> None:
        while not self._flag:
            timestamp = time.process_time()

            frame = self._frame_template.copy()
            canvas = ImageDraw.Draw(frame)
            self.draw(frame, canvas)
            self._display.buffer.put(self._convert(frame))

            if time.process_time() - timestamp < self._min_frametime:
                time.sleep(1 - (time.process_time() - timestamp))

    def _convert(self, frame) -> list:
        return [subsample(pixel) for pixel in list(frame.getdata())]

    def draw(self, canvas) -> None:
        """Override in Subclass"""
        pass

    def start(self) -> None:
        multiprocessing.Process(target=self._render, daemon=True).start()
