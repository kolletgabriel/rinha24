from typing import TypedDict, AsyncIterator
from contextlib import asynccontextmanager
import json

from .endpoints import transaction, statement

from asyncpg import create_pool, Connection, Pool

from starlette.applications import Starlette
from starlette.config import Config
from starlette.routing import Route


class State(TypedDict):
    pool: Pool


@asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[State]:
    cfg = Config()
    DB_URL = cfg('DB_URL')

    async def init_conn(conn: Connection):
        await conn.set_type_codec(  # autoconvert `JSON` -> `dict`
            'json',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )

    async with create_pool(DB_URL, init=init_conn) as pool:
        yield { 'pool': pool }


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route(
                '/customers/{id:int}/transaction',
                endpoint=transaction,
                methods=['POST']
            ),
            Route(
                '/customers/{id:int}/statement',
                endpoint=statement,
                methods=['GET']
            )
        ],
        lifespan=lifespan
    )
