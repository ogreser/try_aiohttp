import argparse
import asyncio
import uuid
import yaml
import logging
import logging.config
import jinja2
import aiohttp
import aiohttp_jinja2
from aiohttp import web
from .utils import MentionCounter, MentionsCounteUpdater


logger = logging.getLogger(__name__)
LOGGING = { 
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': { 
        'standard': { 
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': { 
        'default': { 
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': { 
        '': { 
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        },
        'aiohttp': { 
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
    } 
}


async def shutdown(app):
    for ws in app['websockets'].values():
        await ws.close()
    app['websockets'].clear()


@aiohttp_jinja2.template('index.html')
async def index(request):
    return {}


class WebSocketHandler:
    def __init__(self, updater):
        self._updater = updater

    async def handle(self, request):
        logger.info('websocket connection open')
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        content = aiohttp_jinja2.render_string(
            'content.html', request, self._updater.get_current_state())
        await ws.send_str(content)

        name = uuid.uuid1()
        request.app['websockets'][name] = ws

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception',
                    ws.exception())

        logger.info('websocket connection closed')
        del request.app['websockets'][name]
        return ws

    async def update_clients_task(self, app):
        try:
            template = app.get(aiohttp_jinja2.APP_KEY).get_template('content.html')
            async with aiohttp.ClientSession() as session:
                async for state in self._updater.updates_iter_loop(session):
                    try:
                        content = template.render(state)
                        logger.info('has new update. sending to clients')
                        for ws in app['websockets'].values():
                            if not ws.closed:
                                await ws.send_str(content)
                    except Exception as ex:
                        logger.exception(ex)
        except asyncio.CancelledError:
            pass

    async def start_update_clients_task(self, app):
        app['update_clients'] = app.loop.create_task(self.update_clients_task(app))

    async def cleanup_update_clients_task(self, app):
        app['update_clients'].cancel()
        await app['update_clients']



def init_app(conf):
    updater = MentionsCounteUpdater(start_from_doc=conf.get('start_from_doc'))
    for mention in conf['mentions']:
        updater.add_counter(MentionCounter(mention))
    ws_handler = WebSocketHandler(updater)
    app = web.Application()
    aiohttp_jinja2.setup(
        app, loader=jinja2.PackageLoader('news_counter', 'templates'))
    app['websockets'] = {}
    app.on_startup.append(ws_handler.start_update_clients_task)
    app.on_cleanup.append(ws_handler.cleanup_update_clients_task)
    app.on_shutdown.append(shutdown)
    app.router.add_get('/', index)
    app.router.add_get('/ws', ws_handler.handle)
    return app


def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        '--config', dest='config_file_path', required=True,
        help='path to yaml config')
    parser.add_argument(
        '--port', dest='port', default=8000, type=int)
    args = parser.parse_args()
    logging.config.dictConfig(LOGGING)
    with open(args.config_file_path) as f:
        conf = yaml.load(f)
    app = init_app(conf)
    web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()