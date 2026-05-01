import io
from pathlib import Path
from typing import Callable
import time
import math
import warnings
import psutil
import argparse
import yaml
import threading
from PIL import Image, ImageDraw, ImageFont, ImageOps
from liquidctl import find_liquidctl_devices
import pynvml
import matplotlib.pyplot as plt
import widgets



HEIGHT = 640
WIDTH = 640
RADIUS = 320

RAM_PATH = "/dev/shm/frame.png"


_FONT_CACHE = {}

def get_font(size=30):
    if size not in _FONT_CACHE:
        cwd = Path(__file__).parent
        _FONT_CACHE[size] = ImageFont.truetype(str(cwd / "fonts/Audiowide-Regular.ttf"), size)
    return _FONT_CACHE[size]

def to_px(x,y):
    """Converts (-1,1:1,1) axis coordinates to pixel coordinates."""
    return (
        int(RADIUS + x*RADIUS), 
        int(RADIUS - y*RADIUS)
    )


if 0:
    def rotated_rectangle(ax, ay, bx, by, angle_deg):
        angle_rad = 90 * angle_deg / math.pi
        #rotates point `A` about point `B` by `angle` radians clockwise.
        center = ((ax+bx)/2, (ay+by)/2)
        angle += math.atan2(ay-by, ax-bx)
        return (
            round(bx + radius * math.cos(angle)),
            round(by + radius * math.sin(angle))
        )


class Kraken():
    def __init__(self, debug = False):
        self.debug = debug
        if not debug:
            # Initialize device
            for dev in find_liquidctl_devices():
                if "Kraken" in dev.description:
                    try:
                        dev.connect()
                        dev.initialize()
                        self.device = dev
                    except Exception as e:
                        if "langid" in str(e) or "Access denied" in str(e):
                            print("Error: Permission denied. Please check your udev rules or run with sudo.")
                        else:
                            print(f"Error connecting to device: {e}")
        else:
            self._fig, self._ax = plt.subplots()
            # self.ax.remove()

        pynvml.nvmlInit()
        self._nv_handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        self._cpu_temp = 0
        self._gpu_temp = 0
        self._liq_temp = 0
        self._cpu_load = 0
        self._gpu_load = 0

        self._resolution = (WIDTH, HEIGHT)

        self._bg_image = None
        self._angle = 30
        self._fps = 1
        self._last_stats_update = 0
        self._last_tick = time.time()

        self.frame = Image.new('RGBA', self._resolution, color=(0, 0, 0, 255))
        self._bg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 255))  # black background
        self._fg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))  # transparent widget layer
        self.init_frame()


    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value: int):
        if 0 <= value <= 100:
            self._brightness = value
            if not self.debug:
                self.device.set_brightness(value)
        else:
            raise ValueError(f"Brightness must be between 0 and 100, not {value}")


    @property
    def bg_image(self):
        return self._bg_image

    @bg_image.setter
    def bg_image(self, value):
        if value and Path(value).exists():
            self._bg_image = Image.open(value)
        else:
            raise FileNotFoundError(value)


    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, value):
        if 1 <= value <= 30:
            self._fps = value
            if value > 20:
                warnings.warn("FPS > 20 might not be stable")
        else:
            raise ValueError("FPS must be between 1 and 30")


    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value

    @property
    def cpu_temp(self):
        temps = psutil.sensors_temperatures()
        if 'k10temp' in temps:
            return temps['k10temp'][0].current
        elif 'coretemp' in temps:
            return temps['coretemp'][0].current

    @property
    def cpu_load(self):
        return psutil.cpu_percent()

    @property
    def gpu_temp(self):
        return pynvml.nvmlDeviceGetTemperature(self._nv_handle, pynvml.NVML_TEMPERATURE_GPU)

    @property
    def gpu_load(self):
        return pynvml.nvmlDeviceGetUtilizationRates(self._nv_handle).gpu


    def init_frame(self):

        # Initialize widgets
        rect_width = int(1.09375 * RADIUS)  # 350 px
        line_width = int(0.0625 * RADIUS)   # 20 px
        arc_radius = int(0.28125 * RADIUS)  # 90 px
        font_path = str(Path(__file__).parent / "fonts/Audiowide-Regular.ttf")

        A = to_px(-0.5, 0.1)
        D = to_px(0.5, -0.1)

        self.widgets = {
            "cpu_temp_line": widgets.LineGraphic(rect_width, line_width, data_updater=lambda: self.cpu_temp),
            "cpu_load_arc": widgets.ArcGraphic(170, arc_radius, line_width, data_updater=lambda: self.cpu_load, rot=0),
            "cpu_temp_text": widgets.Text(lambda: f"{int(self.cpu_temp)}°C", font_path, 120),
            "gpu_temp_line": widgets.LineGraphic(rect_width, line_width, data_updater=lambda: self.gpu_temp, rot=180),
            "gpu_load_arc": widgets.ArcGraphic(170, arc_radius, line_width, data_updater=lambda: self.gpu_load, rot=180),
            "gpu_temp_text": widgets.Text(lambda: f"{int(self.gpu_temp)}°C", font_path, 120, align="right"),
        }

        # Define placement: (x, y) coordinates and which edge to align (offset from center)
        self.widget_configs = {
            "cpu_temp_line": (A[0], A[1], "left", 0),
            "cpu_load_arc":  (A[0], A[1] - arc_radius + line_width//2, "center", 0),
            "cpu_temp_text": (A[0], A[1] - arc_radius, "left", 0),
            "gpu_temp_line": (D[0] - rect_width, D[1], "left", 0),
            "gpu_load_arc":  (D[0], D[1] + arc_radius - line_width//2, "center", 0),
            "gpu_temp_text": (D[0], D[1] + arc_radius, "right", 0),
        }

        self._brightness = 50
        self.colors = {
            "debug": "#9A4CB8",
            "bg": (0, 0, 0, 255)  # black
        }

        if self._bg_image:
            scale = 1.22
            bg_w, bg_h = self._bg_image.size
            new_w, new_h = int(bg_w * scale), int(bg_h * scale)
            bg_resized = self._bg_image.resize((new_w, new_h))
            offset_y = int(-0.352 * RADIUS)
            self._bg.paste(bg_resized, (RADIUS - new_w // 2, RADIUS - new_h // 2 + offset_y))

        if self.debug:
            draw = ImageDraw.Draw(self._bg)
            draw.circle((WIDTH//2, HEIGHT//2), radius=RADIUS, outline=self.colors["debug"], width=10)

        for name, widget in self.widgets.items():
            widget.update()
            x, y, align, rot = self.widget_configs[name]

            # Adjust pasting position based on alignment
            w_w, w_h = widget.bg.size
            if align == "left":
                widget.pos = (x, y - w_h // 2)
            elif align == "right":
                widget.pos = (x - w_w, y - w_h // 2)
            else:  # center
                widget.pos = (x - w_w // 2, y - w_h // 2)

            self._bg.paste(widget.bg, widget.pos, widget.bg)
            if widget.fg:
                self._fg.paste(widget.fg, widget.pos, widget.fg)


    def update_frame(self):
        self._fg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))
        for name, widget in self.widgets.items():
            update_widget = widget.update()
            # if update_widget and widget.fg:
            draw = ImageDraw.Draw(self._fg)
            # draw.rectangle((*widget.pos, widget.pos[0]+widget.width, widget.pos[1]+widget.height), fill="#00000000", outline="red")
            self._fg.paste(widget.fg, widget.pos, widget.fg)

        self.frame = Image.alpha_composite(self._bg, self._fg)
        if not self.debug:
            self.frame = self.frame.rotate(self._angle, resample=Image.BICUBIC)


    def display(self):
        self.update_frame()

        with io.BytesIO() as buffer:
            self.frame.convert("RGB").save(buffer, format='BMP')
            # gif_frame = self._frame.convert("P", palette=Image.ADAPTIVE, colors=256)
            # gif_frame.save(buffer, format='GIF', save_all=True, append_images=[gif_frame], duration=500,loop=0)
            buffer.seek(0)

        # while True:
        if not self.debug:
                try:
                    self.device.set_screen('lcd', 'static', buffer)
                except Exception as e:
                    # If the pump is busy or the USB bus is choked, let the USB bus clear
                    if "bucket" in str(e).lower():
                        time.sleep(0.1)
                    else:
                        print(e)
        else:
            plt.ion()
            # self._ax.clear()
            self._ax.imshow(self.frame)
            plt.draw()

        # Proper ticker actualization logic
        elapsed = time.time() - self._last_tick
        delay = (1.0 / self._fps) - elapsed
        if self.debug:
            plt.pause(max(0.001, delay))
        i = int(self._fps * elapsed)
        print(f"skipped {i} frames ({delay:.2f}s, {elapsed:.2f}s)")
        i = 0
        if delay > 0:
            time.sleep(delay)
        self._last_tick = time.time()



def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", default=None, action="store_true", help="Enable debug mode")
    return parser.parse_args()



if __name__ == "__main__":
    args = arg_parser()
    debug = args.debug
    kraken = Kraken(debug=debug)
    kraken.init_frame()
    # threading.Thread(target=kraken.display, daemon=True).start()

    while True:
        kraken.display()
