from .. import datetime

class Logger:
    def __init__(self, logfile):
        self._logfile = logfile

    def _log(self, message):
        message = f'{datetime.get_datetime()} - {message}'

        print(message)
        # with open(self._logfile, 'a') as f:
        #     f.write(message + '\n')

    def log_info(self, message):
        self._log(f'INFO: {message}')

    def log_error(self, message):
        self._log(f'ERROR: {message}')