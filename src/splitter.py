import logging
import multiprocessing as mp
import moviepy.editor as mop
import re
import os

from utils import find_vtt_splits

def split_video_vtt(video_file, s, e, clip_path):
    # moviepy's ffmpeg_extract_subclip does not re-trancode the video
    # resulting in very choppy footage so we will run it ourselves (note this is quite expensive)
    cmd = (
        "ffmpeg -ss {ss:.3f} -i {file} -t {len:.3f} {out} -hide_banner -loglevel error -y"
    ).format(ss=s, file=video_file, len=e-s, out=clip_path)

    os.system(cmd)


def combine_videos(video_files, outfile):
    tmp_files = []
    for i, video_file in enumerate(video_files):
        tmp_file = 'tmp{}.ts'.format(i)
        os.system('ffmpeg -i {} -c copy -bsf:v h264_mp4toannexb -f mpegts {} -hide_banner -loglevel error -y'.format(video_file, tmp_file))
        tmp_files.append(tmp_file)

    os.system('ffmpeg -i "concat:{}" -c copy -bsf:a aac_adtstoasc {} -hide_banner -loglevel error -y tmp.mp4'.format('|'.join(tmp_files), outfile))
    os.system('ffmpeg -i tmp.mp4 -vf scale=720:480 -hide_banner -loglevel error -y {}'.format(outfile)) # force the scale to be 720x480
    os.system('rm tmp.mp4 {}'.format(' '.join(tmp_files)))

class Splitter:
    def __init__(self, debug=False, overwrite=False):
        self.logger = logging.getLogger('splitter')
        self.logger.setLevel(logging.DEBUG)

        self.overwrite = overwrite
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.video_dir = os.path.realpath(os.path.join(script_dir, '..', 'videos'))

        if debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(stream_handler)

    def split_base_videos(self):
        args = []
        for video_id in os.listdir(self.video_dir):
            base_dir = os.path.join(self.video_dir, video_id)
            files = os.listdir(base_dir)

            vtt_file = next((os.path.join(base_dir, f) for f in files if f.endswith('vtt')), None)
            video_file = next((os.path.join(base_dir, f) for f in files if f == video_id + '.mp4'), None)

            # if there is not exaclty a VTT and video file, ignore
            if len(files) < 2 or vtt_file is None or video_file is None:
                self.logger.debug('Skipping video folder (%s)', base_dir)
                continue

            splits = find_vtt_splits(vtt_file, base_dir)
            self.logger.debug('Found %d splits for %s', len(splits), base_dir)

            ignored = 0
            for split in splits:
                i, s, e, caption = split
                clip_path = os.path.join(base_dir, "clip{}.mp4".format(i))
                if self.overwrite or not os.path.isfile(clip_path):
                    args.append((video_file, s, e, clip_path))
                else:
                    ignored += 1

            if ignored:
                self.logger.debug('Ignoring %d/%d splits for (%s)', ignored, len(splits), base_dir)

        n_cpus = mp.cpu_count() - 1
        self.logger.debug('Starting to split %d segements on %d threads...', len(args), n_cpus)
        with mp.Pool(n_cpus) as p:
            p.starmap(split_video_vtt, args)

    
if __name__ == '__main__':
    s = Splitter(debug=True, overwrite=False)
    s.split_base_videos()
