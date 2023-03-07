
from .mp4parse import Mp4Parser
from bisect import bisect_left, bisect_right
import struct
from .utils.utils import byterange_request

class KeyWrapper:
    def __init__(self, iterable, key):
        self.it = iterable
        self.key = key

    def __getitem__(self, i):
        return self.key(self.it[i])

    def __len__(self):
        return len(self.it)

class Mp4Modifier(object):
    def __init__(self, parser:Mp4Parser) -> None:
        """
        Args:
            chunks (list): mp4 parser chunks list
        """
        self.parser = parser
        self.moov = parser.moov
        # self.chunks = parser.chunks
        pass
    def compile_mdat(self, raw):
        return struct.pack(">I", len(raw)+8) + b'mdat' + raw
    
    def get_closest_chunk_right(self, timestamp, trak_id):
        """시각 값에 해당하는 trak의 chunk를 가져옵니다.
        요청한 시각과 일치하는 chunk가 없을 경우, 
        요청한 timestamp "이후"의 시간 값을 가진 chunk 중 가장 가까운 chunk를 가져옵니다.
        """
        chunks = self.parser.tracks.get(trak_id)['chunks']
        bslindex = bisect_left(KeyWrapper(chunks, key=lambda chunk: chunk['timestamp']), timestamp)
        if bslindex == len(chunks):
            bslindex -=1
        return chunks[bslindex]

    def get_chunk_by_time_left(self, timestamp, trak_id, sync=False):
        """시각 값에 해당하는 trak의 chunk를 가져옵니다.
        요청한 시각과 일치하는 chunk가 없을 경우, 
        요청한 timestamp "이후"의 시간 값을 가진 chunk 중 가장 가까운 chunk를 가져옵니다.
        sync:
        iframe을 고려하여 chunk를 가져옵니다.
        요청한 시각 값에 해당하는 chunk에 iframe이 포함되어있지 않을 경우, 시각 값보다 선행하는
        chunk 중, iframe을 포함하는 chunk를 반환합니다.
        -

        Args:
            timestamp (_type_): 시각 값
            trak_id (_type_): vide or sond track type id
            sync (bool, optional):
        """
        stss = None
        chunks = self.parser.tracks.get(trak_id)['chunks']
        if sync:
            for k, v in self.parser.track_type.items():
                if v == 'vide':
                    trak = self.parser.tracks.get(k)['trak']
                    stss = trak.get_first_box_matched('stss', True)
        if sync and not stss:
            # no stss, sync is impossible
            sync = False
        
        bslindex = bisect_left(KeyWrapper(chunks, key=lambda chunk: chunk['timestamp']), timestamp)

        if sync:
            idx = bslindex
            # 요청한 시각 값에 해당하는 chunk에 iframe이 포함되어있지 않을 경우, 시각 값보다 선행하는
            # chunk 중, iframe을 포함하는 chunk를 반환합니다.
            while idx >= 0:
                chunk = chunks[idx]
                first_sample_idx = chunk['chunk_samples'][0]['sample_ID']-1
                
                nearest_iframe_left = bisect_left(KeyWrapper(stss.box_info['entry_list'], key=lambda etry: etry['sample_number']), first_sample_idx)
                if nearest_iframe_left > 1:
                    nearest_iframe_left -= 1
                nearest_iframe_right = bisect_right(KeyWrapper(stss.box_info['entry_list'], key=lambda etry: etry['sample_number']), first_sample_idx + chunk['samples_per_chunk'])
                for etry in stss.box_info['entry_list'][nearest_iframe_left:nearest_iframe_right+1]:
                    if first_sample_idx <= etry['sample_number'] and \
                            etry['sample_number'] < first_sample_idx + chunk['samples_per_chunk']:
                        return chunk
                idx -= 1
            raise Exception("Can't find iframe chunk")
        else:
            if chunks[bslindex] > timestamp and bslindex > 1:
                bslindex-=1
        
        return chunks[bslindex]

    def modify_header_for_trim(self, start_point, end_point, sync=True):
        start_timestamp = start_point
        end_timestamp = end_point
        trim_result = {
            'req_start_time': start_timestamp,
            'req_end_time': end_timestamp,
            # 'video_track': { 'res_start_time': 0, 'res_end_time': 0 },
            # 'sound_track':{ 'res_start_time': 0, 'res_end_time': 0 }
        }

        if end_timestamp > self.parser.duration:
            end_timestamp = self.parser.duration

        if sync:
            chunk_s = None
            chunk_e = None
            for trak_id, handler_type in self.parser.track_type.items():
                if handler_type == 'vide':
                    chunk_s = self.get_chunk_by_time_left(timestamp=start_timestamp, trak_id=trak_id, sync=True)
                chunk_e = self.get_closest_chunk_right(timestamp=end_timestamp, trak_id=trak_id)
                if chunk_s:
                    break
            start_timestamp = chunk_s['timestamp']
            end_timestamp = chunk_e['timestamp']

        duration = end_timestamp - start_timestamp

        read_start_offset = 0xffffffffffffffff
        read_end_offset = -1

        self.parser.mvhd.edit_duration(duration)
        for trak_id, handler_type in self.parser.track_type.items():
            chunk_s = self.get_closest_chunk_right(
                timestamp=start_timestamp,
                trak_id=trak_id
            )
            chunk_e = self.get_closest_chunk_right(
                timestamp=end_timestamp,
                trak_id=trak_id
            )
            if chunk_s['chunk_offset'] < read_start_offset:
                read_start_offset = chunk_s['chunk_offset']
            if chunk_e['chunk_offset'] > read_end_offset:
                read_end_offset = chunk_e['chunk_offset']

            if not handler_type in trim_result:
                trim_result[handler_type] = { 
                    'start_point': chunk_s['timestamp'],
                    'end_point': chunk_e['timestamp']
                }
            trak = self.parser.tracks.get(trak_id)['trak']
            
            # edit track duration
            timescale = self.parser.mvhd.box_info['timescale']
            tkhd = trak.get_first_box_matched('tkhd', False)
            mdhd = trak.get_first_box_matched('mdhd', True)
            stts = trak.get_first_box_matched('stts', True)
            stsc = trak.get_first_box_matched('stsc', True)
            stco = trak.get_first_box_matched('stco', True)
            if not stco:
                stco = trak.get_first_box_matched('co64', True)
            stsz = trak.get_first_box_matched('stsz', True)

            tkhd.edit_duration(duration, timescale)
            mdhd.edit_duration(duration)

            first_sample_idx = chunk_s['chunk_samples'][0]['sample_ID'] - 1
            last_sample_idx = chunk_e['chunk_samples'][0]['sample_ID'] - 1
            start_chunk_id = chunk_s['chunk_ID'] - 1
            end_chunk_id = chunk_e['chunk_ID'] - 1
            
            # edit_stts
            ## 1. remove the out ranged samples
            #### 1. remove right first
            off = 0
            for i, etry in enumerate(stts.box_info['entry_list']):
                if (off + etry['sample_count']) > last_sample_idx:
                    etry['sample_count'] = last_sample_idx - off
                    break
                off += etry['sample_count']
            
            stts.box_info['entry_list'] = stts.box_info['entry_list'][:i+1]
            
            #### 2. remove left next
            number_of_samples_remove_left = first_sample_idx
            for i, etry in enumerate(stts.box_info['entry_list']):
                if etry['sample_count'] <= number_of_samples_remove_left:
                    number_of_samples_remove_left -= etry['sample_count']
                    etry['sample_count'] = 0
                else:
                    etry['sample_count'] -= number_of_samples_remove_left
                    break
                
            stts.box_info['entry_list'] = list(filter(lambda x: x['sample_count'] != 0, stts.box_info['entry_list']))
            stts.box_info['entry_count'] = len(stts.box_info['entry_list'])

            # edit_stco
            stco.box_info['entry_list'] = stco.box_info['entry_list'][start_chunk_id:end_chunk_id]
            stco.box_info['entry_count'] = len(stco.box_info['entry_list'])

            # edit_stsc
            stsc_etry_sz = len(stsc.box_info['entry_list'])

            closest_right = bisect_right(KeyWrapper(stsc.box_info['entry_list'], key=lambda etry: etry['first_chunk']), end_chunk_id)
            if closest_right == stsc_etry_sz:
                closest_right += 1
            stsc.box_info['entry_list'] = stsc.box_info['entry_list'][:closest_right]
            
            closest_left = bisect_left(KeyWrapper(stsc.box_info['entry_list'], key=lambda etry: etry['first_chunk']), start_chunk_id)
            if closest_left > 0:
                closest_left -= 1

            stsc.box_info['entry_list'] = stsc.box_info['entry_list'][closest_left:closest_right]
            
            for idx, etry in enumerate(stsc.box_info['entry_list']):
                etry['first_chunk'] -= start_chunk_id
                # stco.box_info['entry_count] => number of chunks
                if stco.box_info['entry_count'] <= etry['first_chunk']:
                    stsc.box_info['entry_list'] = stsc.box_info['entry_list'][:idx]
                    break
                if etry['first_chunk'] <= 0:
                    etry['first_chunk'] = 1
            
            stsc.box_info['entry_count'] = len(stsc.box_info['entry_list'])
            
            # edit_stsz
            stsz.box_info['entry_list'] = stsz.box_info['entry_list'][first_sample_idx:last_sample_idx]
            stsz.box_info['sample_count'] = len(stsz.box_info['entry_list'])

            stts.compile()
            stsc.compile()
            stco.compile()
            stsz.compile()

            if handler_type == 'vide':
                if sync:
                # edit_stss
                    stss = trak.get_first_box_matched('stss', True)
                    closest_left = bisect_left(KeyWrapper(stss.box_info['entry_list'], key=lambda etry: etry['sample_number']), first_sample_idx)
                    if closest_left > 0:
                        closest_left -= 1
                    closest_right = bisect_left(KeyWrapper(stss.box_info['entry_list'], key=lambda etry: etry['sample_number']), last_sample_idx)
                    slice_start = closest_left

                    for slice_end, etry in enumerate(stss.box_info['entry_list'][closest_left:closest_right+1]):
                        if etry['sample_number'] > last_sample_idx+1:
                            break
                        if etry['sample_number'] < first_sample_idx+1:
                            slice_start+=1

                    stss.box_info['entry_list'] = stss.box_info['entry_list'][slice_start: closest_left + slice_end]
                    stss.box_info['entry_count'] = len(stss.box_info['entry_list'])
                    for etry in stss.box_info['entry_list']:
                        etry['sample_number'] -= first_sample_idx
                    stss.compile()
                    
                ctts = trak.get_first_box_matched('ctts', True)
                if ctts:
                    # edit_ctts
                    sample_count = 0
                    for i, etry in enumerate(ctts.box_info['entry_list']):
                        sample_count += etry['sample_count']
                        if sample_count > first_sample_idx:
                            etry['sample_count'] = sample_count - first_sample_idx
                            break
                    ctts.box_info['entry_list'] = ctts.box_info['entry_list'][i:]

                    sample_count = 0
                    contained_sample = last_sample_idx - first_sample_idx
                    for i, etry in enumerate(ctts.box_info['entry_list']):
                        sample_count += etry['sample_count']
                        if sample_count >= contained_sample:
                            etry['sample_count'] = sample_count - contained_sample
                            break
                    
                    ctts.box_info['entry_list'] = ctts.box_info['entry_list'][:i]
                    ctts.box_info['entry_count'] = len(ctts.box_info['entry_list'])
                    ctts.compile()

        _raw = bytearray(bytes(self.parser.ftyp.raw))
        self.re_serialize(self.parser.moov, _raw, None)
        delta = read_start_offset
        for trak_id, handler_type in self.parser.track_type.items():
            trak = self.parser.tracks.get(trak_id)['trak']
            stco = trak.get_first_box_matched('stco', True)
            if not stco:
                stco = trak.get_first_box_matched('co64', True)
            for etry in stco.box_info['entry_list']:
                etry['chunk_offset'] = etry['chunk_offset'] - delta + len(_raw) + 8 # <-- mdat header
            stco.compile()
            _raw[stco.start_of_box:stco.start_of_box+len(stco.raw)] = stco.raw
        
        trim_result['start_offset'] = read_start_offset
        trim_result['end_offset'] = read_end_offset

        return _raw, trim_result

    def stream_trim(self, url, start_point, end_point, sync=True):
        headr_raw, trim_result = self.modify_header_for_trim(start_point, end_point, sync)
        mdat_raw = byterange_request(url, trim_result['start_offset'], trim_result['end_offset'])
        
        return headr_raw, self.compile_mdat(mdat_raw), trim_result
    
    def data_trim(self, file_path, start_point, end_point, sync=True):
        headr_raw, trim_result = self.modify_header_for_trim(start_point, end_point, sync)
        with open(file_path, 'rb') as f:
            f.seek(trim_result['start_offset'], 0)
            mdat_raw = f.read(trim_result['end_offset'] - trim_result['start_offset'])
        
        return headr_raw, self.compile_mdat(mdat_raw), trim_result


    def re_serialize(self, box, res, box_content):
        header_flag = False
        header_offset = -1
        """
        this can occur bug if size of Atom Header is not 8byte.
        """
        if len(box.raw) == 8 and box.size == int.from_bytes(box.raw[0:4], byteorder='big'):
            header_flag = True
            header_offset = len(res)
        
        # print("{} : {} {} -> {} {}"\
        #         .format(
        #             box.type, 
        #             box.start_of_box, 
        #             box.size, 
        #             len(res), 
        #             len(box.raw))
        #     )
        box.start_of_box = len(res)
        res += bytearray(box.raw)
        for child in box.children:
            self.re_serialize(child, res, box_content)

        if header_flag and header_offset > 0:
            # print(box.type)
            content_sz = len(res[header_offset:])
            if box.size != content_sz:
                res[header_offset:header_offset+4] = struct.pack(">I", content_sz)
                box.header.set_size(content_sz)

        return res
