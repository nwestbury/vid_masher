import logging
import os

import youtube_dl

from youtube_api import youtube_list

class Downloader:
    def __init__(self, debug=False):
        self.logger = logging.getLogger('downloader')
        self.logger.setLevel(logging.DEBUG)

        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.output_dir = os.path.realpath(os.path.join(script_dir, '..', 'videos'))
        self.cache_dir = os.path.realpath(os.path.join(script_dir, '..', 'cache'))

        self.create_dir_if_not_exists(self.output_dir)
        self.create_dir_if_not_exists(self.cache_dir)

        if debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(stream_handler)

    def create_dir_if_not_exists(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)

    def get_channel_list_path(self, channel_id):
        return os.path.join(self.cache_dir, '{}.txt'.format(channel_id))

    def get_channel_subtitled_vids(self, channel_id):
        channel_list_path = self.get_channel_list_path(channel_id)
        if os.path.isfile(channel_list_path):
            x = ''
            while x not in ['y', 'n']:
                x = input('Replace existing file for {}? [y/n]'.format(channel_id))
            if x == 'n':
                return

        self.logger.debug('Downloading subtitles...')

        vid_ids = youtube_list(channel_id, num_pages=10)
        with open(channel_list_path, 'w') as f:
            f.write('### Channel={}{}'.format(channel_id, os.linesep))
            f.write(os.linesep.join(vid_ids))
            f.write(os.linesep)

    def download_subtitled_urls(self, batch_file):
        urls = []
        with open(batch_file, 'r') as f:
            for line in f:
                if not line.startswith('#'):
                    video_id = line.strip()
                    video_dir = os.path.join(self.output_dir, video_id)
                    self.create_dir_if_not_exists(video_dir)

                    if len(os.listdir(video_dir)) < 2:
                        urls.append('https://www.youtube.com/watch?v={}'.format(video_id))

        self.logger.debug('Downloading {} videos...'.format(len(urls)))

        ydl_opts = {
            'subtitleslangs': ['en'],
            'subtitlesformat': 'vtt',
            'writesubtitles': True,
            'nooverwrites': True,
            'convertsubtitles': 'vtt',
            'format': 'mp4',
            'outtmpl': '{}{s}%(id)s{s}%(id)s.%(ext)s'.format(self.output_dir, s=os.sep),
            'retries': 2,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)

    def download_subtitle_channel(self, channel_id):
        video_urls_file = self.get_channel_list_path(channel_id)
        if not os.path.isfile(video_urls_file):
            self.get_channel_subtitled_vids(channel_id)

        self.download_subtitled_urls(video_urls_file)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Download YouTube videos with subtitles')
    parser.add_argument('action', choices=['download', 'd', 'list', 'l'],
                        help="""What to do
                            download (d): create a list of subtitled videos to download and store them
                            list (l): create a list of subtitled videos
                        """)
    parser.add_argument('channel_id', help='Channel ID to fetch')
    args = parser.parse_args()

    d = Downloader(debug=True)
    if args.action.startswith('d'):
        d.download_subtitle_channel(args.channel_id)
    else:
        d.get_channel_subtitled_vids(args.channel_id)
