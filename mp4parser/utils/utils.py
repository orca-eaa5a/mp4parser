import requests

def conver_timestr_to_timestamp(time_str):
    timestamp, _pow = 0, 0
    try:
        time_arr = [float(f) for f in time_str.split(':')]
    except ValueError as ve:
        assert False
    time_arr.reverse()
    for t in time_arr:
        timestamp += pow(60, _pow) * t
        _pow += 1
    del time_arr

    return timestamp