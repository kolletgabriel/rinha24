from typing import TypedDict, AsyncIterator
from contextlib import asynccontextmanager

from .endpoints import transaction, statement

from asyncpg import create_pool, Pool

from starlette.applications import Starlette
from starlette.config import Config
from starlette.routing import Route


class State(TypedDict):
    pool: Pool


@asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[State]:
    cfg = Config()
    DB_URL = cfg('DB_URL')
    pool = await create_pool(DB_URL)

    yield { 'pool': pool }

    await pool.close()


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
                    methods=['POST']
                )
            ],
            lifespan=lifespan
    )
