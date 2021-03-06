import asyncio
import configparser
import logging.handlers
import os
import sys
from typing import Sequence

import telethon
from aiohttp import ClientSession

from providers import db, Provider, merriam, datamuse, wordnik, Definition


async def fetch_from_dictionaries(term):
    db_provider, provider_list = providers[0], providers[1:]

    suggestion = None
    results = await db_provider.fetch(term)
    if not results:
        results = temp_results = []
        for provider in provider_list:
            temp_results = await provider.fetch(term)
            if temp_results:
                break
        for d in temp_results:
            if isinstance(d, str) and not suggestion:  # save topmost suggestion
                suggestion = d
            else:
                results.append(d)
                await db_provider.store(d)

    return results, suggestion


@telethon.events.register(telethon.events.InlineQuery())
async def inline_handler(event: telethon.events.InlineQuery.Event):
    if not event.text:
        return

    logger.info("Inline query %d: text='%s'", event.id, event.text)

    results, suggestion = await fetch_from_dictionaries(event.text)

    logger.debug("Inline query %d: Processed %d results", event.id, len(results))

    if not results:
        definition = 'Not found.'
        if suggestion:
            definition += f' Did you mean "{suggestion}"?'
        results = (Definition(event.text, 'Unknown type', definition),)

    try:
        results = [await event.builder.article(d.term, d.definition, text=str(d), parse_mode='HTML') for d in results]
        await event.answer(results, CACHE_TIME)
    except telethon.errors.QueryIdInvalidError:
        pass
    except telethon.errors.RPCError:
        logger.warning("Inline query %d: Sending results failed", event.id, exc_info=True)
    else:
        logger.debug("Inline query %d: Complete", event.id)


@telethon.events.register(telethon.events.NewMessage(pattern=r"(?i)/logs?"))
async def send_logs(event: telethon.events.NewMessage.Event):
    if event.chat_id != config['main'].getint('owner telegram id'):  # cannot use from_users due to config undefined
        return
    if os.path.exists(LOG_FILE):
        await event.reply(file=LOG_FILE)
    else:
        await event.reply("No log file found")


@telethon.events.register(telethon.events.NewMessage(pattern=r"(?i)/(start|help)$"))
async def start_help(event: telethon.events.NewMessage.Event):
    await event.reply(
        "Hello! I am meant to be used in inline mode."
        "\nIf you are not sure what that means, try typing <code>@workingdictbot</code> and a space. ",
        parse_mode='HTML'
    )


async def main():
    http = ClientSession(headers={'Accept': 'application/json'})  # currently all APIs accept json
    for p in providers:
        await p.init(http_session=http)

    await bot.connect()
    if not await bot.is_user_authorized() or not await bot.is_bot():
        await bot.start(bot_token=config['TG API']['bot_token'])  # noqa (telethon's hack)
    logger.info('Started bot')

    try:
        await bot.run_until_disconnected()
    except KeyboardInterrupt:
        pass
    finally:
        await http.close()


def get_config():
    if not os.path.exists('config.ini'):
        raise FileNotFoundError('config.ini not found. Please copy example-config.ini and edit the relevant values')
    c = configparser.ConfigParser()
    c.read_file(open('config.ini'))
    return c


def init_logging(level, file):
    l = logging.getLogger()
    level = getattr(logging, level, logging.INFO)
    l.setLevel(level)
    if not os.path.exists('logs'):
        os.mkdir('logs', 0o770)
    h = logging.handlers.RotatingFileHandler(file, encoding='utf-8', maxBytes=5 * 1024 * 1024, backupCount=5)
    h.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s:%(message)s"))
    h.setLevel(level)
    l.addHandler(h)
    if os.getenv('DOCKER', False):  # we are in docker, use stdout as well
        l.addHandler(logging.StreamHandler(sys.stdout))
    return l


config = get_config()

CACHE_TIME = config['TG API'].getint('cache_time')
LOG_FILE = config['main'].get('log file', 'logs/bot.log')

logger = init_logging(config['main']['logging level'], LOG_FILE)

providers: Sequence[Provider] = (
    db.MySqlDBProvider(config['mysql']) if config['main']['dbengine'] == 'mysql' else db.SqliteDBProvider(config['sqlite']),
    merriam.MerriamProvider(config['merriam']),
    wordnik.WordnikProvider(config['wordnik']),
    datamuse.DatamuseProvider(config['datamuse'])
)

if __name__ == '__main__':
    bot = telethon.TelegramClient(config['TG API']['session'],
                                  config['TG API'].getint('api_id'), config['TG API']['api_hash'],
                                  auto_reconnect=True, connection_retries=1000)
    bot.flood_sleep_threshold = 5

    for f in (inline_handler, send_logs, start_help):
        bot.add_event_handler(f)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(asyncio.sleep(0.250))  # aiohttp ssl shutdown
        loop.close()
