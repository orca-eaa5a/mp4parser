# from parser.iso import Mp4File
from mp4parse import Mp4Parser

from ctypes import *
if __name__ == '__main__':
    parser = Mp4Parser()
    with open('./video.mp4', 'rb') as f:
        parser.set_binary(f)
    parser.parse()
    parser.make_samples_info()
    parser.moov.get_first_box_matched('stco', True)