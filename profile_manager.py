# WIP
from pathlib import Path
import yaml
# import json

import widgets

DEFAULT_PROFILE = "default.yaml"



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
            "position", "height", "width", "rotation", "alpha"
        ]
        # Load position
        for key in generic_keys:
            if key in widget_data.value():
                setattr(self, key, widget_data[key])

        # Check if colors have been saved in the widget profile
        # If they have and differ from the reference colors, load them
        if "colors" in widget_data.keys():
            for color_key, color in widget_data["colors"].items():
                if ref_colors[color_key] != color:
                    self.colors[color_key] = color