from urllib.parse import quote

from . import Provider, Definition


class DatamuseProvider(Provider):
    def __init__(self, config):
        super().__init__(config)
        self._max_results = config.get('max results', 50)
        self._result_score_threshold = config.get('result score threshold', 500)
        self._url = 'https://api.datamuse.com/words?'

    async def init(self, *args, http_session, **kwargs):
        self._session = http_session

    async def fetch(self, term: str, suggestions=True):
        params = {'sp': quote(term), 'md': 'd', 'max': self._max_results}
        async with self._session.get(self._url, params=params) as resp:
            json = await resp.json()

        if not json:
            return ()

        if self._max_results:  # we limited to 1 result in PHP bot, made configurable here
            json = json[:self._max_results]

        return tuple(
            Definition(
                result['word'],
                *(self.parse_def(definition))
            ) for result in json if all(x in result for x in ('score', 'defs', 'word')) and result['score'] > self._result_score_threshold
            for definition in result['defs']
        ) or (json[0]['word'],)  # return suggestion

    @staticmethod
    def parse_def(d) -> tuple:
        temp = d.split('\t', 2)
        return 'other' if temp[0] == 'u' else temp[0], quote(temp[1])
