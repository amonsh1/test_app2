from datetime import datetime, timezone
import hashlib
import json

from aiohttp import web
import aiohttp_jinja2
import sqlalchemy as sa

from app import config, models, processing
from app.db import tables


__all__ = ['index', 'search', 'ws_handler']


async def index(request: web.Request) -> web.Response:
    intitle = request.query.get('intitle')
    if intitle:
        return web.HTTPFound(f'/items/{intitle}')

    async with request.app['db_engine'].acquire() as conn:
        search_types = await (
            await conn.execute(
                tables.search_types_table.select().distinct('intitle')
            )
        ).fetchall()
    response = aiohttp_jinja2.render_template(
        'index.html', request, {'search_types': search_types}
    )
    return response


async def search(request: web.Request) -> web.Response:
    query = models.SearchQuery(
        page=request.query.get('page', 1),
        pagesize=request.query.get('pagesize', config.PAGE_SIZES[0]),
        intitle=request.match_info['intitle'],
        sort=request.query.get('sort', 'activity'),
        order=request.query.get('order', 'desc'),
    )

    order_fields = {
        models.Sort.ACTIVITY: tables.questions_table.c.last_activity_date,
        models.Sort.VOTES: tables.questions_table.c.score,
        models.Sort.CREATION: tables.questions_table.c.creation_date,
    }
    order_field = order_fields[query.sort]
    order_field_to_response = (
        sa.desc(order_field)
        if query.order == models.Order.DESC
        else order_field
    )

    async with request.app['db_engine'].acquire() as conn:
        async with conn.begin():
            await processing.insert(
                conn,
                query.intitle,
                query.sort,
                query.order,
                query.page,
                query.pagesize,
            )
    redis_key = hashlib.sha256(
        f'{query.page}{query.pagesize}{query.intitle}'
        f'{query.sort.value}{query.order}'.encode()
    ).hexdigest()

    response_data = await request.app['redis'].get(redis_key)

    if not response_data:
        async with request.app['db_engine'].acquire() as conn:
            search_type = await processing.get_or_create_search_type(
                conn, query.intitle, query.sort, query.order
            )
            response_data = await (
                await conn.execute(
                    tables.questions_table.select(tables.questions_table)
                    .where(
                        tables.questions_table.c.search_type_id
                        == search_type['id']
                    )
                    .order_by(order_field_to_response)
                    .offset(query.pagesize * query.page - query.pagesize)
                    .limit(query.pagesize)
                )
            ).fetchall()
        response_data = list(map(dict, response_data))
        response_data = [
            {
                key: val.replace(tzinfo=timezone.utc).strftime(
                    '%d-%m-%Y %H:%M:%S %Z'
                )
                if isinstance(val, datetime)
                else val
                for key, val in item.items()
            }
            for item in response_data
        ]

        await request.app['redis'].set(
            redis_key,
            json.dumps(response_data).encode(),
            expire=config.CACHE_TIMEOUT,
        )
    else:
        response_data = json.loads(response_data.decode())

    context = {
        'items': response_data,
        'query': {
            'page': query.page,
            'pagesize': query.pagesize,
            'intitle': query.intitle,
            'sort': query.sort.value,
            'order': query.order.value,
        },
    }
    response = aiohttp_jinja2.render_template('items.html', request, context)

    return response


async def ws_handler(request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app['notification_ws'].append(ws)
    try:
        async for x in ws:
            pass
    finally:
        request.app['notification_ws'].remove(ws)
    return ws
