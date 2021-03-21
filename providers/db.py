import json
import sqlite3

import aiomysql

from . import Definition, Provider


class MySqlDBProvider(Provider):
    """MySQL provider, for fetching and storing results primarily as a caching layer"""

    def __init__(self, config):
        super().__init__(config)
        self._pool: aiomysql.Pool = None  # noqa (will be populated in init)
        self._config = config

    async def init(self, *args, **kwargs):
        self._pool = await aiomysql.create_pool(**json.loads(self._config['connopts']))

    async def fetch(self, term: str, suggestions=False):
        if len(term) >= 3:  # switch to prefix-based when amount of results is likely to be low
            condition = 'LIKE %s'
            term += '%'
        else:
            condition = '=%s'

        results = []

        async with self._pool.acquire() as conn, conn.cursor() as cursor:
            await cursor.execute(
                f'SELECT `word`, `type`, `definition` FROM `dictionary` WHERE `word` {condition} LIMIT 50',
                (term,)
            )
            row = await cursor.fetchone()
            while row:
                results.append(Definition(*row))
                row = await cursor.fetchone()

        return results

    async def store(self, d: Definition):
        query = 'INSERT IGNORE INTO `dictionary` VALUES(%s, %s, %s, DEFAULT, DEFAULT)' \
                'ON DUPLICATE KEY UPDATE `type`=VALUES(`type`), `definition`=VALUES(`definition`)'

        if len(d.definition) > 3000:  # just a precaution
            d.definition = d.definition[:3000] + '...'

        async with self._pool.acquire() as conn, conn.cursor() as cursor:
            await cursor.execute(query, d)


class SqliteDBProvider(Provider):
    """SQLite provider for fetching and storing results primarily as a caching layer"""

    def __init__(self, config):
        super().__init__(config)
        opts = json.loads(config['connopts'])
        opts.setdefault('isolation_level', None)  # autocommit

        self._conn = sqlite3.connect(**opts)
        self._conn.execute(
            'CREATE TABLE IF NOT EXISTS dictionary('
            '   `word` TEXT NOT NULL,'
            '   `type` TEXT NOT NULL,'
            '   `definition` TEXT,'
            '   `inserted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,'
            '   PRIMARY KEY(`word`, `type`)'
            ')'
        )

    async def fetch(self, term, suggestions=False):
        if len(term) >= 3:  # switch to prefix-based when amount of results is likely to be low
            condition = 'LIKE ?'
            term += '%'
        else:
            condition = '=?'

        cursor = self._conn.cursor()
        cursor.execute(
            f'SELECT `word`, `type`, `definition` FROM `dictionary` WHERE `word` {condition} LIMIT 50',
            (term,)
        )
        results = []
        row = cursor.fetchone()
        while row:
            results.append(Definition(*row))
            row = cursor.fetchone()
        return results

    async def store(self, d: Definition):
        query = 'INSERT INTO `dictionary`(`word`, `type`, `definition`) VALUES (?, ?, ?) ' \
                'ON CONFLICT(`word`, `type`) DO UPDATE SET `definition`=excluded.`definition`'

        if len(d.definition) > 3000:  # just a precaution
            d.definition = d.definition[:3000] + '...'

        self._conn.cursor().execute(query, d)

    def __del__(self):
        self._conn.close()
