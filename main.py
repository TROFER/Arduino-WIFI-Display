#!/usr/bin/env python

"""Main.py - Example Interface Script"""

__author__ = "Tristan Day"
__version__ = "0.1"

import time
import urllib.request
from xml.etree import ElementTree

from PIL import Image, ImageFont

from driver import Display, Renderer


class Main(Renderer):
    def __init__(self) -> None:

        display = Display("Arduino Remote IP", 4300)

        self._template = Image.open(r"./Resource/Template.png")
        self._fonts = {
            "Large": ImageFont.truetype(
                r"./Resource/Yagora.ttf",
                size=20,
            ),
            "Medium": ImageFont.truetype(
                r"./Resource/Yagora.ttf",
                size=18,
            ),
        }
        self._icons = {
            "temperature": Image.open(r"./Resource/Temperature.png")
        }

        self._icons["temperature"].thumbnail(
            (25, 100), resample=Image.ANTIALIAS
        )

        self._weather = Weather()

        super().__init__(1, display, template=self._template)

    def draw(self, frame, canvas) -> None:
        canvas.text(
            (20, 38),
            time.strftime("%H:%M"),
            font=self._fonts["Large"],
            anchor="lm",
            fill=(255, 255, 255),
        )

        # Temperate Guage

        frame.alpha_composite(self._icons["temperature"], dest=(87, 52))

        canvas.text(
            (116, 58),
            str(round(float(self._weather.temperature()))),
            font=self._fonts["Medium"],
            anchor="lm",
            fill=(255, 255, 255),
        )

        canvas.text(
            (138, 58),
            "°C",
            font=self._fonts["Medium"],
            anchor="lm",
            fill=(245, 223, 70),
        )

    def show(self) -> None:
        self._display.begin()
        self.start()
        input("[INPUT] Press Enter to Kill")


class Weather:

    Interval = 300
    URL = r"http://www.isleofwightweather.com/rss.xml"

    def __init__(self) -> None:
        self._buffer = None
        self._lastcall = 0

    def temperature(self):
        self.get()
        return self._buffer[2].split(": ")[1][0:-2]

    def get(self):
        if time.time() - self._lastcall > 120:
            print("[INFO] Getting Weather Data")
            string = urllib.request.urlopen(self.URL).read()
            self._buffer = self._parse(string)
            self._lastcall = time.time()

    def _parse(self, string):
        return ElementTree.fromstring(string)[0][6][2].text.split(" | ")


if __name__ == "__main__":
    main = Main()
    main.show()
