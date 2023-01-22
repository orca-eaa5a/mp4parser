# from parser.iso import Mp4File
from io import BytesIO
from mp4parse import Mp4Parser
from mp4modifier import Mp4Modifier
from utils import *
from ffmpeg_utils import ffmpeg_trim, ffmpeg_cutoff_extra_times

from ctypes import *
if __name__ == '__main__':
    url = 'test.url.com'
    sp = '00:02:00.150'
    ep = '00:03:00.0'
    
    parser = Mp4Parser()
    parser.stream_parse(url)
    parser.make_samples_info()

    modifier = Mp4Modifier(parser)
    sp = conver_timestr_to_timestamp(sp)
    ep = conver_timestr_to_timestamp(ep)
    duration = ep - sp
    mp4_header, mdat, trim_result = modifier.livetrim(url, sp, ep + 1.0, True)

    # with open('./video.mp4', 'rb') as f:
    #     parser.set_binary(f)
    #     parser.parse()
    #     parser.make_samples_info()

    #     modifier = Mp4Modifier(parser)
    #     sp = conver_timestr_to_timestamp("15:12")
    #     ep = conver_timestr_to_timestamp("20:40")
    #     duration = ep - sp
    #     mp4_header, mdat, trim_result = modifier.trim(f, sp, ep + 1.0, True)
        
    with open('wow.mp4', 'wb') as f:
        f.write(mp4_header)
        f.write(mdat)
    
    o, m_sp = ffmpeg_trim('wow.mp4', trim_result)
    s_sp = sp - m_sp
    o = ffmpeg_cutoff_extra_times(o, s_sp, duration)

    pass