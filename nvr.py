#!/usr/bin/env python3

from subprocess import run, PIPE
from time import sleep

class NVR:
    def __init__(self, name: str, source: str, segment_duration_s: int, storage_dirpath: str):
        super().__init__()

        self._name = name
        self._source = source
        self._segment_duration_s = segment_duration_s
        self._storage_dirpath = storage_dirpath

        self._shouldBeRunning = False
        self._process = None

        # print(self._name, self._source, self._segment_duration_s, self._storage_dirpath)

    def isRunning(self):
        if self._process is None:
            return False

        return self._process.poll() is None

    def start(self):
        if self.isRunning():
            raise Exception(f'NVR {self._name} is already running!')

        self._shouldBeRunning = True
        while self._shouldBeRunning:
            print(f'NVR {self._name} is doing stuff...')
            sleep(2)

    def stop(self):
        self._shouldBeRunning = False
        if self.isRunning():
            self._process.terminate()
            self._process.wait()