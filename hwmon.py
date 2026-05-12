import psutil
import subprocess
from pathlib import Path
from random import randint



def get_cpu_temp():
    temps = psutil.sensors_temperatures()
    if 'k10temp' in temps:
        return temps['k10temp'][0].current
    elif 'coretemp' in temps:
        return temps['coretemp'][0].current



def get_cpu_load():
    return psutil.cpu_percent()



def _get_gpu_temp_nvidia():
    return pynvml.nvmlDeviceGetTemperature(_NV_HANDLE, pynvml.NVML_TEMPERATURE_GPU)



def _get_gpu_load_nvidia():
    return pynvml.nvmlDeviceGetUtilizationRates(_NV_HANDLE).gpu



def _get_gpu_temp_amd():
    hwmon_path = Path("/sys/class/drm/card0/device/hwmon/")

    try:
        # There's usually one folder inside (e.g., hwmon3)
        for hwmon_dir in hwmon_path.iterdir():
            if hwmon_dir.is_dir():
                temp_file = hwmon_dir / "temp1_input"
                break
    
        with open(temp_file, "r") as f:
            # Value is in millidegrees Celsius
            return int(f.read().strip()) / 1000
    except Exception:
        return None



def _get_gpu_load_amd():
    # card0 is usually the first GPU
    load_path = "/sys/class/drm/card0/device/gpu_busy_percent"

    try:
        with open(load_path, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0



def get_gpu_brand() -> str:
    """Return 'nvidia', 'intel', 'amd', or 'unknown' based on system PCI listing."""
    out = subprocess.run("lspci -nn", shell=True, capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if not ('VGA' in line or '3D controller' in line):
            continue
        l = line.lower()
        if 'nvidia' in l:
            return 'nvidia'
        if 'intel' in l:
            return 'intel'
        if 'amd' in l or 'advanced micro devices' in l or 'ati' in l:
            return 'amd'
    raise ValueError("Unable to determine GPU brand from lspci output.")


_gpu_temp_fns = {
    'nvidia': _get_gpu_temp_nvidia,
    'intel': _get_gpu_temp_amd,
    'amd': _get_gpu_temp_amd
}

_gpu_load_fns = {
    'nvidia': _get_gpu_load_nvidia,
    'intel': _get_gpu_load_amd,
    'amd': _get_gpu_load_amd
}


_gpu_brand = get_gpu_brand()

if _gpu_brand == "nvidia":
    import pynvml
    global _NV_HANDLE
    pynvml.nvmlInit()
    _NV_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)

get_gpu_temp = _gpu_temp_fns[_gpu_brand]
get_gpu_load = _gpu_load_fns[_gpu_brand]
