from collections import deque
from io import BytesIO, BufferedReader
from .parser.iso import *
from .utils.utils import byterange_request

import logging

logging.getLogger().setLevel(logging.INFO)

class Mp4Parser(object):
    def __init__(self) -> None:
        self.fp = None
        self.duration = 0
        self.ftyp = None
        self.moov = None
        self.mvhd = None
        self.mdat = None
        self.track_type = {}
        self.tracks = {}
        pass

    def set_binary(self, fp):
        """
        set target binary to parsing
        -----------------------------
        Args:
            fp (_io.BufferedReader):
                Readable Buffer or byte or bytearray
        """
        ty = type(fp)
        if ty == BufferedReader:
            fp = BytesIO(fp.read())
        elif ty == bytes or ty == bytearray:
            fp = BytesIO(fp)
        elif ty == BytesIO:
            pass
        else:
            return False
        
        self.fp = fp

        return True

    def get_ftypbox_size(self, raw):
        return int.from_bytes(raw[:4], byteorder="big")

    def get_moovbox_size(self, raw, offset=24):
        return int.from_bytes(raw[offset:offset+4], byteorder="big")

    def stream_parse(self, url):
        _raw = byterange_request(url, 0, 40)
        ftyp_sz = self.get_ftypbox_size(_raw)
        moov_sz = self.get_moovbox_size(_raw, ftyp_sz)
        del _raw
        _raw = BytesIO(byterange_request(url, 0, ftyp_sz + moov_sz))
    
        self.set_binary(_raw)
        self.parse_metadata()

    def binary_parse(self, file_path):
        with open(file_path, 'rb') as f:
            _raw = f.read(40)
            ftyp_sz = self.get_ftypbox_size(_raw)
            moov_sz = self.get_moovbox_size(_raw, ftyp_sz)
            del _raw
            f.seek(0, 0)
            _raw = BytesIO(f.read(ftyp_sz + moov_sz))
        self.set_binary(_raw)
        self.parse_metadata()

    def parse_metadata(self):
        if not self.fp:
            return False
        while True:
            current_header:Header = Header(self.fp)
            current_box:Mp4Box = box_factory(self.fp, current_header)

            setattr(self, current_box.type, current_box)

            if len(self.fp.read(4)) != 4 or current_box.size == 0:
                break
            else:
                self.fp.seek(-4, 1)

    def make_samples_info(self):
        """make samples information contained mp4 file
        ------------------------
        """

        mdats = self.mdat
        if not mdats:
            # binary only contains mp4 header
            pass
        # generate a sample list if there is a moov that contains traks N.B only ever 0,1 moov boxes
        moov = self.moov
        if moov:
            self.mvhd = moov.get_first_box_matched('mvhd', False)
            traks = moov.search_boxes_for_type('trak', False)
            for trak in traks:
                tkhd = trak.get_first_box_matched('tkhd', False)
                mdia = trak.get_first_box_matched('mdia', False)
                hdlr = mdia.get_first_box_matched('hdlr', False)
                mdhd = mdia.get_first_box_matched('mdhd', False)
                minf = mdia.get_first_box_matched('minf', False)
                stbl = minf.get_first_box_matched('stbl', False)
                stco = stbl.get_first_box_matched('stco', False)
                stsz = stbl.get_first_box_matched('stsz', False)
                stsc = stbl.get_first_box_matched('stsc', False)
                stts = stbl.get_first_box_matched('stts', False)

                if not stco:
                    stco = stbl.get_first_box_matched('co64', False)
                if not stsz:
                    stsz = stbl.get_first_box_matched('stz2', False)

                timescale = mdhd.box_info['timescale']
                trak_id = tkhd.box_info['track_ID']
                self.duration = self.mvhd.box_info['duration']/self.mvhd.box_info['timescale']
                chunk_offsets = stco.box_info['entry_list']
                sample_size_box = stsz
                if trak_id not in self.track_type:
                    self.track_type[trak_id] = hdlr.box_info['handler_type']
                    self.tracks[trak_id] = {
                        'trak': trak,
                        'chunks': deque()
                    }

                if sample_size_box.box_info['sample_size'] > 0:
                    sample_sizes = [{'entry_size': sample_size_box.box_info['sample_size']}]*sample_size_box.box_info['sample_count']
                else:
                    sample_sizes = sample_size_box.box_info['entry_list']

                sample_to_chunks = stsc.box_info['entry_list']
                s2c_index = 0
                next_run = 0
                stts_offset = 0
                stts_sum = stts.box_info['entry_list'][stts_offset]['sample_count']
                sample_idx = 0
                chunk_timestamp = 0.0
                for i, chunk in enumerate(chunk_offsets, start=1):
                    if i >= next_run:
                        samples_per_chunk = sample_to_chunks[s2c_index]['samples_per_chunk']
                        s2c_index += 1
                        next_run = sample_to_chunks[s2c_index]['first_chunk'] \
                            if s2c_index < len(sample_to_chunks) else len(chunk_offsets) + 1
                    if stts_sum <= sample_idx:
                        stts_offset += 1
                        stts_sum += stts.box_info['entry_list'][stts_offset]['sample_count']
                        
                    chunk_timestamp = sample_idx/(timescale/stts.box_info['entry_list'][stts_offset]['sample_delta'])
                    chunk_dict = {
                                    'track_ID': trak_id,
                                    'chunk_ID': i,
                                    'chunk_offset': chunk['chunk_offset'],
                                    'samples_per_chunk': samples_per_chunk,
                                    'chunk_samples': deque(),
                                    'timestamp': chunk_timestamp
                                }
                    sample_offset = chunk['chunk_offset']
                    for j, sample in enumerate(sample_sizes[sample_idx:sample_idx + samples_per_chunk], sample_idx + 1):
                        chunk_dict['chunk_samples'].append({
                            'sample_ID': j,
                            'size': sample['entry_size'],
                            'offset': sample_offset
                        })
                        sample_offset += sample['entry_size']
                    self.tracks[trak_id]['chunks'].append(chunk_dict)
                    sample_idx += samples_per_chunk