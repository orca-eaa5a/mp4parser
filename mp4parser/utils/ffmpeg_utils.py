import os
import hashlib
import subprocess
FFMPEG_PATH = "ffmpeg"

def ffmpeg_sync(media_file, trim_result, synced=True):
    vide = trim_result['vide']
    soun = trim_result['soun']
    sync_delay = 0.0
    video_delay = True
    sp = 0.0
    if vide['start_point'] < soun['start_point']:
        sp = soun['start_point']
        sync_delay = soun['start_point'] - vide['start_point']
        video_delay = False
    else:
        sp = vide['start_point']
        sync_delay = vide['start_point'] - soun['start_point']

    if video_delay:
        ffmpeg_sync_cmd = "{ffmpeg_bin} -y -i {media_file} -itsoffset {ts} -i {media_file} -map 0:a -map 1:v -c copy {out_file}"
    else:
        ffmpeg_sync_cmd = "{ffmpeg_bin} -y -i {media_file} -itsoffset {ts} -i {media_file} -map 0:v -map 1:a -c copy {out_file}"

    f, ext = os.path.splitext(media_file)
    tmp_file_name = hashlib.sha256(f.encode()).hexdigest()
    out_file = "{}{}".format(tmp_file_name, ext)
    cmd = ffmpeg_sync_cmd.format(media_file=media_file, ts=sync_delay, out_file=out_file, ffmpeg_bin=FFMPEG_PATH)
    child = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = child.communicate()
    if not os.path.exists(out_file):
        return None, None

    return out_file, sp

def ffmpeg_cutoff_extra_times(media_file, sp, duration):
    f, ext = os.path.splitext(media_file)
    tmp_file_name = hashlib.sha256(f.encode()).hexdigest()
    out_file = "{}{}".format(tmp_file_name, ext)
    ffmpeg_cutoff_cmd = "{ffmpeg_bin} -y -ss {sp} -i {media_file} -c copy -t {duration} {out_file}"
    cmd = ffmpeg_cutoff_cmd.format(media_file=media_file, sp=sp, duration=duration, out_file=out_file, ffmpeg_bin=FFMPEG_PATH)
    
    child = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = child.communicate()
    if not os.path.exists(out_file):
        return None

    return out_file