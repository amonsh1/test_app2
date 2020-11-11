import asyncio
import datetime
from typing import Optional
from urllib.parse import urlencode

from aiohttp import client, web, web_exceptions
import sqlalchemy as sa

from app import config, models
from app.db import tables


__all__ = [
    'fetch_data',
    'get_or_create_search_type',
    'get_border_value',
    'generate_url',
]


async def fetch_data(
    pagesize: int,
    sort: models.Sort,
    intitle: str,
    order: models.Order,
    max: Optional[int] = None,
    min: Optional[int] = None,
):
    assert not (max is not None and min is not None)
    async with client.ClientSession() as session:
        url = 'https://api.stackexchange.com/2.2/search?'
        params = {
            'page': 1,
            'pagesize': pagesize,
            'sort': sort.value,
            'order': order.value,
            'intitle': intitle,
            'site': 'stackoverflow',
        }
        if max is not None:
            params['max'] = max
        if min is not None:
            params['min'] = min
        params['filter'] = '!0UscSptPTVlsBx4DMPqYtcLW*'
        async with session.get(url + urlencode(params)) as response:
            items = list(map(dict, (await response.json())['items']))
            for item in items:
                for date_field in (
                    'last_activity_date',
                    'creation_date',
                    'last_edit_date',
                    'closed_date',
                    'community_owned_date',
                    'protected_date',
                    'bounty_amount',
                    'locked_date',
                ):
                    value = item.get(date_field)
                    if value is None:
                        continue
                    item[date_field] = datetime.datetime.fromtimestamp(
                        item[date_field], tz=datetime.timezone.utc
                    )

            return items


async def get_or_create_search_type(
    conn, intitle, sort: models.Sort, order: models.Order
) -> dict:
    search_type = await (
        await conn.execute(
            tables.search_types_table.select().where(
                (tables.search_types_table.c.intitle == intitle)
                & (tables.search_types_table.c.sort == sort.value)
                & (tables.search_types_table.c.order == order.value)
            )
        )
    ).fetchone()
    if not search_type:
        search_type = await (
            await conn.execute(
                tables.search_types_table.insert()
                .values(
                    intitle=intitle,
                    sort=sort.value,
                    order=order.value,
                )
                .returning(tables.search_types_table)
            )
        ).fetchone()
    return search_type


async def get_border_value(
    border_value: dict, sort: models.Sort, order: models.Order
):
    """Возарвщает пограничное значение для api запроса"""

    if sort == models.Sort.ACTIVITY:
        v = int(
            border_value['last_activity_date']
            .replace(tzinfo=datetime.timezone.utc)
            .timestamp()
        )

    elif sort == models.Sort.VOTES:
        v = border_value['score']
    elif sort == models.Sort.CREATION:
        v = int(
            border_value['creation_date']
            .replace(tzinfo=datetime.timezone.utc)
            .timestamp()
        )
    else:
        raise ValueError
    # исключаем из запроса пограничное значение, которое уже естьв  базе
    v = v + 1 if order == 'asc' else v - 1
    return v


def generate_url(
    page: str, pagesize: str, intitle: str, sort: str, order: str
) -> str:
    return f'http://{config.HOST}:{config.PORT}/items/{intitle}?' + urlencode(
        {
            'page': page,
            'pagesize': pagesize,
            'sort': sort,
            'order': order,
        }
    )


async def insert(
    conn,
    intitle: str,
    sort: models.Sort,
    order: models.Order,
    page: int,
    pagesize: int,
):
    order_fields = {
        models.Sort.ACTIVITY: tables.questions_table.c.last_activity_date,
        models.Sort.VOTES: tables.questions_table.c.score,
        models.Sort.CREATION: tables.questions_table.c.creation_date,
    }
    order_field = order_fields[sort]

    search_type = await get_or_create_search_type(conn, intitle, sort, order)
    order_field_to_border = (
        sa.desc(order_field) if order == models.Order.ASC else order_field
    )
    questions_count = await (
        await conn.execute(
            sa.select([sa.func.count()])
            .select_from(tables.questions_table)
            .where(tables.questions_table.c.search_type_id == search_type['id'])
        )
    ).fetchone()

    not_existed_count = page * pagesize - questions_count[0]
    if not_existed_count > pagesize:
        raise web_exceptions.HTTPBadRequest(text='Не прыгай через страницу')
    if not_existed_count > 0:
        border_value = await (
            await conn.execute(
                tables.questions_table.select()
                .where(
                    tables.questions_table.c.search_type_id == search_type['id']
                )
                .order_by(order_field_to_border)
                .limit(1)
            )
        ).fetchone()

        if questions_count[0] != 0:
            border_value = await get_border_value(border_value, sort, order)
        else:
            # если в база пустая, то качаем с начала
            border_value = None

        if order == 'asc':
            border_params = {'min': border_value}
        else:
            border_params = {'max': border_value}

        questions = await fetch_data(
            not_existed_count,
            sort,
            intitle,
            order,
            **border_params,
        )
        async with conn.begin():
            for question in questions:
                owner = question.pop('owner')

                owner = await (
                    await conn.execute(
                        tables.owners_table.insert()
                        .values(**owner)
                        .returning(tables.owners_table)
                    )
                ).fetchone()

                question['search_type_id'] = search_type['id']
                question['owner_id'] = owner['id']
                await conn.execute(
                    tables.questions_table.insert().values(**question)
                )


async def bg_worker(app: web.Application):
    while True:
        await asyncio.sleep(config.BG_WORKER_TIMEOUT)
        async with app['db_engine'].acquire() as conn:
            search_types = await (
                await conn.execute(tables.search_types_table.select())
            ).fetchall()

            async with await conn.begin():
                # await conn.execute(tables.owners_table.delete())
                for s_type in search_types:

                    questions_count = await (
                        await conn.execute(
                            sa.select([sa.func.count()])
                            .select_from(tables.questions_table)
                            .where(
                                tables.questions_table.c.search_type_id
                                == s_type['id']
                            )
                        )
                    ).fetchone()
                    questions_count = questions_count[0]
                    await conn.execute(
                        tables.questions_table.delete().where(
                            tables.questions_table.c.search_type_id
                            == s_type['id']
                        )
                    )
                    page_sizes = [100 for _ in range(questions_count // 100)]
                    if questions_count % 100:
                        page_sizes.append(int(questions_count % 100))
                    for i, page_size in enumerate(page_sizes, 1):
                        if page_size != 100:
                            # если запраиваем не по 100, то меняем номер
                            # страницы относительно размера
                            i = int(100 / page_size * (i - 1)) + 1
                        await insert(
                            conn,
                            s_type['intitle'],
                            models.Sort(s_type['sort']),
                            models.Order(s_type['order']),
                            i,
                            page_size,
                        )
            # raise Exception
            for ws_client in app['notification_ws']:
                for search_type in search_types:
                    await ws_client.send_str(
                        f'{search_type["intitle"]} обновился'
                    )
