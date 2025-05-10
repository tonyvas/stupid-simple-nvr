#!/usr/bin/env python3

import os, sys, yaml, time, threading

from utils.logger import Logger
from utils.recorder import Recorder

SCRIPT_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
LOG_FILE = os.path.join(SCRIPT_DIR, 'loggers.log')
DEFAULT_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.yml')

logger = Logger(LOG_FILE)

def create_threads(targets:list):
    return [ threading.Thread(target=target, daemon=True) for target in targets ]

def start_threads(threads:list):
    for thread in threads:
        thread.start()

def join_threads(threads:list):
    for thread in threads:
        thread.join()

def setup_recorder(storage_dirpath:str, name:str, config:dict):
    try:
        SOURCE_KEY = 'source'
        SEGMENT_DURATION_KEY = 'segment-duration-sec'
        RECORD_AUDIO_KEY = 'record-audio'
        MAX_AGE_KEY = 'max-age-hours'
        MAX_DISK_KEY = 'max-disk-gb'

        monitor_dirpath = os.path.join(storage_dirpath, name)
        source = config[SOURCE_KEY]
        segment_duration_sec = int(config[SEGMENT_DURATION_KEY])
        record_audio = config[RECORD_AUDIO_KEY]
        max_age_sec = float(config[MAX_AGE_KEY]) * 3600 if config[MAX_AGE_KEY] is not None else None
        max_disk_bytes = float(config[MAX_DISK_KEY]) * 1e9 if config[MAX_DISK_KEY] is not None else None

        if segment_duration_sec <= 0:
            raise Exception(f'Segment duration cannot be negative or zero!')

        if max_age_sec is not None and max_age_sec < 0:
            raise Exception(f'Max age cannot be negative!')

        if max_disk_bytes is not None and max_disk_bytes < 0:
            raise Exception(f'Max disk cannot be negative!')

        return Recorder(monitor_dirpath, name, source, segment_duration_sec, record_audio, max_age_sec, max_disk_bytes)
    except Exception as e:
        raise Exception(f'Failed to setup recorder {name}: {e}')

def setup_recorders(config:dict):
    STORAGE_DIRPATH_KEY = 'storage'
    GLOBAL_MAX_DISK_KEY = 'max-disk-gb'
    MONITORS_KEY = 'monitors'

    try:
        storage_dirpath = config[STORAGE_DIRPATH_KEY]
        if not storage_dirpath.startswith('/'):
            storage_dirpath = os.path.join(SCRIPT_DIR, storage_dirpath)

        global_max_disk_gb = float(config[GLOBAL_MAX_DISK_KEY]) * 1e9

        recorders = {}
        for monitor_name, monitor_config in config[MONITORS_KEY].items():
            recorders[monitor_name] = setup_recorder(storage_dirpath, monitor_name, monitor_config)
        
        return recorders
    except Exception as e:
        raise Exception(f'Failed to setup recorders: {e}')

def check_disk_limits(recorders:list):
    logger.log_info('Checking global disk limits...')

def start_global_limit_checker(recorders:list, run_flag:threading.Event, idle_flag:threading.Event):
    while run_flag.is_set():
        try:
            idle_flag.clear()
            check_disk_limits(recorders)
        except Exception as e:
            logger.log_error(f'Failed to check global disk limit: {e}')
        finally:
            time.sleep(5)
            idle_flag.set()

def setup(config:dict):
    logger.log_info(f'Setting up NVR...')

    logger.log_info(f'Setting up recorders...')
    recorders = setup_recorders(config)

    is_running = threading.Event()
    is_checker_idle = threading.Event()

    limit_threads = create_threads([ lambda: start_global_limit_checker(recorders, is_running, is_checker_idle) ])
    recorder_start_threads = create_threads([ recorder.start for recorder in recorders.values() ])
    recorder_stop_threads = create_threads([ recorder.stop for recorder in recorders.values() ])

    def start():
        logger.log_info('Starting NVR...')

        if is_running.is_set():
            raise Exception(f'NVR is already running!')
        
        is_running.set()

        logger.log_info('Starting recorders...')
        start_threads(recorder_start_threads)
        
        logger.log_info('Starting global disk limit checker...')
        start_threads(limit_threads)

        logger.log_info('NVR has started!')

        join_threads([ *limit_threads, *recorder_start_threads ])

    def stop():
        logger.log_info('Stopping NVR...')
        is_running.clear()

        logger.log_info('Stopping recorders...')
        start_threads(recorder_stop_threads)
        join_threads(recorder_stop_threads)

        logger.log_info('Waiting for global disk limit checker to stop...')
        is_checker_idle.wait()

        logger.log_info('NVR has stopped!')

    return (start, stop)

if __name__ == '__main__':
    try:
        try:
            logger.log_info(f'Reading config from {DEFAULT_CONFIG_FILE}...')
            config = yaml.safe_load(open(DEFAULT_CONFIG_FILE, 'r'))
        except FileNotFoundError as e:
            raise Exception(f'Config file at "{DEFAULT_CONFIG_FILE}" does not exist!')
        except Exception as e:
            raise Exception(f'Failed to parse config: {e}')

        (start, stop) = setup(config)

        try:
            start()
            pass
        except KeyboardInterrupt as e:
            print(f'Received keyboard interrupt, stopping NVR!')
            stop()
        except Exception as e:
            raise Exception(f'Failed to start NVR!')
    except Exception as e:
        print(e)
        exit(1)
    finally:
        print('NVR has stopped!')