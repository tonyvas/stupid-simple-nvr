import threading, subprocess, os, psutil, shutil
from time import sleep

from ..logger import Logger

class Recorder:
    def __init__(self, storage_dirpath:str, name:str, source:str, segment_duration_sec:int, record_audio:bool=True, max_age_hours:float|None=None, max_disk_gb:float|None=None):
        self._storage_dirpath = storage_dirpath
        self._name = name
        self._source = source
        self._segment_duration_sec = segment_duration_sec
        self._record_audio = record_audio
        self._max_age_hours = max_age_hours
        self._max_disk_gb = max_disk_gb

        self._is_running = False

        self._threads = [
            threading.Thread(target=self._start_limit_checker, daemon=True),
            threading.Thread(target=self._start_video_mover, daemon=True),
            threading.Thread(target=self._start_ffmpeg, daemon=True),
        ]
        self._ffmpeg = None

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

            for thread in self._threads:
                thread.join()

            self._log_info('Recorder started!')
        except Exception as e:
            message = f'Failed to start: {e}'
            self._log_error(message)
            raise Exception(message)

    def stop(self):
        try:
            self._log_info('Stopping recorder...')

            # Clear flag
            self._is_running = False

            if self._ffmpeg is not None:
                # Stop FFmpeg subprocess if it is running
                self._log_info('Terminating FFmpeg subprocess...')
                self._ffmpeg.terminate()
                self._ffmpeg.wait()

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

    def _start_limit_checker(self):
        self._log_info(f'Starting limit checker...')

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

    def _start_video_mover(self):
        self._log_info(f'Starting video mover...')

        # Create directories if needed
        os.makedirs(self._temp_dirpath, exist_ok=True)
        os.makedirs(self._video_dirpath, exist_ok=True)

        while self.is_running():
            try:
                # For each completed .mkv file
                for temp_mkv_path in self._get_completed_temp_videos():
                    self._log_info(f'Moving {os.path.basename(temp_mkv_path)}...')

                    # Get temp and final .mp4 paths
                    temp_mp4_path = temp_mkv_path.replace('.mkv', '.mp4')
                    final_mp4_path = os.path.join(self._video_dirpath, os.path.basename(temp_mp4_path))

                    # Convert temp mkv to mp4
                    self._mkv_to_mp4(temp_mkv_path, temp_mp4_path)
                    # Move mp4 from temp to final directory
                    shutil.move(temp_mp4_path, final_mp4_path)
                    # Delete original temp mkv
                    os.remove(temp_mkv_path)
            except Exception as e:
                self._log_error(f'Failed to run mover: {e}')
            finally:
                sleep(5)

    def _get_completed_temp_videos(self):
        # List of files ending in .mkv
        filepaths = []
        for filename in sorted(os.listdir(self._temp_dirpath)):
            if not filename.endswith('.mkv'):
                continue

            filepaths.append(os.path.join(self._temp_dirpath, filename))

        # Return all filenames except the last
        return filepaths[:-1]

    def _mkv_to_mp4(self, input_path, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        ffmpeg_cmd = [
            'ffmpeg',
            '-loglevel', 'error',
            '-threads', '2',
            '-i', input_path,
            '-c', 'copy',
            '-y', output_path
        ]

        proc = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            stderr = proc.stderr.decode('utf-8')
            raise Exception(f'Failed to convert MKV to MP4: {stderr}')

    def _start_ffmpeg(self):
        ffmpeg_cmd = self._generate_ffmpeg_command()
        os.makedirs(self._temp_dirpath, exist_ok=True)

        while self.is_running():
            try:
                self._log_info(f'Starting FFmpeg subprocess...')

                self._ffmpeg = subprocess.Popen(ffmpeg_cmd, text=True, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                while self._ffmpeg.poll() is None:
                    line = self._ffmpeg.stderr.readline().rstrip()
                    if line:
                        self._log_info(f'FFmpeg: {line}')
            except Exception as e:
                self._log_error(f'Failed to run FFmpeg subprocess: {e}')
            finally:
                sleep(5)

    def _generate_ffmpeg_command(self):
        RTSP_ARGS = ['-rtsp_transport', 'tcp']
        LOG_ARGS = ['-loglevel', 'error']
        INPUT_ARGS = ['-i', self._source]
        VCODEC_ARGS = ['-c:v', 'copy']
        ACODEC_ARGS = ['-c:a', 'aac']
        NO_ACODEC_ARGS = ['-an']
        SEGMENT_ARGS = [
            '-f', 'segment',
            '-segment_time', str(self._segment_duration_sec),
            '-strftime', '1',
            '-segment_atclocktime', '1',
            '-reset_timestamps', '1'
        ]
        OUTPUT_ARGS = ['-y', os.path.join(self._temp_dirpath, '%F_%H-%M-%S.mkv')]

        cmd = ['ffmpeg']

        for arg_list in [ RTSP_ARGS, LOG_ARGS, INPUT_ARGS, VCODEC_ARGS ]:
            for arg in arg_list:
                cmd.append(arg)
        
        if self._record_audio:
            for arg in ACODEC_ARGS:
                cmd.append(arg)
        else:
            for arg in NO_ACODEC_ARGS:
                cmd.append(arg)

        for arg_list in [ SEGMENT_ARGS, OUTPUT_ARGS ]:
            for arg in arg_list:
                cmd.append(arg)

        return cmd

    def _check_storage_limit(self):
        if self._max_disk_gb is None:
            return

    def _check_age_limit(self):
        if self._max_age_hours is None:
            return

    def _prune_oldest(self):
        pass

    def _get_oldest_video(self):
        pass