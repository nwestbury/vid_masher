import logging
import os

from database import Database
from splitter import combine_videos, split_video_vtt
from synthesizer import Synthesizer
from utils import clean_caption_text

class Masher:
    def __init__(self, debug=False):
        self.logger = logging.getLogger('mash')
        self.logger.setLevel(logging.DEBUG)
        self.db = Database(debug=debug)
        self.sythesizer = Synthesizer(debug=debug)

        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.root_dir = os.path.realpath(os.path.join(script_dir, '..'))
        self.syth_dir = os.path.join(self.root_dir, 'videos', 'syn')

        if not os.path.isdir(self.syth_dir):
            os.mkdir(self.syth_dir)

        if debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(stream_handler)

    def max_word_range(self, words, start_index, db_words):
        ranges = []

        possible_words = self.db.find_text_range(words[start_index])
        j = start_index

        self.logger.debug('Got %s words at first level for %s', len(possible_words), words[start_index])

        while possible_words:
            ranges.append(possible_words)

            j += 1
            if j >= len(words) or not db_words[j]:
                break

            filters = []
            for word_row in possible_words:
                _, caption_id, _, index, _ = word_row
                filters.append((caption_id, index+1))

            possible_words = self.db.find_text_range(words[j], caption_index_filters=filters)

        return ranges

    def lucky_check(self, ranges):
        for i in range(len(ranges)-1, -1, -1):
            range_size = i+1
            for word_row in ranges[i]:
                _, caption_id, _, _, length = word_row
                if length == range_size: # happy !!! :)
                    return {
                        'name': 'clip',
                        'caption_id': caption_id,
                        'size': range_size,
                    }
        return None

    def generate_action_plan(self, text):
        clean = clean_caption_text(text).replace('.', '')
        words = clean.split(' ')
        existing_words = self.db.find_existing_words(words)
        db_words = [word in existing_words for word in words]

        self.logger.debug('Starting long search for "%s"', clean)
        self.logger.debug('DB WORDS: %s', ','.join(str(x) for x in db_words))

        i = 0
        # 's' -> sythesize, 'c' -> got full clip, 'g' -> split clip needed
        actions = []
        while i < len(words):
            if db_words[i]:
                word_ranges = self.max_word_range(words, i, db_words)
                full_clip = self.lucky_check(word_ranges)

                if full_clip is not None:
                    skipped_words = words[i:i+full_clip['size']]
                    self.logger.debug('--> F*** yes! We got lucky, %s skipped (%s)! :)', full_clip['size'], ' '.join(skipped_words))
                    actions.append(full_clip)
                    i += full_clip['size']
                else:
                    self.logger.debug('--> Lots of work ahead for %s clips', word_ranges)
                    actions.append({
                        'name': 'generate',
                        'ranges': word_ranges,
                    })
                    i += len(word_ranges)
            else:
                range_start = i
                while i < len(words) and not db_words[i]:
                    i += 1

                self.logger.debug('--> Sythesizing %d word(s)', i-range_start)
                actions.append({
                    'name': 'sythesize',
                    'words': words[range_start:i],
                })

        return actions

    def sythesize_words(self, words):
        clips = []
        for i in range(0, len(words), 2):
            text = ' '.join(words[i:i+2])
            video_path = os.path.join('videos', 'syn', '{}.mp4'.format(text))
            full_path = os.path.join(self.root_dir, video_path)

            print(text, full_path)
            duration = self.sythesizer.sythesize_word(text, full_path)
            self.db.insert_syn(text, video_path, duration)
            clips.append(full_path)
        return clips

    def fetch_clip(self, caption_id):
        self.logger.debug('Fetching %s', caption_id)
        realtive_video_path, start_t, end_t, relative_clip_path = self.db.find_caption_info(caption_id)

        full_clip_path = os.path.join(self.root_dir, relative_clip_path)
        if not os.path.isfile(full_clip_path):
            self.logger.debug('Spliting %s...', caption_id)
            full_video_path = os.path.join(self.root_dir, realtive_video_path)
            split_video_vtt(full_video_path, start_t, end_t, full_clip_path)

        return full_clip_path

    def acquire_clips(self, actions):
        self.logger.debug('Acquiring clips for %s actions', len(actions))
        clips = []
        for action in actions:
            if action['name'] == 'sythesize':
                clips += self.sythesize_words(action['words'])
            elif action['name'] == 'clip':
                clips.append(self.fetch_clip(action['caption_id']))
        return clips

    def merge_clips(self, clips, output):
        self.logger.debug('Merging %s clips...', len(clips))
        combine_videos(clips, output)
        print('Done! :) Check {}'.format(output))

    def mash(self, text, output):
        actions = self.generate_action_plan(text)
        clips = self.acquire_clips(actions)
        self.merge_clips(clips, output)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Mash YouTube Clips ;)')
    parser.add_argument('text', help='text')
    parser.add_argument('output', help='MP4 file path (default: "out.mp4")',
                        nargs='?', default='out.mp4')
    parser.add_argument('--debug', action='store_true', default=False)
    args = parser.parse_args()

    m = Masher(debug=args.debug)
    m.mash(args.text, args.output)

