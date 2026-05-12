# WIP
from pathlib import Path
import ruamel.yaml as yaml

from widgets import LineGraphic, ArcGraphic, Text
from hwmon import get_cpu_temp, get_cpu_load, get_gpu_temp, get_gpu_load



DEFAULT_PROFILE = "default.yaml"


hwmon_functions = {
    'cpu_load': get_cpu_load,
    'gpu_load': get_gpu_load,
    'cpu_temp': get_cpu_temp,
    'gpu_temp': get_gpu_temp,
    'liquid_temp': get_liq_temp,
}



class ProfileManager:
    def __init__(self, profile_path: Path = "./profiles/default.yaml"):
        self.profile_path = profile_path
        self.widgets = []
        self.colors = {}
        self.profile = self.load_profile()

    def load_profile(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for widget_data in data.get("widgets", []):
            self.widget.append(WidgetProfile(widget_data), self.colors)

    def save_profile(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.profiles, f)

    def _write_widget_profile(self, widget_name, profile_name, profile_data):
        if widget_name not in self.profiles:
            self.profiles[widget_name] = {}
        self.profiles[widget_name][profile_name] = profile_data
        self.save_profiles()



class WidgetProfile(Widget):
    def __init__(self, widget_data:dict, ref_colors = {}):
        generic_keys = [
            "name", "position", "height", "width", "rotation", "alpha"
        ]
        # Generic widget properties
        for key in generic_keys:
            if key in widget_data.value():
                setattr(self, key, widget_data[key])

        # Check if colors have been saved in the widget profile
        # If they have and differ from the reference colors, load them
        if "colors" in widget_data.keys():
            for color_key, color in widget_data["colors"].items():
                if ref_colors[color_key] != color:
                    self.colors[color_key] = color

        # hwmon functions
        if "source_metric" in widget_data.keys():
            self.data_updater = hwmon_functions[widget_data["source_metric"]]
