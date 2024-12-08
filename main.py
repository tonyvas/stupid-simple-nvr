#!/usr/bin/env python3

import os, sys, yaml, time, multiprocessing

from nvr import NVR

def setup_nvrs(storage_dirpath: str, configs: dict):
    if configs is None:
        return None

    nvrs = {}

    # Setup NVR for each monitor
    for name, config in configs.items():
        # Parse config
        source = config['source']
        segment_duration_s = config['segmentDurationSeconds']
        monitor_storage_dirpath = os.path.join(storage_dirpath, name)

        # Create NVR
        nvrs[name] = NVR(name, source, segment_duration_s, monitor_storage_dirpath)

    return nvrs

def start(storage_dirpath: str, max_storage_gb: float, monitor_configs: dict):
    nvrs = setup_nvrs(storage_dirpath, monitor_configs)
    procs = {}

    for name, nvr in nvrs.items():
        procs[name] = multiprocessing.Process(target=nvr.start)

    for name, proc in procs.items():
        proc.start()

if __name__ == '__main__':
    try:
        SCRIPT_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
        CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.yml')

        try:
            config = yaml.safe_load(open(CONFIG_FILE, 'r'))
        except FileNotFoundError as e:
            raise Exception(f'Config file at "{CONFIG_FILE}" does not exist!')
        except Exception as e:
            raise Exception(f'Failed to parse config: {e}')

        storage_dirpath = config['storage']
        max_storage_gb = config['maxDiskGB']
        monitors = config['monitors']

        start(storage_dirpath, max_storage_gb, monitors)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        exit(1)