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
    assert new_transaction['description'] == req_body['desc']


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
    assert new_transaction['description'] == req_body['desc']


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
