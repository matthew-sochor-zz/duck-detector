import json
import os
import sqlite3

from threading import get_ident


class Pics:

    _create = ("CREATE TABLE IF NOT EXISTS pic "
               "("
               " pic_id INTEGER PRIMARY KEY AUTOINCREMENT,"
               " item TEXT"
               ")")

    _append = 'INSERT INTO pic (item) VALUES (?)'

    _replace = 'UPDATE pic SET item = ? WHERE pic_id = ?'

    _get = ('SELECT item from pic '
            'WHERE pic_id = ?')

    _last_rowid = 'SELECT last_insert_rowid() from pic'

    _random = 'SELECT * from pic ORDER BY Random() LIMIT 1'

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self._connection_cache = {}

        with self._get_conn() as conn:
            conn.execute(self._create)

    def _get_conn(self):
        id = get_ident()
        if id not in self._connection_cache:
            self._connection_cache[id] = sqlite3.Connection(self.path, timeout=60)
        return self._connection_cache[id]

    def append(self, value):
        value_json = json.dumps(value)
        with self._get_conn() as conn:
            conn.execute(self._append, (value_json,))
            pic_id = conn.execute(self._last_rowid).fetchone()[0]
        return pic_id

    def replace(self, key, value):
        value_json = json.dumps(value)
        with self._get_conn() as conn:
            conn.execute(self._replace, (value_json, key))

    def random(self):
        with self._get_conn() as conn:
            key, value_json = conn.execute(self._random).fetchone()

        value = json.loads(value_json)
        return key, value

    def get(self, key):
        with self._get_conn() as conn:
            value_json = conn.execute(self._get, (key,)).fetchone()[0]

        value = json.loads(value_json)
        return value
