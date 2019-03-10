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
        cur.close()

    def drop(self):
        cur = self.conn.cursor()
        cur.execute("DROP TABLE caption CASCADE")
        cur.execute("DROP TABLE word")
        self.conn.commit()
        cur.close()

    def insert_syn(self, text, video_path, duration):
        cur = self.conn.cursor()

        cur.execute("SELECT COALESCE(MAX(index), 0) FROM caption WHERE vid_id='syn'")
        syn_id = cur.fetchone()[0] + 1

        self.insert_caption(cur, syn_id, 'syn', 0, duration, text, video_path, video_path, converted=True, priority=10)

    def insert_caption(self, cur, clip_i, vid_id, start_t, end_t, raw_text, video_path, clip_path, converted=False, priority=100):
        text = clean_caption_text(raw_text)

        try:
            cur.execute("""
                INSERT INTO caption
                    (index, vid_id, raw_text, text, clip_path, video_path, converted, start_t, end_t, duration, priority)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (clip_i, vid_id, raw_text, text, clip_path, video_path, converted, start_t, end_t, end_t - start_t, priority))
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

        cur.close()

    def find_existing_words(self, words):
        cur = self.conn.cursor()
        cur.execute('SELECT word FROM word WHERE word IN %s GROUP BY word', (tuple(words), ))
        data = set(w for w, in cur.fetchall())
        cur.close()

        return data

    def find_text_range(self, word, caption_index_filters=None, limit=None):
        cur = self.conn.cursor()

        args = [word]
        query = 'SELECT * FROM word WHERE word = %s'
        if caption_index_filters is not None:
            query += ' AND ('
            cond = []
            for cap_id, index in caption_index_filters:
                cond.append('(caption_id = %s AND index = %s)')
                args.append(cap_id)
                args.append(index)
            query += ' OR '.join(cond) + ')'

        if limit is not None:
            query += ' LIMIT %s'
            args.append(limit)

        cur.execute(query, args)
        data = cur.fetchall()

        cur.close()

        return data

    def find_caption_info(self, caption_id):
        cur = self.conn.cursor()
        cur.execute('SELECT video_path, start_t, end_t, clip_path FROM caption WHERE id = %s', (caption_id,))
        path = cur.fetchone()
        cur.close()
        return path

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
