import os
import threading

import yaml


class CredentialStore:
    """
    Keeps refreshed cookies out of the hand-edited recorder_config.yaml.

    Each entry remembers the config SESSDATA it was refreshed from ("base_sessdata"). Once someone pastes
    new cookies into the config, that no longer matches and the config wins again.
    """

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.entries = {}
        if os.path.isfile(path):
            with open(path, 'r') as file:
                self.entries = yaml.safe_load(file) or {}

    def get(self, key, base_sessdata):
        entry = self.entries.get(key)
        if entry is None or entry.get("base_sessdata") != base_sessdata:
            return None
        return entry

    def put(self, key, entry):
        with self.lock:
            self.entries[key] = entry
            tmp_path = self.path + ".tmp"
            with open(tmp_path, 'w') as file:
                yaml.safe_dump(self.entries, file, allow_unicode=True)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, self.path)
