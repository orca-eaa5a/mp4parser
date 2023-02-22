from mp4parser.utils.utils import *
from mp4parser.utils.ffmpeg_utils import *
from mp4parser.mp4modifier import Mp4Modifier
from mp4parser.mp4parse import Mp4Parser

import gc
import psutil
import hashlib

def write_at_lambda_storage(file_name, raw):
    tmp_file_path = os.path.join('./tmp', file_name)
    
    with open(tmp_file_path, 'wb') as f:
        f.write(raw)

    return tmp_file_path

def memory_usage(message: str = 'debug'):
    # current process RAM usage
    p = psutil.Process()
    rss = p.memory_info().rss / 2 ** 20 # Bytes to MB
    print(f"[{message}] memory usage: {rss: 10.5f} MB")

if __name__ == '__main__':

    memory_usage("program start")

    video_url = "https://rr1---sn-3pm7dned.googlevideo.com/videoplayback?expire=1677091089&ei=sQz2Y7fDHI-Rs8IP99yjqA0&ip=3.37.127.142&id=o-ADR7FSJ2K_YSe_Sxgty5r0xI4yLHTt48rflYwiq6_Ij4&itag=22&source=youtube&requiressl=yes&mh=9_&mm=31%2C29&mn=sn-3pm7dned%2Csn-3pm7knel&ms=au%2Crdu&mv=m&mvi=1&pl=24&initcwndbps=527500&vprv=1&mime=video%2Fmp4&cnr=14&ratebypass=yes&dur=30950.574&lmt=1675024506598428&mt=1677069226&fvip=5&fexp=24007246&c=ANDROID&txp=5432434&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cvprv%2Cmime%2Ccnr%2Cratebypass%2Cdur%2Clmt&sig=AOq0QJ8wRgIhAJ1kyfsNoARTLS8JqNYsDlTdJQq224MShfdFNxrC9aHwAiEA1AsS7M7umxfE-hK58L0KL9F2arPmceHiQlSUyLTdrMw%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Cinitcwndbps&lsig=AG3C_xAwRgIhAM2MjgjBkq0HMOHBAnGHbFAJ2gdPSB9FdIRIuRQWcuNhAiEAwLGimq_zUTVdSRMd9XyDpDFJfKfF37PCTWik5YD0q5o%3D"
    sp = "02:18:13.000"
    ep = "02:20:13.000"

    sp = conver_timestr_to_timestamp(sp)
    ep = conver_timestr_to_timestamp(ep)
    
    memory_usage("before parse")

    parser = Mp4Parser()
    parser.stream_parse(video_url)
    parser.make_samples_info()
    modifier = Mp4Modifier(parser)
    
    memory_usage("after parse")

    duration = ep - sp

    mp4_header, mdat, trim_result = modifier.livetrim(video_url, sp, ep + 1.0, True)


    memory_usage("after stream")
    raw = mp4_header + mdat
    memory_usage("after concat")
    del mp4_header
    del mdat
    memory_usage("after del#1")

    tmp_file_name = hashlib.sha256(video_url.encode()).hexdigest() + ".mp4"
    tmp_file_path = write_at_lambda_storage(tmp_file_name, raw)
    out_file, m_sp = ffmpeg_sync(tmp_file_path, trim_result)
    out_file = ffmpeg_cutoff_extra_times(out_file, sp - m_sp, duration)
    memory_usage("before del#2")

    del modifier
    del parser
    
    memory_usage("after del#2")

    print(gc.collect())

    memory_usage("before gc")
    pass
    pass