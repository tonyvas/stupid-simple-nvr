from ..logger import Logger
from ..recorder import Recorder
from ..limit_manager import LimitManager

class RecorderLimitManager(LimitManager):
    def __init__(self, logger:Logger, recorder:Recorder, max_age_sec:int|None=None, max_disk_bytes:int|None=None):
        super().__init__(logger, max_age_sec=max_age_sec, max_disk_bytes=max_disk_bytes)

        self._recorder = recorder
    
    def _get_videos(self):
        return self._recorder.get_videos()