#!/usr/bin/env python3
import io
import time
import psutil
from PIL import Image, ImageDraw
from liquidctl import find_liquidctl_devices
from pynvml import *

def get_kraken_device():
    # Look specifically for the Elite
    for dev in find_liquidctl_devices():
        if "Kraken" in dev.description:
            dev.connect()
            # initialize() is often required to wake the interface for control
            dev.initialize()
            return dev
    return None


def get_cpu_temp():
    temps = psutil.sensors_temperatures()
    # Common keys: 'coretemp' (Intel), 'k10temp' (AMD), 'cpu_thermal' (Raspberry Pi)
    for name in ['coretemp', 'k10temp', 'cpu_thermal']:
        if name in temps:
            # Returns the temperature of the first package/core
            return temps[name][0].current
    return 0.0


def get_gpu_temp_nvidia(handle):
    try:
        temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        return temp
    except:
        return 0.0


def create_frame(cpu_temp, gpu_temp, liq_temp, load, bg_image=None):
    # Elite resolution is 640x640
    if bg_image:
        img = bg_image.convert('RGB').resize((640, 640))
    else:
        img = Image.new('RGB', (640, 640), color=(0, 0, 0))
    
    draw = ImageDraw.Draw(img)
    
    # Semi-transparent overlay for text readability if there's a background
    if bg_image:
        overlay = Image.new('RGBA', (640, 640), (0, 0, 0, 100))
        img.paste(overlay, (0,0), overlay)

    # Draw stats (Note: Default font is small, consider ImageFont.truetype for better looks)
    draw.text((320, 200), f"LIQUID: {liq_temp:.1f}°C", fill=(0, 255, 130), anchor="mm", font_size=60)
    draw.text((320, 300), f"CPU: {cpu_temp:.1f}°C ({load}%)", fill=(255, 255, 255), anchor="mm", font_size=40)
    draw.text((320, 400), f"GPU: {gpu_temp:.1f}°C", fill=(255, 150, 0), anchor="mm", font_size=40)

    # Rotate the image 30 degrees counter-clockwise
    img = img.rotate(-60, resample=Image.BICUBIC)

    return img


if __name__ == "__main__":
    kraken = get_kraken_device()
    
    # Initialize NVML once
    try:
        nvmlInit()
        nv_handle = nvmlDeviceGetHandleByIndex(0)
    except:
        nv_handle = None

    # Optional: Load a GIF to use as background frames
    # gif = Image.open("your_animation.gif")
    # frame_count = 0

    if kraken:
        try:
            print(f"Connected to {kraken.description}")
            while True:
                # 1. Gather Data
                cpu_load = psutil.cpu_percent()
                cpu_temp = get_cpu_temp()
                gpu_temp = get_gpu_temp_nvidia(nv_handle) if nv_handle else 0
                
                raw_status = kraken.get_status()
                liq_temp = 0
                for desc, val, unit in raw_status:
                    if "Liquid temperature" in desc:
                        liq_temp = val
                        break
                
                # 2. Render (Pass a background frame if desired)
                frame = create_frame(cpu_temp, gpu_temp, liq_temp, cpu_load)
                
                # 3. Push to LCD
                # The driver expects a file-like object with a .read() method
                with io.BytesIO() as buffer:
                    frame.save(buffer, format='PNG')
                    buffer.seek(0)
                    kraken.set_screen('lcd', 'static', buffer)
                
                time.sleep(0.5) # Refresh slightly faster for smoother updates

        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            kraken.disconnect()
            if nv_handle:
                nvmlShutdown()
    else:
        print("No Kraken Elite found!")
