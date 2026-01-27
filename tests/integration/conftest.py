from rinha24.app import create_app

from pathlib import Path

from pytest import fixture
from asyncpg import create_pool
from starlette.config import environ
from starlette.testclient import TestClient
from testcontainers.postgres import PostgresContainer


@fixture(scope='package')
def db_url():
    pg = PostgresContainer('postgres:18.1-trixie', driver=None)
    pg.start()
    url = pg.get_connection_url()
    environ['DB_URL'] = url  # override Dockerfile's `ENV`

    yield url

    pg.stop()


@fixture
def init_sql():
    filepath = Path(__file__).resolve().parent.parent.parent / 'init.sql'
    with open(filepath, 'r') as file:
        sql = file.read()
    return sql


@fixture
async def db_pool(anyio_backend, db_url, init_sql):
    pool = await create_pool(db_url)

    async with pool.acquire() as conn:
        await conn.execute(init_sql)

    yield pool

    async with pool.acquire() as conn:
        await conn.execute('''DROP TABLE customers, transactions CASCADE;
                              DROP PROCEDURE do_transaction;
                              DROP PROCEDURE get_statement;''')


@fixture(scope='package')
def client(db_url):
    with TestClient(app=create_app()) as tc:
        yield tc
