from urllib.parse import quote

from . import Provider, Definition


class WordnikProvider(Provider):
    def __init__(self, config):
        super().__init__(config)
        self._part_of_speech_map = {
            'adjective': 'adj',
            'abbreviation': 'abbr',
            **{x: 'n' for x in ('noun', 'pronoun', 'noun-possesive', 'noun-plural', 'proper-noun',
                                'proper-noun-plural', 'proper-noun-possessive')},
            **{x: 'v' for x in ('verb', 'past-participle', 'auxiliary-verb', 'verb-transitive',
                                'verb-intransitive', 'imperative')}
        }
        self._params = {
            'key': config['key'],
            'useCanonical': True,
            'partOfSpeech': ','.join(self._part_of_speech_map.keys())
        }
        self._max_results = config.get('max results', 0)

    async def init(self, *args, http_session, **kwargs):
        self._session = http_session

    async def fetch(self, term: str, suggestions=True):
        async with self._session.get(
                f'https://api.wordnik.com/v4/word.json/{quote(term)}/definitions',
                params=self._params
        ) as resp:
            json = await resp.json()

        if not json:
            return ()

        if self._max_results:  # we limited to 1 result in PHP bot, made configurable here
            json = json[:self._max_results]

        return tuple(
            Definition(
                result['word'],
                self._part_of_speech_map.get(result['partOfSpeech'], 'other'),
                result['text']
            ) for result in json if all(x in result for x in ('word', 'text', 'partOfSpeech'))
        )
