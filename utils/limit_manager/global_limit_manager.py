from ..logger import Logger
from ..recorder import Recorder
from ..limit_manager import LimitManager

class GlobalLimitManager(LimitManager):
    def __init__(self, logger:Logger, recorders:list[Recorder], max_disk_bytes:int):
        super().__init__(logger, max_disk_bytes=max_disk_bytes)

        self._recorders = recorders
    
    def _get_videos(self):
        unsorted_videos = []
        for recorder in self._recorders:
            for video in recorder.get_videos():
                unsorted_videos.append(video)

        return sorted(unsorted_videos)