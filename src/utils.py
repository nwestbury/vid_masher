import re
import os
from webvtt import WebVTT

whitespace_regex = re.compile('\s+')
parentheses_regex = re.compile('[\{\(\[].*?[\}\)\]]')
colon_regex = re.compile('^.*:')
alphanumeric_comma_regex = re.compile("[^a-zA-Z0-9_' \.]")

def clean_caption_text(text):
    text = whitespace_regex.sub(' ', text)
    text = parentheses_regex.sub('', text)
    text = colon_regex.sub('', text)
    text = alphanumeric_comma_regex.sub('', text)

    return text.strip().lower()

def convert_timestamp(ts):
    h, m, s = ts.split(":")
    return float(h)*3600 + float(m)*60 + float(s)

def find_vtt_splits(vtt_file, out_dir):
    captions = WebVTT().read(vtt_file)

    splits = []
    for i, caption in enumerate(captions):
        s = convert_timestamp(caption.start)
        e = convert_timestamp(caption.end)
        splits.append((i, s, e, caption.text))

    return splits
