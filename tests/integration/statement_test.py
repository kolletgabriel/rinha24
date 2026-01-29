import asyncio

from ..utils import Queries

from datetime import datetime
from pytest import mark


pytestmark = mark.anyio


async def test_404(db_pool, client):
    res = await client.get('/customers/6/statement')
    assert res.status_code == 404


async def test_is_empty(db_pool, client):
    res = await client.get('/customers/1/statement')
    assert res.status_code == 200

    res_body = res.json()

    balance = res_body['balance']
    assert balance['total'] == 0
    assert balance['overdraft_limit'] == \
            await db_pool.fetchval(Queries.OVERDRAFT)

    recent_transactions = res_body['recent_transactions']
    assert recent_transactions is None


async def test_shows_10_at_most(db_pool, client):
    await asyncio.gather(
        *[db_pool.execute(Queries.PROC) for _ in range(9)]
    )

    res = await client.get('/customers/1/statement')
    assert res.status_code == 200
    assert len(res.json()['recent_transactions']) == 9

    await asyncio.gather(
        *[db_pool.execute(Queries.PROC) for _ in range(2)]
    )

    res = await client.get('/customers/1/statement')
    assert res.status_code == 200
    assert len(res.json()['recent_transactions']) == 10


async def test_is_sorted(db_pool, client):
    await asyncio.gather(
        *[db_pool.execute(Queries.PROC) for _ in range(10)]
    )

    res = await client.get('/customers/1/statement')
    assert res.status_code == 200

    from_stmt = res.json()['recent_transactions']
    for t in from_stmt:
        t['ts'] = datetime.fromisoformat(t['ts'])

    from_db = await db_pool.fetch(Queries.TRANSACTIONS)
    assert from_stmt == [dict(t) for t in from_db]
