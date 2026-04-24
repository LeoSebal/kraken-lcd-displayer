#!/usr/bin/env python3
import io
from pathlib import Path
import time
import psutil
from PIL import Image, ImageDraw, ImageFont
from liquidctl import find_liquidctl_devices
import pynvml
import matplotlib.pyplot as plt



def get_font(size = 30):
    cwd = Path(__file__).parent
    return ImageFont.truetype(cwd / "fonts/Audiowide-Regular.ttf", size)

def to_px(val):
    """Converts NZXT normalized coordinates to pixel coordinates."""
    return 320 + (val * 320)



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
            self.fig, self.ax = plt.subplots()
            # self.ax.remove()

        pynvml.nvmlInit()
        self.nv_handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        self.cpu_temp = 0
        self.gpu_temp = 0
        self.liq_temp = 0
        self.cpu_load = 0
        self.gpu_load = 0

        self.frame = None
        self.bg_image = None

        self.resolution = [640, 640]
        self.angle = -60

        self.fps = 20


    def update_cpu_temp(self):
        temps = psutil.sensors_temperatures()
        self.cpu_temp = temps['k10temp'][0].current


    def update_cpu_load(self):
        self.cpu_load = psutil.cpu_percent()


    def update_gpu_temp(self):
        self.gpu_temp = pynvml.nvmlDeviceGetTemperature(self.nv_handle, pynvml.NVML_TEMPERATURE_GPU)


    def update_gpu_load(self):
        self.gpu_load = pynvml.nvmlDeviceGetUtilizationRates(self.nv_handle).gpu


    def update_all_stats(self):
        self.update_cpu_temp()
        self.update_cpu_load()
        self.update_gpu_temp()
        self.update_gpu_load()


    def draw_frame(self):
        self.update_all_stats()

        colors = {
            "bg": (0,0,0),  # black
            "liquid": (97, 103, 131, 255),  # dark grey
            "widget_front": (0, 255, 255, 255),  # ice blue
            "numbers": (255, 255,255, 255), # white
        }

        # Canvas resolution for Kraken Elite
        self.frame = Image.new('RGBA', self.resolution, color=colors["bg"])
        draw = ImageDraw.Draw(self.frame)

        if self.debug:
            draw.rectangle((0,0,640,640), fill="red")
            draw.circle((320,320),320, fill=colors["bg"])

        # 1. Background Media
        if self.bg_image:
            # Scale 1.22 and Offset Y -0.352 from JSON
            bg_w, bg_h = self.bg_image.size
            new_w = int(640 * 1.22)
            new_h = int(640 * 1.22)
            bg_resized = self.bg_image.resize((new_w, new_h))
            offset_y = int(-0.352 * 320)
            self.frame.paste(bg_resized, (320 - new_w // 2, 320 - new_h // 2 + offset_y))

        # 2. Liquid Temp Circle (Infographic)
        # Color from JSON: RGB(97, 103, 131)
        # color = (97, 103, 131)  # 
        # liquid_color = (97, 103, 131)
        # The circle fills the 640x640 area based on liquid temp
        # fill_height = int((liq_temp / 100) * 640)
        # draw.ellipse([0, 0, 640, 640], outline=None, fill=(20, 20, 30)) # Background sphere
        # draw.chord([0, 0, 640, 640], start=180, end=0, fill=colors["liquid"]) # Wave approximation

        # 3. Arcs (CPU and GPU Load)
        # CPU Arc: x: -0.194, y: -0.5557, size: 250, angle: 185
        cpu_arc_box = [to_px(-0.194) - 125, to_px(-0.5557) - 125, to_px(-0.194) + 125, to_px(-0.5557) + 125]
        draw.arc(cpu_arc_box, start=135, end=135 + (self.cpu_load / 100 * 185), fill=colors["widget_front"], width=30)

        # GPU Arc: x: 0.1938, y: 0.5563, size: 250, angle: 185
        gpu_arc_box = [to_px(0.1938) - 125, to_px(0.5563) - 125, to_px(0.1938) + 125, to_px(0.5563) + 125]
        draw.arc(gpu_arc_box, start=315, end=315 + (self.gpu_load / 100 * 185), fill=colors["widget_front"], width=30)

        # 4. Metrics (CPU and GPU Temp)
        # CPU Temp: x: 0.0855, y: -0.3938, fontSize: 120
        draw.text((to_px(0.0855), to_px(-0.3938)), f"{int(self.cpu_temp)}°C", 
                    font=get_font(120), fill=colors["numbers"], anchor="mm")

        # GPU Temp: x: -0.0844, y: 0.3938, fontSize: 120
        draw.text((to_px(-0.0844), to_px(0.3938)), f"{int(self.gpu_temp)}°C", 
                    font=get_font(120), fill=colors["numbers"], anchor="mm")

        # 5. Icons (CPU and GPU)
        draw.text((to_px(0.7403), to_px(-0.0736)), "CPU", font=get_font(30), fill=colors["numbers"], anchor="mm")
        draw.text((to_px(-0.7406), to_px(0.075)), "GPU", font=get_font(30), fill=colors["numbers"], anchor="mm")

        # Final Rotation (If needed for hardware mounting orientation)
        if not self.debug:
            self.frame = self.frame.rotate(self.angle, resample=Image.BICUBIC)


    def display(self):
        if not self.debug:
            with io.BytesIO() as buffer:
                self.frame.save(buffer, format='PNG')
                buffer.seek(0)
                self.device.set_screen('lcd', 'static', buffer)
            time.sleep(1./self.fps)
        else:
            plt.ion()
            self.ax.imshow(self.frame)
            plt.draw()
            plt.pause(1./self.fps)



if __name__ == "__main__":
    kraken = Kraken(debug=False)
    while True:
        kraken.draw_frame()
        kraken.display()
