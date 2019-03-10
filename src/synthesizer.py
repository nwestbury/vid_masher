import logging
import os

import gizeh
from gtts import gTTS
import moviepy.editor as mpy

from utils import clean_caption_text

class Synthesizer:
    def __init__(self, debug=False):
        self.logger = logging.getLogger('sytheizer')
        self.logger.setLevel(logging.DEBUG)

        if debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(stream_handler)

    def sythesize_word(self, word, output_path):
        clean = clean_caption_text(word).replace('.', '')

        self.logger.debug('Synthesizing "%s"...', clean)
        tts = gTTS(text=clean, lang='en')
        tts.save('tmp.mp3')

        os.system('ffmpeg -i tmp.mp3 -c:a aac tmp.m4a')
        audio_clip = mpy.AudioFileClip('tmp.m4a')

        fontsize = 90 if len(word) <= 13 else 50

        surface = gizeh.Surface(720, 480) # width, height
        text = gizeh.text(clean.capitalize(), fontfamily="Impact", fontsize=fontsize,
                          fill=(1, 1, 1), xy=(360, 240))
        text.draw(surface)
        np_image = surface.get_npimage()

        video_clip = mpy.VideoClip(lambda t: np_image, duration=audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        video_clip.write_videofile(output_path, fps=24, audio_codec='aac')
        os.remove('tmp.mp3')
        os.remove('tmp.m4a')

        return audio_clip.duration

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Synthesize a video clip of text')
    parser.add_argument('text', help='text')
    parser.add_argument('output', help='MP4 file path (default: "out.mp4")',
                        nargs='?', default='out.mp4')
    args = parser.parse_args()

    s = Synthesizer(debug=True)
    s.sythesize_word(args.text, args.output)
