import io
from pathlib import Path
import time
import warnings
import argparse
import threading
import signal
import sys
from PIL import Image, ImageDraw, ImageFont
from liquidctl import find_liquidctl_devices
import matplotlib.pyplot as plt  # for debug sessions

import widgets
from hwmon import get_cpu_temp, get_cpu_load, get_gpu_temp, get_gpu_load



HEIGHT = 640  # height of the frame to be displayed
WIDTH = 640  # width of the frame to be displayed
RADIUS = min(HEIGHT//2, WIDTH//2)  # actual radius of the Kraken Elite LCD
MAX_NB_ATTEMPTS = 3

global kraken

_FONT_CACHE = {}
running = True

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

        self.mode = 'static'

        self._cpu_temp = 0
        self._gpu_temp = 0
        self._liq_temp = 0
        self._cpu_load = 0
        self._gpu_load = 0

        self._resolution = (WIDTH, HEIGHT)

        # Background image (only static allowed for now)
        self._bg_image = None
        # Display angle
        self._angle = 0
        # FPS to be displayed on-screen
        self._fps = 15
        self._last_tick = time.time()
        # Rate at which data is polled 
        self._poll_rate = 0.5
        self._last_stats_update = time.time()
        # Rate at which we display onto the Kraken.
        # Will have to be calculated depending on GIF duration (when that is supported) and poll rate
        self._push_rate = 5
        self._last_push = time.time()

        self.frames = []
        self._bg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 255))  # black background
        self._fg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))  # transparent widget layer

        # frame management
        self.init_frame()
        self._frame_lock = threading.Lock()
        self._frame_ready = threading.Condition(self._frame_lock)
        self.current_frame_data = None
        self._last_frame_data = None


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
            "cpu_temp_text": widgets.Text(lambda: f"{round(self.cpu_temp)}°C", font_path, 120, align="lb"),
            "gpu_temp_line": widgets.LineGraphic(rect_width, line_width, data_updater=lambda: self.gpu_temp, rot=180),
            "gpu_load_arc": widgets.ArcGraphic(170, arc_radius, line_width, data_updater=lambda: self.gpu_load, rot=180),
            "gpu_temp_text": widgets.Text(lambda: f"{round(self.gpu_temp)}°C", font_path, 120, align="rt"),
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

            bg = widget.bg
            self._bg.paste(bg, widget.pos, bg)
            fg = widget.fg
            if widget.fg:
                self._fg.paste(fg, widget.pos, fg)


    def update_frames(self):
        self._fg = Image.new('RGBA', self._resolution, color=(0, 0, 0, 0))
        frame_changed = False
        for widget in self.widgets.values():
            frame_changed |= bool(widget.update())
            fg = widget.fg
            if fg:
                self._fg.paste(fg, widget.pos, fg)

        if self.current_frame_data is not None and not frame_changed:
            return

        frame = Image.alpha_composite(self._bg, self._fg)
        if not self.debug:
            frame = frame.rotate(self._angle, resample=Image.BICUBIC)

        buffer = io.BytesIO()

        if self.mode == 'static':
            self.frames = [frame]
            self.frames[0].save(buffer, format='PNG')
        elif self.mode == 'gif':
            frame_count = max(1, round(self._fps / self._push_rate))
            self.frames = [frame] * frame_count
            self.frames[0].convert("P", palette=Image.ADAPTIVE).save(
                buffer,
                format='GIF',
                save_all=True,
                append_images=self.frames[1:],
                duration=int(1000 / self._fps),
                loop=0,
            )

        payload = buffer.getvalue()

        if payload == self._last_frame_data:
            return

        self._last_frame_data = payload
        with self._frame_ready:
            self.current_frame_data = payload
            self._frame_ready.notify_all()


    def _send_payload(self, payload):
        if not getattr(self, 'device', None):
            return

        for attempt in range(1, MAX_NB_ATTEMPTS + 1):
            if hasattr(self.device, 'clear_enqueued_reports'):
                try:
                    self.device.clear_enqueued_reports()
                except Exception:
                    print("Warning: Failed to clear enqueued reports. Continuing with sending the frame.")

            try:
                with io.BytesIO(payload) as stream:
                    self.device.set_screen('lcd', 'static', stream)
                return
            except Exception as e:
                message = str(e).lower()
                if attempt >= 3 or not any(word in message for word in ('bucket', 'usb', 'langid', 'timeout', 'failed')):
                    print(f"USB Communication Error: {e}")
                    return
                time.sleep(0.2)


    def display(self):
        while True:
            with self._frame_ready:
                self._frame_ready.wait()
                data_to_send = self.current_frame_data

            if data_to_send and not self.debug:
                self._send_payload(data_to_send)


    def stop(self):
        global running
        running = False
        if not self.debug and hasattr(self, 'device'):
            self.device.disconnect()

    def run(self):
        # Send data to display in a separate thread while the main loop updates the frames
        if not self.debug:
            threading.Thread(target=kraken.display, daemon=True).start()
        while running:
            self.update_frames()
            if not self.debug:
                time.sleep(1 / self._push_rate)
            else:
                # The debugging mode is a direct display mode, that displays the UI in a Matplotlib plot
                for frame in kraken._frames:
                    kraken._ax.imshow(frame)
                    plt.pause(1/kraken._fps)



def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", default=None, action="store_true", help="Enable debug mode")
    return parser.parse_args()



def handle_signal(signum, frame):
    kraken.stop()
    sys.exit(0)

if __name__ == "__main__":
    args = arg_parser()
    debug = args.debug
    kraken = Kraken(debug=debug)
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    kraken.init_frame()
    kraken.run()
