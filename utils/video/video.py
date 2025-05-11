from __future__ import annotations

import os, shutil
from datetime import datetime, timezone

class Video:
    def __init__(self, filepath):
        self._filepath = filepath

    def get_filepath(self):
        return self._filepath

    def get_dirpath(self):
        return os.path.dirname(self._filepath)

    def get_filename(self):
        return os.path.basename(self._filepath)

    def get_size(self):
        return os.path.getsize(self._filepath)

    def get_datetime(self):
        unix_timestamp = int(self.get_filename().split('.')[0])

        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

    def get_age(self):
        now = datetime.now(tz=timezone.utc)

        return now - self.get_datetime()

    def get_age_seconds(self):
        return self.get_age().total_seconds()

    def exists(self):
        return os.path.exists(self._filepath)

    def delete(self):
        if not self.exists():
            raise Exception(f'Video does not exist at current location!')

        os.remove(self._filepath)

    def __lt__(self, v:Video):
        if not isinstance(v, Video):
            raise Exception(f'Cannot compare {type(self)} to {type(v)}')

        return self.get_datetime() < v.get_datetime()