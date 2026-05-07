# WIP: not functional at this point
from pathlib import Path
import yaml
# import json



class ProfileManager:
    def __init__(self, config_path: Path = "./profiles/default.yaml"):
        self.config_path = config_path
        self.profiles = self.load_profiles()

    def load_profiles(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def save_profiles(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.profiles, f)

    def _write_widget_profile(self, widget_name, profile_name, profile_data):
        if widget_name not in self.profiles:
            self.profiles[widget_name] = {}
        self.profiles[widget_name][profile_name] = profile_data
        self.save_profiles()
