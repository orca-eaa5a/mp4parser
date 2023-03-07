import requests
import logging

logging.getLogger().setLevel(logging.INFO)

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

def byterange_request(url, start_byte, end_byte):
    CHUNK_SIZE = 1024*1024*10 # 10mb request
    if end_byte < CHUNK_SIZE:
        CHUNK_SIZE = end_byte

    current_offset = start_byte
    _bin = b''
    if type(start_byte) != int or type(end_byte) != int:
        assert False
    while True:
        retry_cnt = 0
        end_offset = current_offset + CHUNK_SIZE - 1
        if current_offset + end_offset >= end_byte:
            end_offset = end_byte - 1
        while True:
            if retry_cnt >= 5:
                raise Exception("byterange_request failed: range: {}-{}".format(current_offset, end_offset))
            try:
                resp = requests.get(url=url, headers={
                    'Range': 'bytes={}-{}'.format(current_offset, end_offset)
                })
                # check status code is http 206 (partital content)
                if resp.status_code == 206 or resp.status_code == 200:
                    current_offset += len(resp.content)
                    _bin += resp.content
                    break
                else:
                    retry_cnt+=1
                    logging.info('byterange_request retry... {}'.format(retry_cnt))

            except requests.exceptions.HTTPError as http_err:
                logging.error("byterange_request invalid url: {}".format(http_err.response.status_code))
                raise conn_err
            except requests.exceptions.Timeout as tmout_err:
                logging.error("byterange_request timeout error: {}".format(str(tmout_err)))
                logging.info('byterange_request retry... {}'.format(retry_cnt))
                retry_cnt += 1
            except requests.exceptions.ConnectionError as conn_err:
                logging.error("byterange_request connection error: {}".format(str(conn_err)))
                raise conn_err
            except Exception as e:
                logging.error("byterange_request unknown error: {}".format(str(e)))
                raise e

        if current_offset >= end_byte:
            break
    
    return _bin