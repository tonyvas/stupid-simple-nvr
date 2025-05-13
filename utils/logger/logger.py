import os
from datetime import datetime

class Logger:
    def __init__(self, logfile):
        self._logfile = logfile
        self._created = False

    def _log(self, message):
        message = f'{datetime.now().isoformat()} - {message}'
        print(message)

        if not self._created:
            os.makedirs(os.path.dirname(self._logfile), exist_ok=True)
            self._created = True

        with open(self._logfile, 'a') as f:
            f.write(message + '\n')

    def log_info(self, message):
        self._log(f'INFO: {message}')

    def log_error(self, message):
        self._log(f'ERROR: {message}')

    def log_warning(self, message):
        self._log(f'WARNING: {message}')