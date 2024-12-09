#!/usr/bin/env python3

from time import sleep
import threading, multiprocessing, subprocess, os, signal

from utils.logger import Logger
from utils.datetime import datetime

class NVR:
    def __init__(self, name:str, source:str, segment_duration_s:int, storage_dirpath:str, max_age_hours:float, max_disk_gb:float):
        self._name = name
        self._source = source
        self._segment_duration_s = segment_duration_s
        self._storage_dirpath = storage_dirpath
        self._max_age_hours = max_age_hours
        self._max_disk_gb = max_disk_gb

        self._is_running = False
        self._should_be_running = multiprocessing.Event()

        self._threads = []
        self._subprocess = None

        self._logger = Logger(os.path.join(self._storage_dirpath, f'{datetime.get_datetime()}.log'))

    def is_running(self):
        return self._is_running

    def start(self):
        if self.is_running():
            # Prevent multiple instances
            raise Exception(f'NVR {self._name} is already running!')

        # Set flag
        self._is_running = True

        # Ignore interrupt signals
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Set flag so processes keep restarting
        self._should_be_running.set()

        # Create threads for checking limits and recording
        self._threads.append(threading.Thread(target=self._start_limit_checker, daemon=True))
        self._threads.append(threading.Thread(target=self._start_recorder, daemon=True))

        # Start threads
        for thread in self._threads:
            thread.start()

        # Keep threads running
        for thread in self._threads:
            thread.join()

    def stop(self):
        # Unset flag so processes do not restart
        self._should_be_running.clear()
        
        if self._subprocess is not None:
            # Stop subprocess if it is running
            self._subprocess.terminate()
            self._subprocess.wait()

        for thread in self._threads:
            thread.join()

        # Clear flag once threads have exited
        self._is_running = False

    def _get_oldest_video(self):
        pass

    def _prune_oldest(self):
        pass

    def _check_storage_limit(self):
        if self._max_disk_gb is None or self._max_disk_gb <= 0:
            return

        self._logger.log_info('Checking storage...')

    def _check_age_limit(self):
        if self._max_age_hours is None or self._max_age_hours <= 0:
            return

        self._logger.log_info('Checking age...')

    def _start_limit_checker(self):
        while self._should_be_running.is_set():
            try:
                try:
                    # Check age limit
                    self._check_age_limit()
                except Exception as e:
                    self._logger.log_error(f'Failed to check age limit: {e}')

                try:
                    # Check disk limit
                    self._check_storage_limit()
                except Exception as e:
                    self._logger.log_error(f'Failed to check storage limit: {e}')
            except Exception as e:
                self._logger.log_error(f'Failed to check limits: {e}')
            finally:
                # Delay before next checks
                sleep(5)

    def _start_recorder(self):
        while self._should_be_running.is_set():
            try:
                self._logger.log_info(f'Recording {self._name}...')
            except Exception as e:
                self._logger.log_error(f'Failed to run recorder: {e}')
            finally:
                # Delay before restarting recorder
                sleep(5)