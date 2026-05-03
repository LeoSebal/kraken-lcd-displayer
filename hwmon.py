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



def get_gpu_temp_nvidia():
    return pynvml.nvmlDeviceGetTemperature(_NV_HANDLE, pynvml.NVML_TEMPERATURE_GPU)



def get_gpu_load_nvidia():
    return pynvml.nvmlDeviceGetUtilizationRates(_NV_HANDLE).gpu



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



gpu_brand = get_gpu_brand()
match gpu_brand:
    case 'nvidia':
        import pynvml
        global _NV_HANDLE
        pynvml.nvmlInit()
        _NV_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)

        get_gpu_temp = get_gpu_temp_nvidia
        get_gpu_load = get_gpu_load_nvidia

    case 'intel':
        # raise NotImplementedError("GPU monitoring for Intel GPUs is not implemented yet.")
        get_gpu_temp = lambda: randint(30, 70)  # Placeholder: return random temp between 30-70°C
        get_gpu_load = lambda: randint(0, 100)  # Placeholder: return random load between 0-100%

    case 'amd':
        raise NotImplementedError("GPU monitoring for Intel AMDs is not implemented yet.")
