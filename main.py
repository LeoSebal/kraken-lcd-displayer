import io
from pathlib import Path
import time
import warnings
import argparse
import threading
from PIL import Image, ImageDraw, ImageFont
from liquidctl import find_liquidctl_devices
import matplotlib.pyplot as plt

import widgets
from stats import get_cpu_temp, get_cpu_load, get_gpu_temp, get_gpu_load



HEIGHT = 640  # height of the frame to be displayed
WIDTH = 640  # width of the frame to be displayed
RADIUS = 320  # actual radius of the Kraken Elite LCD

global kraken



_FONT_CACHE = {}

def get_font(size=30):
    if size not in _FONT_CACHE:
        cwd = Path(__file__).parent
        _FONT_CACHE[size] = ImageFont.truetype(str(cwd / "fonts/Audiowide-Regular.ttf"), size)
    return _FONT_CACHE[size]

def to_px(x,y):
    """Utility function that converts (-1,1:1,1) axis coordinates to pixel coordinates."""
    return (
        int(RADIUS + x*RADIUS), 
        int(RADIUS - y*RADIUS)
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

        self._cpu_temp = 0
        self._gpu_temp = 0
        self._liq_temp = 0
        self._cpu_load = 0
        self._gpu_load = 0

        self._resolution = (WIDTH, HEIGHT)

        # Background image (only static allowed for now)
        self._bg_image = None
        # Display angle
        self._angle = 30
        # FPS to be displayed on-screen
        self._fps = 15
        # Rate at which data is polled 
        self._poll_rate = 0.5
        self._last_stats_update = 0
        # Rate at which we display onto the Kraken.
        # Will have to be calculated depending on GIF duration (when that is supported) and poll rate
        self._push_rate = 1
        self._last_tick = time.time()

        self.frame = Image.new('RGBA', self._resolution, color=(0, 0, 0, 255))
        self._bg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 255))  # black background
        self._fg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))  # transparent widget layer
        self.init_frame()
        self.current_frame_data = None


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
        return get_cpu_temp()

    @property
    def cpu_load(self):
        return get_cpu_load()
    @property
    def gpu_temp(self):
        return get_gpu_temp()

    @property
    def gpu_load(self):
        return get_gpu_load()

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
            "gpu_temp_text": widgets.Text(lambda: f"{int(self.gpu_temp)}°C", font_path, 120, align="rt"),
        }

        # Define placement: (x, y) coordinates, which edge to align (offset from center) and rotation angle
        self.widget_configs = {
            "cpu_temp_line": (A[0], A[1]+1,                             "left",     0),
            "cpu_load_arc":  (A[0], A[1] - arc_radius + line_width//2,  "center",   0),
            "cpu_temp_text": (A[0], A[1] - arc_radius,                  "left",     0),
            "gpu_temp_line": (D[0] - rect_width, D[1]-1,                "left",     0),
            "gpu_load_arc":  (D[0], D[1] + arc_radius - line_width//2,  "center",   0),
            "gpu_temp_text": (D[0], D[1] + arc_radius,                  "right",    0),
        }

        self._brightness = 50
        self.colors = {
            "debug": "#9A4CB8",
            "bg": "#000000"  # black
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
            with io.BytesIO() as buffer:
                self.frame.convert("P", palette=Image.ADAPTIVE).save(buffer, format='GIF', append_images=[self.frame]*5, duration=500, loop=0)
                self.current_frame_data = buffer.getvalue()


    def display(self):
        while True:
            # Take a local reference to the frame data
            data_to_send = self.current_frame_data

            if data_to_send and not self.debug:
                try:
                    # Wrap the bytes in BytesIO so liquidctl treats it as a stream, not a path
                    with io.BytesIO(data_to_send) as stream:
                        # Note: 'animation' is the standard liquidctl mode for GIF/AVI on Kraken Elite
                        self.device.set_screen('lcd', 'gif', stream)
                except Exception as e:
                    # Handle USB congestion (liquidctl bucket errors)
                    if "bucket" in str(e).lower():
                        time.sleep(0.1)
                    else:
                        print(f"USB Communication Error: {e}")

            # Throttle the display thread to match the target FPS
            elapsed = time.time() - self._last_tick
            delay = (1.0 / self._fps) - elapsed
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

    # Start the USB communication in a background thread.
    # It will continuously push whatever is in `kraken.current_frame_data`.
    if not debug:
        threading.Thread(target=kraken.display, daemon=True).start()

    while True:
        # The main thread handles data fetching and rendering the UI layers.
        kraken.update_frame()
        # The debugging mode is a direct display mode, that displays the UI in a Matplotlib plot
        if debug:
            kraken._ax.clear()
            kraken._ax.imshow(kraken.frame)
            plt.pause(1/kraken._fps) # Small pause to allow GUI events to process
