import asyncio

from ..utils import Queries

from pytest import mark


pytestmark = mark.anyio


async def test_404(db_pool, client):
    req_body = {'value': 1000, 'type': 'c', 'desc': 'desc'}

    res = await client.post('/customers/6/transaction', json=req_body)
    assert res.status_code == 404


async def test_credit_success(db_pool, client):
    req_body = {'value': 1000, 'type': 'c', 'desc': 'desc'}

    balance_before = await db_pool.fetchval(Queries.BALANCE)
    overdraft_limit = await db_pool.fetchval(Queries.OVERDRAFT)

    res = await client.post('/customers/1/transaction', json=req_body)
    assert res.status_code == 200

    res_body = res.json()
    assert {'balance', 'overdraft_limit'}.issubset(res_body)
    assert res_body['balance'] == (balance_before + req_body['value'])
    assert res_body['overdraft_limit'] == overdraft_limit

    balance_after = await db_pool.fetchval(Queries.BALANCE)
    assert balance_after == res_body['balance']

    new_transaction = await db_pool.fetchrow(Queries.TRANSACTION)
    assert new_transaction is not None
    assert new_transaction['value'] == req_body['value']
    assert new_transaction['type'] == req_body['type']
    assert new_transaction['desc'] == req_body['desc']


async def test_credit_failure(db_pool, client):
    req_body = {'value': -1000, 'type': 'c', 'desc': 'desc'}

    balance_before = await db_pool.fetchval(Queries.BALANCE)

    res = await client.post('/customers/1/transaction', json=req_body)
    assert res.status_code == 422

    balance_after = await db_pool.fetchval(Queries.BALANCE)
    assert balance_after == balance_before

    new_transaction = await db_pool.fetchrow(Queries.TRANSACTION)
    assert new_transaction is None


async def test_debit_success(db_pool, client):
    req_body = {
        'value': await db_pool.fetchval(Queries.OVERDRAFT),  # within the limit
        'type': 'd',
        'desc': 'desc'
    }

    balance_before = await db_pool.fetchval(Queries.BALANCE)
    overdraft_limit = req_body['value']

    res = await client.post('/customers/1/transaction', json=req_body)
    assert res.status_code == 200

    res_body = res.json()
    assert {'balance', 'overdraft_limit'}.issubset(res_body)
    assert res_body['balance'] == (balance_before - req_body['value'])
    assert res_body['overdraft_limit'] == overdraft_limit

    balance_after = await db_pool.fetchval(Queries.BALANCE)
    assert balance_after == res_body['balance']

    new_transaction = await db_pool.fetchrow(Queries.TRANSACTION)
    assert new_transaction is not None
    assert new_transaction['value'] == req_body['value']
    assert new_transaction['type'] == req_body['type']
    assert new_transaction['desc'] == req_body['desc']


async def test_debit_failure(db_pool, client):
    req_body = {
        'value': await db_pool.fetchval(Queries.OVERDRAFT) + 1,  # past the limit
        'type': 'd',
        'desc': 'desc'
    }

    balance_before = await db_pool.fetchval(Queries.BALANCE)
    overdraft_limit = req_body['value']

    res = await client.post('/customers/1/transaction', json=req_body)
    assert res.status_code == 422

    balance_after = await db_pool.fetchval(Queries.BALANCE)
    assert balance_after == balance_before

    new_transaction = await db_pool.fetchrow(Queries.TRANSACTION)
    assert new_transaction is None


async def test_debit_concurrently_fail(db_pool, client):
    req_body = { 'value': 100, 'type': 'd', 'desc': 'desc' }

    res = await asyncio.gather(*[
        client.post('/customers/1/transaction', json=req_body)
        for _ in range(1001)
    ])
    assert sum([1 for r in res if r.status_code == 200]) == 1000
    assert sum([1 for r in res if r.status_code == 422]) == 1

    balance_after = await db_pool.fetchval(Queries.BALANCE)
    overdraft_limit = await db_pool.fetchval(Queries.OVERDRAFT)
    assert balance_after >= overdraft_limit*(-1)


async def test_zero_sum_concurrently(db_pool, client):
    req_body_c = { 'value': 100, 'type': 'c', 'desc': 'desc' }
    req_body_d = { 'value': 100, 'type': 'd', 'desc': 'desc' }

    balance_before = await db_pool.fetchval(Queries.BALANCE)

    res = await asyncio.gather(
        *[client.post('/customers/1/transaction', json=req_body_c)
          for _ in range(1000)],
        *[client.post('/customers/1/transaction', json=req_body_d)
          for _ in range(1000)]
    )
    assert all([r.status_code == 200 for r in res])

    balance_after = await db_pool.fetchval(Queries.BALANCE)
    assert balance_before == balance_after
