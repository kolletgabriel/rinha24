import pytest


SELECT_BALANCE = 'SELECT balance FROM customers WHERE id = 1;'
SELECT_OVERDRAFT = 'SELECT overdraft_limit FROM customers WHERE id = 1;'
SELECT_TRANSACTION = 'SELECT * FROM transactions WHERE customer_id = 1;'


@pytest.mark.anyio
async def test_credit_success(db_pool, client):
    async with db_pool.acquire() as conn:
        tr_val = 1000

        balance_before = await conn.fetchval(SELECT_BALANCE)
        res = client.post('/customers/1/transaction', json={
            'value': tr_val, 'type': 'c', 'desc': 'desc'
        })
        assert res.status_code == 200
        assert res.json()['balance'] == (balance_before + tr_val)

        balance_after = await conn.fetchval(SELECT_BALANCE)
        assert balance_after == (balance_before + tr_val)

        new_transaction = await conn.fetchrow(SELECT_TRANSACTION)
        assert new_transaction['value'] == tr_val
        assert new_transaction['type'] == 'c'


@pytest.mark.anyio
async def test_credit_failure(db_pool, client):
    async with db_pool.acquire() as conn:
        tr_value = -1000

        balance_before = await conn.fetchval(SELECT_BALANCE)
        res = client.post('/customers/1/transaction', json={
            'value': tr_value, 'type': 'c', 'desc': 'desc'
        })
        assert res.status_code == 422

        balance_after = await conn.fetchval(SELECT_BALANCE)
        assert balance_after == balance_before

        new_transaction = await conn.fetchrow(SELECT_TRANSACTION)
        assert new_transaction is None


@pytest.mark.anyio
async def test_debit_success(db_pool, client):
    async with db_pool.acquire() as conn:
        tr_value = await conn.fetchval(SELECT_OVERDRAFT)  # within the limit

        balance_before = await conn.fetchval(SELECT_BALANCE)
        res = client.post('/customers/1/transaction', json={
            'value': tr_value, 'type': 'd', 'desc': 'desc'
        })
        assert res.status_code == 200
        assert res.json()['balance'] == (balance_before - tr_value)

        balance_after = await conn.fetchval(SELECT_BALANCE)
        assert balance_after == (balance_before - tr_value)

        new_transaction = await conn.fetchrow(SELECT_TRANSACTION)
        assert new_transaction['value'] == tr_value
        assert new_transaction['type'] == 'd'


@pytest.mark.anyio
async def test_debit_failure(db_pool, client):
    async with db_pool.acquire() as conn:
        tr_value = (await conn.fetchval(SELECT_OVERDRAFT)) + 1  # past the limit

        balance_before = await conn.fetchval(SELECT_BALANCE)
        res = client.post('/customers/1/transaction', json={
            'value': tr_value, 'type': 'd', 'desc': 'desc'
        })
        assert res.status_code == 422

        balance_after = await conn.fetchval(SELECT_BALANCE)
        assert balance_before == balance_after

        new_transaction = await conn.fetchrow(SELECT_TRANSACTION)
        assert new_transaction is None
