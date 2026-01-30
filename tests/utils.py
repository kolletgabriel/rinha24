class Queries:
    BALANCE = 'SELECT balance FROM customers WHERE id = 1;'

    OVERDRAFT = 'SELECT overdraft_limit FROM customers WHERE id = 1;'

    TRANSACTION = 'SELECT * FROM transactions WHERE customer_id = 1;'

    TRANSACTIONS = '''SELECT value, type, "desc", ts
                      FROM transactions
                      WHERE customer_id = 1
                      ORDER BY id DESC;'''

    PROC = "CALL do_transaction(1, 'c', 100, 'desc', NULL, NULL);"
