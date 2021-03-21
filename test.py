import asyncio
import unittest

from aiohttp import ClientSession

from main import providers, fetch_from_dictionaries


class MyTestCase(unittest.TestCase):
    http: ClientSession = None

    @classmethod
    def setUpClass(cls) -> None:
        asyncio.get_event_loop().run_until_complete(cls.setUpClassAsync())

    @classmethod
    async def setUpClassAsync(cls):
        cls.http = ClientSession(headers={'Accept': 'application/json'})  # currently all APIs accept json
        for p in providers:
            await p.init(http_session=cls.http)

    @classmethod
    def tearDownClass(cls) -> None:
        asyncio.get_event_loop().run_until_complete(cls.tearDownClassAsync())

    @classmethod
    async def tearDownClassAsync(cls):
        await cls.http.close()

    def test(self):
        asyncio.get_event_loop().run_until_complete(self._test_async())

    async def _test_async(self):
        results, suggestion = await fetch_from_dictionaries('beep')
        self.assertTrue(results)  # len(r)>0
        for r in results:
            print(r)  # TODO: hard coded result comparison?


if __name__ == '__main__':
    unittest.main()
