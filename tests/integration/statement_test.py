from datetime import datetime
import pytest


PROC = "CALL do_transaction(1, 'c', 100, 'desc', NULL, NULL);"

TRANSACTIONS = '''SELECT value, type, description, ts
                  FROM transactions
                  WHERE customer_id = 1
                  ORDER BY ts DESC;'''

OVERDRAFT = 'SELECT overdraft_limit FROM customers WHERE id = 1;'


@pytest.mark.anyio
async def test_is_empty(db_pool, client):
    async with db_pool.acquire() as conn:
        res = client.get('/customers/1/statement')

        stmt = res.json()
        balance = stmt['balance']
        recent_transactions = stmt['recent_transactions']

        assert res.status_code == 200
        assert balance['total'] == 0
        assert balance['overdraft_limit'] == await conn.fetchval(OVERDRAFT)
        assert recent_transactions is None


@pytest.mark.anyio
async def test_shows_10_at_most(db_pool, client):
    async with db_pool.acquire() as conn:
        for _ in range(9):
            await conn.execute(PROC)
        res = client.get('/customers/1/statement')
        assert res.status_code == 200
        assert len(res.json()['recent_transactions']) == 9

        for _ in range(2):
            await conn.execute(PROC)
        res = client.get('/customers/1/statement')
        assert res.status_code == 200
        assert len(res.json()['recent_transactions']) == 10


@pytest.mark.anyio
async def test_is_sorted(db_pool, client):
    async with db_pool.acquire() as conn:
        for _ in range(10):
            await conn.execute(PROC)

        res = client.get('/customers/1/statement')
        assert res.status_code == 200

        from_stmt = res.json()['recent_transactions']
        for t in from_stmt:
            t['ts'] = datetime.fromisoformat(t['ts'])

        from_db = await conn.fetch(TRANSACTIONS)
        assert from_stmt == [dict(t) for t in from_db]
