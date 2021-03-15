from typing import NamedTuple, Sequence, Union


class Definition(NamedTuple):
    term: str
    type: str
    definition: str

    def __str__(self):
        return f"<b>{self.term}</b> (<i>{self.type}</i>):\n{self.definition}"


class Provider:
    def __init__(self, config):
        pass

    async def init(self, *args, **kwargs) -> None:
        pass

    async def fetch(self, term: str, suggestions=True) -> Sequence[Union[Definition, str]]:
        """Return one or more Definitions/Suggestions from the provider"""
        raise NotImplementedError()
