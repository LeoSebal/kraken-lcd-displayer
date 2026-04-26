import io
from pathlib import Path
import time
import math
import warnings
import psutil
import argparse
import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps
from liquidctl import find_liquidctl_devices
import pynvml
import matplotlib.pyplot as plt



HEIGHT = 640
WIDTH = 640
RADIUS = 320


def get_font(size = 30):
    cwd = Path(__file__).parent
    return ImageFont.truetype(cwd / "fonts/Audiowide-Regular.ttf", size)

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


def rotated_rectangle(frame, x, y, rotation, width, height):
    drawing = ImageDraw.Draw()
    x1, y1 = to_px(x, y)
    x2 = x1 + width
    y2 = y1 + height
    center = ((x1+x2)/2, (y1+y2)/2)
    drawing.rectangle((x1, y1, x2, y2))
    drawing.rotate()


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

        self.colors = {
            "bg": (0,0,0),  # black
            "liquid": (97, 103, 131, 255),  # dark grey
            "widget_bg": (97, 103, 131, 255),  # light grey
            "widget_front": (0, 255, 255, 255),  # ice blue
            "numbers": (255, 255,255, 255), # white,
            "debug": "#9A4CB8",
        }

        pynvml.nvmlInit()
        self._nv_handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        self._cpu_temp = 0
        self._gpu_temp = 0
        self._liq_temp = 0
        self._cpu_load = 0
        self._gpu_load = 0

        self._resolution = (WIDTH, HEIGHT)
        self._frame = None

        self._brightness = 50

        self._bg_image = None
        self._angle = 30
        self._fps = 30
        self._last_tick = time.time()


    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def set_brightness(self, brightness:int):
        if 0 <= brightness <= 100:
            self._brightness = _brightness
            self.device.set_brightness(brightness)
        else:
            raise ValueError(f"Brightness must be between 0 and 100, not {brightness}")


    @property
    def bg_image(self):
        return self.bg_image

    @bg_image.setter
    def set_bg_image(self, bg_image):
        if Path(bg_image).exists():
            self._bg_image = bg_image
        else:
            raise FileNotFoundError(bg_image)


    @property
    def fps(self):
        return self._fps

    @fps.setter
    def set_fps(self, fps):
        if 1 <= fps <= 30:
            self._fps = fps
            if fps > 20:
                warnings.warn("FPS > 20 might not be stable")
        else:
            raise ValueError("FPS must be between 1 and 30")


    @property
    def angle(self):
        return self._angle

    @angle.setter
    def set_angle(self, angle):
        self._angle = angle


    def update_cpu_temp(self):
        temps = psutil.sensors_temperatures()
        self._cpu_temp = temps['k10temp'][0].current


    def update_cpu_load(self):
        self._cpu_load = psutil.cpu_percent()


    def update_gpu_temp(self):
        self._gpu_temp = pynvml.nvmlDeviceGetTemperature(self._nv_handle, pynvml.NVML_TEMPERATURE_GPU)


    def update_gpu_load(self):
        self._gpu_load = pynvml.nvmlDeviceGetUtilizationRates(self._nv_handle).gpu


    def update_all_stats(self):
        self.update_cpu_temp()
        self.update_cpu_load()
        self.update_gpu_temp()
        self.update_gpu_load()


    def _get_cpu_layer(self, rect_width, line_width, R, font_size, small_font_size,
        arc_length):

        # 1. Initialize canvas
        cpu_layer = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))
        cpu_widget = ImageDraw.Draw(cpu_layer)
        # 2. CPU anchors
        A = to_px(-0.5, 1/10)  # left anchor
        B = (A[0] + rect_width, A[1])  # right anchor
        # 3. CPU load arc gauge
        cpu_arc_box = [A[0] - R - line_width//2, A[1] - 2*R - line_width//2,
                       A[0] + R + line_width//2, A[1] + line_width//2]
        cpu_widget.arc(cpu_arc_box, start=90, end=90+arc_length, fill=self.colors["widget_bg"], width=line_width)
        cpu_widget.arc(cpu_arc_box, start=90, end=90 + (self._cpu_load / 100 * arc_length), fill=self.colors["widget_front"], width=line_width)
        # 4. CPU temp line gauge
        cpu_widget.line((*A, *B), fill=self.colors["widget_bg"], width = line_width)
        cpu_widget.line((*A, A[0] + (self._cpu_temp / 100 * rect_width), B[1]), fill=self.colors["widget_front"], width = line_width)
        # 5. CPU temp display
        cpu_widget.text((A[0], A[1] - R),
                    f"{int(self._cpu_temp)}°C",
                    font=get_font(font_size), fill=self.colors["numbers"], anchor="lm")
        # 6. CPU text
        cpu_txt = Image.new('RGBA', (R, R), color=(0, 0, 0, 0))
        d = ImageDraw.Draw(cpu_txt)
        d.text((0, 0), "CPU",
                font=get_font(small_font_size), fill=self.colors["numbers"], anchor="lt")
        cpu_txt = cpu_txt.rotate(90, expand=1)
        cpu_layer.paste(cpu_txt, (A[0] - R//2, A[1] - int(R*1.6)), cpu_txt)

        return cpu_layer


    def _get_gpu_layer(self, rect_width, line_width, R, font_size, small_font_size,
        arc_length):

        # 1. Initialize canvas
        gpu_layer = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))
        gpu_widget = ImageDraw.Draw(gpu_layer)
        # 2. GPU anchors
        D = to_px(0.5, -1/10)  # right anchor
        C = (D[0] - rect_width, D[1])  # left anchor
        # 3. GPU load arc gauge
        gpu_arc_box = [D[0] - R - line_width//2, D[1] - line_width//2,
                       D[0] + R + line_width//2, D[1] + 2*R + line_width//2]
        gpu_widget.arc(gpu_arc_box, start=270, end=270+arc_length, fill=self.colors["widget_bg"], width=line_width)
        gpu_widget.arc(gpu_arc_box, start=270, end=270 + (self._gpu_load / 100 * arc_length), fill=self.colors["widget_front"], width=line_width)
        # 4. GPU temp line gauge
        gpu_widget.line((*C, *D), fill=self.colors["widget_bg"], width = line_width)
        gpu_widget.line((D[0] - self._gpu_temp / 100 * rect_width, D[1], *D), fill=self.colors["widget_front"], width = line_width)
        # 5. GPU temp display
        gpu_widget.text((D[0], D[1] + R),
                    f"{int(self._gpu_temp)}°C", 
                    font=get_font(font_size), fill=self.colors["numbers"], anchor="rm")
        # 6. GPU text
        gpu_txt = Image.new('RGBA', (R, R), color=(0, 0, 0, 0))
        d = ImageDraw.Draw(gpu_txt)
        d.text((0, 0), "GPU",
                font=get_font(small_font_size), fill=self.colors["numbers"], anchor="lt")
        gpu_txt = gpu_txt.rotate(-90, expand=1)
        gpu_layer.paste(gpu_txt, (D[0] - R//2, D[1] + int(R*0.6)), gpu_txt)

        return gpu_layer


    def draw_frame(self):
        self.update_all_stats()
        radius = self._resolution[0]/2

        # 1. Base Layer (Main Canvas)
        self._frame = Image.new('RGBA', self._resolution, color=self.colors["bg"])
        main_draw = ImageDraw.Draw(self._frame)

        # For debugging purposes, draw a visual circle with a purple ring
        if self.debug:
            main_draw.rectangle((0,0,WIDTH,HEIGHT), fill=self.colors["debug"])
            main_draw.circle((WIDTH//2,HEIGHT//2),RADIUS, fill=self.colors["bg"])
            main_draw.line((WIDTH//2,0,WIDTH//2,HEIGHT), width=1, fill=self.colors["debug"])
            main_draw.line((0,HEIGHT//2,WIDTH,HEIGHT//2), width=1, fill=self.colors["debug"])

        # 1. Background Media
        if self._bg_image:
            # Scale 1.22 and Offset Y -0.352 from JSON
            scale = 1.22
            bg_w, bg_h = self._bg_image.size
            new_w, new_h = int(bg_w * scale), int(bg_h * scale)
            bg_resized = self._bg_image.resize((new_w, new_h))
            offset_y = int(-0.352 * radius)
            self._frame.paste(bg_resized, (radius - new_w // 2, radius - new_h // 2 + offset_y))

        # 3. Arcs (CPU and GPU Load)
        rect_width = int(1.09375 * RADIUS)  #  350 px
        line_width = int(0.0625 * RADIUS)  # 20 px
        R = int(0.28125 * RADIUS)  # 90 px
        font_size = 120  # pt
        small_font_size = 30  # pt
        arc_length = 170  # degrees

        # 4. Generate widget layers
        cpu_layer = self._get_cpu_layer(rect_width, line_width, R, font_size, small_font_size, arc_length)
        gpu_layer = self._get_gpu_layer(rect_width, line_width, R, font_size, small_font_size, arc_length)

        # 5. Composite Layers
        self._frame.paste(cpu_layer, (0, 0), cpu_layer)
        self._frame.paste(gpu_layer, (0, 0), gpu_layer)


    def display(self):
        if not self.debug:
            with io.BytesIO() as buffer:
                frame = self._frame.rotate(self._angle, resample=Image.BICUBIC)
                frame.save(buffer, format='BMP')
                buffer.seek(0)
                try:
                    self.device.set_screen('lcd', 'static', buffer)
                except:
                    # If the pump is busy or the USB bus is choked, wait before retrying
                    time.sleep(0.1)
        else:
            plt.ion()
            self._ax.imshow(self._frame)
            plt.draw()

        # Proper ticker actualization logic
        elapsed = time.time() - self._last_tick
        delay = (1.0 / self._fps) - elapsed
        if self.debug:
            plt.pause(max(0.001, delay))
        elif delay > 0:
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
    while True:
        kraken.draw_frame()
        kraken.display()
