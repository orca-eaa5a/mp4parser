from mp4parser.utils.utils import *
from mp4parser.utils.ffmpeg_utils import *
from mp4parser.mp4modifier import Mp4Modifier
from mp4parser.mp4parse import Mp4Parser

import re
import gc
import psutil
import hashlib

import time

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
    # import ssl
    # from pytube import YouTube
    # ssl._create_default_https_context = ssl._create_unverified_context

    # yt = YouTube('https://www.youtube.com/watch?v=4S27MSw92XY&t=11169s')
    # stream = yt.streams.filter(progressive=True, file_extension='mp4')

    memory_usage("program start")
    # https://www.youtube.com/watch?v=MfXh1guvZp0
    # video_url = "https://rr2---sn-n3cgv5qc5oq-bh26r.googlevideo.com/videoplayback?expire=1677175578&ei=ulb3Y4fjLpndrQSd34TICQ&ip=211.215.4.208&id=o-AD7qpCnPBi2-nEN67dHXAOtnmQqYQ3mK5tnyBNxa6LXs&itag=22&source=youtube&requiressl=yes&mh=7l&mm=31%2C26&mn=sn-n3cgv5qc5oq-bh26r%2Csn-oguesn6d&ms=au%2Conr&mv=m&mvi=2&pl=17&initcwndbps=1270000&vprv=1&mime=video%2Fmp4&cnr=14&ratebypass=yes&dur=33397.051&lmt=1675512405060367&mt=1677153666&fvip=2&fexp=24007246&c=ANDROID&txp=6318224&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cvprv%2Cmime%2Ccnr%2Cratebypass%2Cdur%2Clmt&sig=AOq0QJ8wRQIgFXFH3qwaKzfi1LgHO8v_OWlyr_lQRO-HF7LUzze03cgCIQCz1OZJvdHsz7O1PcrYPhXKFTXL0nx3SuwIQxigIxj19Q%3D%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Cinitcwndbps&lsig=AG3C_xAwRQIgcR23i6zJ2lLTO60hsaaDCMHa5JdeLdMkeIpghWowGMUCIQC9u05bEeFOjAkFzWMXpcTDsGLdbB2knbokfINISgdSdQ%3D%3D"
    # sp = "09:13:30"
    # ep = "09:16:37"
    # video_url = "https://rr2---sn-3pm7knee.googlevideo.com/videoplayback?expire=1677443653&ei=5W37Y5L7NtG_vcAP1uiX2AM&ip=3.36.13.247&id=o-AH67Jil8k9PAHGACixYWZftGFV6j0MFevmG2nqD_66MW&itag=22&source=youtube&requiressl=yes&mh=jo&mm=31%2C29&mn=sn-3pm7knee%2Csn-3pm7dner&ms=au%2Crdu&mv=m&mvi=2&pl=14&initcwndbps=912500&vprv=1&mime=video%2Fmp4&cnr=14&ratebypass=yes&dur=9191.061&lmt=1671379875882095&mt=1677421758&fvip=1&fexp=24007246&c=ANDROID&txp=7318224&sparams=expire%2Cei%2Cip%2Cid%2Citag%2Csource%2Crequiressl%2Cvprv%2Cmime%2Ccnr%2Cratebypass%2Cdur%2Clmt&sig=AOq0QJ8wRQIhAJMPjkrmM7JSeqei9ue2mVfLhMr7eBEh1fib38lbeB1IAiBz0hoAw-VDdSGsTmu1ahgxSAk34lWurhFAaJsuWeqb2w%3D%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Cinitcwndbps&lsig=AG3C_xAwRAIgHJ5R4ool7zIfqb5EXKq9fsFeiNif_y3NbFyRTSiptEICIHPQkGhInnzt6v33m1FKd_Qlj5ofuAvzoBRrwkVdo5En"

    sp = "00:14:12"
    ep = "00:24:00"
    sp = conver_timestr_to_timestamp(sp)
    ep = conver_timestr_to_timestamp(ep)
    file_path = "./test.mp4"
    memory_usage("before parse")

    parser = Mp4Parser()
    print("Mp4 parse start")
    st = time.time()
    parser.binary_parse(file_path)
    ed = time.time()
    print("Mp4 parse finished.. duration : {}".format(ed-st))

    print("Mp4 create samples info start")
    st = time.time()
    parser.make_samples_info()
    ed = time.time()
    print("Mp4 create samples info finished.. duration : {}".format(ed-st))
    
    modifier = Mp4Modifier(parser)
    
    memory_usage("after parse")

    duration = ep - sp
    
    print("Mp4 trim start")
    st = time.time()
    mp4_header, mdat, trim_result = modifier.data_trim(file_path, sp, ep + 1.0, True)
    ed = time.time()
    print("Mp4 trim start finished.. duration : {}".format(ed-st))

    memory_usage("after stream")
    raw = mp4_header + mdat
    memory_usage("after concat")
    del mp4_header
    del mdat
    memory_usage("after del#1")

    tmp_file_name = hashlib.sha256(file_path.encode()).hexdigest() + ".mp4"
    tmp_file_path = write_at_lambda_storage(tmp_file_name, raw)
    tmp_file_name2 = "./tmp/{}".format(hashlib.sha256(tmp_file_name.encode()).hexdigest() + ".mp4")
    out_file, m_sp = ffmpeg_sync(tmp_file_path, tmp_file_name2, trim_result)
    tmp_file_name2 = "./tmp/{}".format(hashlib.sha256(out_file.encode()).hexdigest() + ".mp4")
    out_file = ffmpeg_cutoff_extra_times(out_file, tmp_file_name2, sp - m_sp, duration)
    memory_usage("before del#2")

    del modifier
    del parser
    
    memory_usage("after del#2")

    print(gc.collect())

    memory_usage("before gc")
    pass
    pass