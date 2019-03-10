import logging
import psycopg2
import os

from utils import find_vtt_splits, clean_caption_text

class Database:
    def __init__(self, debug=False):
        self.logger = logging.getLogger('db')
        self.logger.setLevel(logging.DEBUG)
        self.conn = psycopg2.connect(host='',
                                     dbname='masher',
                                     user=os.environ['PSQL_USER'],
                                     password=os.environ['PSQL_PASS'])

        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.root_dir = os.path.realpath(os.path.join(script_dir, '..'))
        self.video_dir = os.path.join(self.root_dir, 'videos')

        if debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(stream_handler)

    def setup(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE caption (
                id                 SERIAL PRIMARY KEY,
                vid_id             VARCHAR (11) NOT NULL,
                index              INTEGER NOT NULL,
                raw_text           VARCHAR(250) NOT NULL,
                text               VARCHAR(250) NOT NULL,
                clip_path          VARCHAR(200) NOT NULL,
                video_path         VARCHAR(200) NOT NULL,
                converted          BOOLEAN NOT NULL,
                start_t            FLOAT(24) NOT NULL,
                end_t              FLOAT(24) NOT NULL,
                duration           FLOAT(24) NOT NULL,
                priority           INTEGER NOT NULL,
                CONSTRAINT uniq_id_vid_id UNIQUE (vid_id, index)
            );

            CREATE TABLE word (
                id                 SERIAL PRIMARY KEY,
                caption_id         SERIAL REFERENCES caption(id),
                word               VARCHAR(50) NOT NULL,
                index              INTEGER NOT NULL,
                length             INTEGER NOT NULL
            );
        """)

        self.conn.commit()

    def drop(self):
        cur = self.conn.cursor()
        cur.execute("DROP TABLE caption CASCADE")
        cur.execute("DROP TABLE word")
        self.conn.commit()

    def insert_caption(self, cur, clip_i, vid_id, start_t, end_t, raw_text, video_path, clip_path):
        text = clean_caption_text(raw_text)

        try:
            cur.execute("""
                INSERT INTO caption
                    (index, vid_id, raw_text, text, clip_path, video_path, converted, start_t, end_t, duration, priority)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (clip_i, vid_id, raw_text, text, clip_path, video_path, False, start_t, end_t, end_t - start_t, 100))
        except psycopg2.IntegrityError:
            self.conn.rollback()
            return

        db_caption_id = cur.fetchone()[0]
        self.conn.commit()

        if text:
            args = []
            query = "INSERT INTO word (caption_id, word, index, length) VALUES "
            words = text.split(' ')
            for i, word in enumerate(words):
                morg = cur.mogrify("(%s,%s,%s,%s)", (db_caption_id, word.replace('.', ''), i, len(words))).decode("utf-8")
                args.append(morg)
            query += ','.join(args)

            cur.execute(query)
            self.conn.commit()

    def populate(self):
        cur = self.conn.cursor()

        video_ids = os.listdir(self.video_dir)
        for video_index, video_id in enumerate(video_ids):
            if video_index % 100 == 0:
                self.logger.debug('Progress Report: %s/%s', video_index+1, len(video_ids))

            base_dir = os.path.join(self.video_dir, video_id)
            files = os.listdir(base_dir)

            vtt_file = next((os.path.join('videos', video_id, f) for f in files if f.endswith('vtt')), None)
            video_file = next((os.path.join('videos', video_id, f) for f in files if f == video_id + '.mp4'), None)

            # if there is not exaclty a VTT and video file, ignore
            if len(files) < 2 or vtt_file is None or video_file is None:
                self.logger.debug('Skipping video folder (%s)', base_dir)
                continue

            splits = find_vtt_splits(os.path.join(self.root_dir, vtt_file), base_dir)
            for split in splits:
                i, s, e, raw_text = split
                clip_path = os.path.join('videos', video_id, "clip{}.mp4".format(i))
                self.insert_caption(cur, i, video_id, s, e, raw_text, video_file, clip_path)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database for masher')
    parser.add_argument('action', choices=['setup', 's', 'populate', 'p', 'drop', 'd'],
                        help="""What to do
                            setup (s): create tables to setup database
                            drop (d): drop tables
                            populate (p): fill database with caption data
                        """)
    args = parser.parse_args()

    d = Database(debug=True)
    if args.action.startswith('s'):
        d.setup()
    elif args.action.startswith('d'):
        d.drop()
    else:
        d.populate()
