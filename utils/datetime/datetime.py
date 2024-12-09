#!/usr/bin/env python3

from datetime import datetime

def get_date(separator = '-'):
    now = datetime.now()
    return separator.join([ f'{part:02}' for part in [ now.year, now.month, now.day ] ])

def get_time(separator = '-'):
    now = datetime.now()
    return separator.join([ f'{part:02}' for part in [ now.hour, now.minute, now.second ] ])

def get_datetime(date_sep = '-', datetime_sep = '_', time_sep = '-'):
    return datetime_sep.join([get_date(date_sep), get_time(time_sep)])

if __name__ == '__main__':
    print(f'Date: {get_date()}')
    print(f'Time: {get_time()}')
    print(f'Datetime: {get_datetime()}')