#!/usr/bin/env python3

import os, sys, yaml, time, threading

from utils.logger import Logger
from utils.recorder import Recorder
from utils.limit_manager import LimitManager, RecorderLimitManager, GlobalLimitManager

SCRIPT_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
LOG_DIRPATH = os.path.join(SCRIPT_DIR, 'logs')
DEFAULT_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.yml')

main_logger = Logger(os.path.join(LOG_DIRPATH, 'main.log'))

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

        monitor_dirpath = os.path.join(storage_dirpath, name)
        source = config[SOURCE_KEY]
        segment_duration_sec = int(config[SEGMENT_DURATION_KEY])
        record_audio = config[RECORD_AUDIO_KEY]

        if segment_duration_sec <= 0:
            raise Exception(f'Segment duration cannot be negative or zero!')

        logger = Logger(os.path.join(LOG_DIRPATH, name, 'recorder.log'))

        return Recorder(logger, monitor_dirpath, name, source, segment_duration_sec, record_audio)
    except Exception as e:
        raise Exception(f'Failed to setup recorder {name}: {e}')

def setup_recorders(config:dict):
    STORAGE_DIRPATH_KEY = 'storage'
    MONITORS_KEY = 'monitors'

    try:
        storage_dirpath = config[STORAGE_DIRPATH_KEY]
        if not storage_dirpath.startswith('/'):
            storage_dirpath = os.path.join(SCRIPT_DIR, storage_dirpath)

        recorders = {}
        for monitor_name, monitor_config in config[MONITORS_KEY].items():
            recorders[monitor_name] = setup_recorder(storage_dirpath, monitor_name, monitor_config)
        
        return recorders
    except Exception as e:
        raise Exception(f'Failed to setup recorders: {e}')

def setup_limit_checkers(recorders:dict, config:dict):
    MONITORS_KEY = 'monitors'
    GLOBAL_MAX_DISK_KEY = 'max-disk-gb'
    RECORDER_MAX_AGE_KEY = 'max-age-hours'
    RECORDER_MAX_DISK_KEY = 'max-disk-gb'

    limit_checkers = []

    # Get global disk limit
    global_max_disk_bytes = config[GLOBAL_MAX_DISK_KEY] * 1e9
    if global_max_disk_bytes < 0:
        raise Exception(f'Global max disk limit cannot be negative!')

    for name, recorder in recorders.items():
        recorder_config = config[MONITORS_KEY][name]

        # Get recorder age and disk limits
        max_age_sec = float(recorder_config[RECORDER_MAX_AGE_KEY]) * 3600 if recorder_config[RECORDER_MAX_AGE_KEY] is not None else None
        if max_age_sec is not None and max_age_sec < 0:
            raise Exception(f'Max age cannot be negative!')

        max_disk_bytes = float(recorder_config[RECORDER_MAX_DISK_KEY]) * 1e9 if recorder_config[RECORDER_MAX_DISK_KEY] is not None else None
        if max_disk_bytes is not None and max_disk_bytes < 0:
            raise Exception(f'Max disk cannot be negative!')

        # Create recorder limit checker
        limit_logger = Logger(os.path.join(LOG_DIRPATH, name, 'limit.log'))
        limit_checkers.append(RecorderLimitManager(limit_logger, recorder, max_age_sec=max_age_sec, max_disk_bytes=max_disk_bytes))

    # Create global limit checker
    # Do this last so it checks after the individual recorders do their thing
    global_limit_logger = Logger(os.path.join(LOG_DIRPATH, 'limit.log'))
    limit_checkers.append(GlobalLimitManager(global_limit_logger, recorders.values(), max_disk_bytes=global_max_disk_bytes))

    return limit_checkers

def start_limit_checkers(limit_checkers:list[LimitManager], run_flag:threading.Event, idle_flag:threading.Event):
    while run_flag.is_set():
        idle_flag.clear()

        for limit_checker in limit_checkers:
            try:
                limit_checker.run()
            except Exception as e:
                main_logger.log_warning(f'Failed to check limits: {e}')

        time.sleep(5)
        idle_flag.set()

def setup(config:dict):
    main_logger.log_info(f'Setting up NVR...')

    main_logger.log_info(f'Setting up recorders...')
    recorders = setup_recorders(config)

    main_logger.log_info(f'Setting up limit checkers...')
    limit_checkers = setup_limit_checkers(recorders, config)

    is_running = threading.Event()
    are_checkers_idle = threading.Event()

    limit_threads = create_threads([ lambda: start_limit_checkers(limit_checkers, is_running, are_checkers_idle) ])
    recorder_start_threads = create_threads([ recorder.start for recorder in recorders.values() ])
    recorder_stop_threads = create_threads([ recorder.stop for recorder in recorders.values() ])

    def start():
        main_logger.log_info('Starting NVR...')

        if is_running.is_set():
            raise Exception(f'NVR is already running!')
        
        is_running.set()

        main_logger.log_info('Starting recorders...')
        start_threads(recorder_start_threads)
        
        main_logger.log_info('Starting limit checkers...')
        start_threads(limit_threads)

        main_logger.log_info('NVR has started!')

        join_threads([ *limit_threads, *recorder_start_threads ])

    def stop():
        main_logger.log_info('Stopping NVR...')
        is_running.clear()

        main_logger.log_info('Stopping recorders...')
        start_threads(recorder_stop_threads)
        join_threads(recorder_stop_threads)

        main_logger.log_info('Waiting for limit checkers to stop...')
        are_checkers_idle.wait()

        main_logger.log_info('NVR has stopped!')

    return (start, stop)

if __name__ == '__main__':
    try:
        try:
            main_logger.log_info(f'Reading config from {DEFAULT_CONFIG_FILE}...')
            config = yaml.safe_load(open(DEFAULT_CONFIG_FILE, 'r'))
        except FileNotFoundError as e:
            raise Exception(f'Config file at "{DEFAULT_CONFIG_FILE}" does not exist!')
        except Exception as e:
            raise Exception(f'Failed to parse config: {e}')

        try:
            (start, stop) = setup(config)
        except Exception as e:
            raise Exception(f'Failed to setup NVR: {e}')

        try:
            start()
        except KeyboardInterrupt as e:
            print(f'Received keyboard interrupt, stopping NVR!')
            stop()
        except Exception as e:
            raise Exception(f'Failed to start NVR: {e}')
    except Exception as e:
        print(e)
        exit(1)
    finally:
        print('NVR has stopped!')