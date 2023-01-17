from parser.iso import *

def get_box_size(fp):
    sz = int.from_bytes(fp.read(4), byteorder='big')
    fp.read(-4, 1)
    return sz


