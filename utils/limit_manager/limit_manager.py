from ..logger import Logger
from ..recorder import Recorder

class LimitManager:
    def __init__(self, logger:Logger, max_age_sec:int|None=None, max_disk_bytes:int|None=None):
        self._logger = logger
        self._max_age_sec = max_age_sec
        self._max_disk_bytes = max_disk_bytes

    def run(self):
        try:
            # Check limits
            self._check_age_limit()
            self._check_storage_limit()
        except Exception as e:
            message = f'Failed to check limits: {e}'
            self._log_error(message)
            raise Exception(message)

    def _log_info(self, message):
        self._logger.log_info(message)

    def _log_error(self, message):
        self._logger.log_error(message)

    def _log_warning(self, message):
        self._logger.log_warning(message)

    def _get_videos(self):
        raise Exception(f'LimitManager interface _get_videos needs an override!')

    def _check_storage_limit(self):
        if self._max_disk_bytes is None:
            return

        try:
            # Calculate total size
            videos = self._get_videos()
            total_bytes = sum(video.get_size() for video in videos)

            # Calculate how many bytes to free up
            bytes_over_limit = total_bytes - self._max_disk_bytes

            # Delete videos until below limit
            while bytes_over_limit > 0:
                # If no videos to delete, then something is very wrong
                if len(videos) == 0:
                    raise Exception(f'Above disk limit, but no videos to delete!')

                # Get oldest video from list
                oldest = videos.pop(0)

                try:
                    self._log_info(f'Deleting {oldest.get_filename()}, above disk limit!')

                    # Get its size
                    size = oldest.get_size()

                    # Delete video and update disk usage
                    oldest.delete()
                    bytes_over_limit -= size
                except Exception as e:
                    self._log_warning(f'Failed to delete {oldest.get_filename()}: {e}')
        except Exception as e:
            raise Exception(f'Failed to handle disk limit: {e}')

    def _check_age_limit(self):
        if self._max_age_sec is None:
            return

        try:
            # Get list of all videos
            videos = self._get_videos()

            for video in videos:
                try:
                    # Get age
                    age_sec = video.get_age_seconds()

                    if age_sec > self._max_age_sec:
                        # If video is too old, delete it
                        self._log_info(f'Deleting {video.get_filename()}, video is too old!')
                        video.delete()
                    else:
                        # If not, stop checking. Further videos are even younger
                        break
                except Exception as e:
                    self._log_warning(f'Failed to delete {video.get_filename()}: {e}')
        except Exception as e:
            raise Exception(f'Failed to age limit: {e}')