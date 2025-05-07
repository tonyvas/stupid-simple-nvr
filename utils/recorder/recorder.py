import threading, subprocess, os
from time import sleep

from ..logger import Logger

class Recorder:
    def __init__(self, storage_dirpath:str, name:str, source:str, segment_duration_sec:int, max_age_hours:float|None=None, max_disk_gb:float|None=None):
        self._storage_dirpath = storage_dirpath
        self._name = name
        self._source = source
        self._segment_duration_sec = segment_duration_sec
        self._max_age_hours = max_age_hours
        self._max_disk_gb = max_disk_gb

        self._is_running = False

        self._threads = [
            threading.Thread(target=self._start_video_mover, daemon=True),
            threading.Thread(target=self._start_recorder, daemon=True),
            threading.Thread(target=self._start_limit_checker, daemon=True)
        ]
        self._subprocess = None

        self._video_dirpath = os.path.join(storage_dirpath, 'videos')
        self._temp_dirpath = os.path.join(storage_dirpath, 'temp')

        self._logger = Logger(os.path.join(self._storage_dirpath, f'{self._name}.log'))

    def is_running(self):
        return self._is_running

    def start(self):
        try:
            self._log_info('Starting recorder...')

            if self.is_running():
                # Prevent multiple instances
                raise Exception(f'Recorder is already running!')

            # Ignore interrupt signals
            # signal.signal(signal.SIGINT, signal.SIG_IGN)

            # Set flag
            self._is_running = True

            self._log_info('Starting threads...')
            for thread in self._threads:
                thread.start()

            self._log_info('Recorder started!')
            for thread in self._threads:
                thread.join()
        except Exception as e:
            message = f'Failed to start: {e}'
            self._log_error(message)
            raise Exception(message)

    def stop(self):
        try:
            self._log_info('Stopping recorder...')

            # Clear flag
            self._is_running = False

            if self._subprocess is not None:
                # Stop subprocess if it is running
                self._log_info('Terminating subprocess...')
                self._subprocess.terminate()
                self._subprocess.wait()

            self._log_info('Waiting for threads to finish...')
            for thread in self._threads:
                thread.join()

            self._log_info('Recorder stopped!')
        except Exception as e:
            message = f'Failed to stop: {e}'
            self._log_error(message)
            raise Exception(message)

    def _log_info(self, message):
        self._logger.log_info(f'{self._name}: {message}')

    def _log_error(self, message):
        self._logger.log_error(f'{self._name}: {message}')

    def _start_video_mover(self):
        while self.is_running():
            try:
                self._log_info(f'Checking for completed videos to move...')
            except Exception as e:
                self._log_error(f'Failed to run mover: {e}')
            finally:
                sleep(5)

    def _start_limit_checker(self):
        while self.is_running():
            try:
                # Check limits
                self._check_age_limit()
                self._check_storage_limit()
            except Exception as e:
                self._log_error(f'Failed to check limits: {e}')
            finally:
                # Delay before next check
                sleep(5)

    def _start_recorder(self):
        while self.is_running():
            try:
                self._log_info(f'Recording {self._name}...')
            except Exception as e:
                self._log_error(f'Failed to run recorder: {e}')
            finally:
                # Delay before restarting recorder
                sleep(5)

    def _check_storage_limit(self):
        if self._max_disk_gb is None:
            return

        self._log_info('Checking storage...')

    def _check_age_limit(self):
        if self._max_age_hours is None:
            return

        self._log_info('Checking age...')

    def _prune_oldest(self):
        pass

    def _get_oldest_video(self):
        pass