import asyncio
import os

from aiohttp import web
import aiohttp_jinja2
from aiopg.sa import create_engine
import aioredis
import jinja2

from app import config, handlers, processing


async def create_db(app):
    app['db_engine'] = await create_engine(
        user=os.environ['PG_USER'],
        database=os.environ['PG_DB_NAME'],
        host=os.environ['PG_HOST'],
        port=os.environ['PG_PORT'],
        password=os.environ['PG_PASS'],
    )


async def dispose_db(app):
    app['db_engine'].close()
    await app['db_engine'].wait_closed()


async def create_redis(app):
    app['redis'] = await aioredis.create_redis_pool(os.environ['REDIS_DSN'])


async def dispose_redis(app):
    app['redis'].close()
    await app['redis'].wait_closed()


async def dispose_bg_worker(app):
    app['bg_worker_task'].cancel()
    try:
        await app['bg_worker_task']
    except asyncio.CancelledError:
        pass


async def create_bg_worker(app):
    app['notification_ws'] = []
    app['bg_worker_task'] = asyncio.create_task(processing.bg_worker(app))


async def startup(app):
    await create_db(app)
    await create_redis(app)
    await create_bg_worker(app)


async def cleanup(app):
    await dispose_db(app)
    await dispose_redis(app)
    await dispose_bg_worker(app)


async def get_app(args=None) -> web.Application:
    application = web.Application()
    aiohttp_jinja2.GLOBAL_HELPERS['generate_url'] = processing.generate_url

    aiohttp_jinja2.GLOBAL_HELPERS['PAGE_SIZES'] = config.PAGE_SIZES
    aiohttp_jinja2.GLOBAL_HELPERS['HOST'] = config.HOST
    aiohttp_jinja2.GLOBAL_HELPERS['PORT'] = config.PORT

    aiohttp_jinja2.setup(
        application,
        loader=jinja2.FileSystemLoader(
            os.path.join(os.path.dirname(__file__), 'templates')
        ),
    )

    application.on_startup.append(startup)
    application.on_cleanup.append(cleanup)

    application.add_routes(
        [
            web.get('/items/{intitle}', handlers.search),
            web.get('/', handlers.index),
            web.get('/notification', handlers.ws_handler),
        ]
    )
    return application


def run():
    loop = asyncio.get_event_loop()
    try:
        web.run_app(
            loop.run_until_complete(get_app()),
            host=config.HOST,
            port=config.PORT,
        )
    finally:
        loop.close()


if __name__ == '__main__':
    run()
