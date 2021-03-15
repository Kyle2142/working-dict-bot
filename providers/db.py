import json

import aiomysql

from . import Definition, Provider


class DBProvider(Provider):
    """MySQL provider, for fetching and storing results primarily as a caching layer"""

    def __init__(self, config):
        super().__init__(config)
        self._pool: aiomysql.Pool = None
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
