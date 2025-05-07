#!/usr/bin/env python3

import os, sys, yaml, time, threading

from utils.logger import Logger
from utils.recorder import Recorder

SCRIPT_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
LOG_FILE = os.path.join(SCRIPT_DIR, 'loggers.log')
DEFAULT_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.yml')

logger = Logger(LOG_FILE)

def run_batch(targets:list):
    threads = [ threading.Thread(target=target, daemon=True) for target in targets ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

def setup_recorders(storage_dirpath:str, monitor_configs:dict):
    try:
        SOURCE_KEY = 'source'
        SEGMENT_DURATION_KEY = 'segment-duration-sec'
        MAX_AGE_KEY = 'max-age-hours'
        MAX_DISK_KEY = 'max-disk-gb'

        recorders = {}

        for name, config in monitor_configs.items():
            monitor_dirpath = os.path.join(storage_dirpath, name)
            source = config[SOURCE_KEY]
            segment_duration_sec = int(config[SEGMENT_DURATION_KEY])
            max_age_hours = float(config[MAX_AGE_KEY]) * 3600 if config[MAX_AGE_KEY] is not None else None
            max_disk_gb = float(config[MAX_DISK_KEY]) * 1e9 if config[MAX_DISK_KEY] is not None else None

            recorders[name] = Recorder(monitor_dirpath, name, source, segment_duration_sec, max_age_hours, max_disk_gb)

        return recorders
    except Exception as e:
        raise Exception(f'Failed to setup recorders: {e}')

def setup(config:dict):
    STORAGE_DIRPATH_KEY = 'storage'
    GLOBAL_MAX_DISK_KEY = 'max-disk-gb'
    MONITORS_KEY = 'monitors'

    try:
        storage_dirpath = config[STORAGE_DIRPATH_KEY]
        global_max_disk_gb = float(config[GLOBAL_MAX_DISK_KEY]) * 1e9
        
        return setup_recorders(storage_dirpath, config[MONITORS_KEY])
    except Exception as e:
        raise Exception(f'Failed to setup: {e}')

if __name__ == '__main__':
    try:
        logger.log_info('Starting NVR...')
        
        try:
            logger.log_info(f'Reading config from {DEFAULT_CONFIG_FILE}...')
            config = yaml.safe_load(open(DEFAULT_CONFIG_FILE, 'r'))
        except FileNotFoundError as e:
            raise Exception(f'Config file at "{DEFAULT_CONFIG_FILE}" does not exist!')
        except Exception as e:
            raise Exception(f'Failed to parse config: {e}')

        logger.log_info(f'Setting up recorders...')
        recorders = setup(config)

        try:
            logger.log_info(f'Starting recorders...')
            run_batch([ recorder.start for recorder in recorders.values() ])
        except KeyboardInterrupt as e:
            logger.log_info(f'Received keyboard interrupt, stopping recorders...')
            run_batch([ recorder.stop for recorder in recorders.values() ])
        except Exception as e:
            raise Exception(f'Failed to start recorders!')
    except Exception as e:
        logger.log_error(f'{e}')
        exit(1)
    finally:
        logger.log_info('NVR has stopped!')