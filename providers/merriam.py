from urllib.parse import quote

from . import Provider, Definition


class MerriamProvider(Provider):
    def __init__(self, config):
        super().__init__(config)
        self._params = {'key': config['key']}
        self._part_of_speech_map = {
            'adjective': 'adj',
            'abbreviation': 'abbr',
            **{x: 'n' for x in ('noun', 'pronoun', 'noun-possesive', 'noun-plural', 'proper-noun',
                                'proper-noun-plural', 'proper-noun-possessive')},
            **{x: 'v' for x in ('verb', 'past-participle', 'auxiliary-verb', 'verb-intransitive',
                                'verb-transitive', 'imperative')}
        }

    async def init(self, *args, http_session, **kwargs):
        self._session = http_session

    async def fetch(self, term, suggestions=True):
        async with self._session.get(
                f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{quote(term)}',
                params=self._params
        ) as resp:
            json = await resp.json()
        if not json:
            return ()

        if isinstance(json[0], str) and suggestions:
            return json

        return tuple(
            Definition(
                result['meta']['id'].split(':', 2)[0],
                self._part_of_speech_map.get(result['fl'], 'other'),
                '.\n- '.join(x[0].upper() + x[1:] for x in result['shortdef'] if x)
            ) for result in json if all(x in result for x in ('shortdef', 'meta', 'fl'))
        )
