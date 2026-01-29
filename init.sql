CREATE TABLE customers (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    balance BIGINT DEFAULT 0,
    overdraft_limit INT
);


CREATE TABLE transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INT REFERENCES customers,
    ts TIMESTAMPTZ DEFAULT NOW(),
    type CHAR NOT NULL,
    value BIGINT NOT NULL,
    description VARCHAR NOT NULL
);


INSERT INTO customers (overdraft_limit) VALUES
    (1000 * 100),
    (800 * 100),
    (10000 * 100),
    (100000 * 100),
    (5000 * 100);


CREATE PROCEDURE do_transaction(
    p_id INT,
    p_type CHAR,
    p_val BIGINT,
    p_desc VARCHAR,
    OUT overdraft_limit INT,
    OUT balance BIGINT
) LANGUAGE plpgsql AS $$
DECLARE
    curr_balance BIGINT;
    curr_overdraft_limit INT;
BEGIN
    SELECT c.balance, c.overdraft_limit
    INTO curr_balance, curr_overdraft_limit
    FROM customers AS c
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION no_data_found;
    ELSIF p_type = 'c' THEN
        UPDATE customers AS c
        SET balance = c.balance + p_val
        WHERE c.id = p_id
        RETURNING c.overdraft_limit, c.balance
        INTO overdraft_limit, balance;

        INSERT INTO transactions
        VALUES (DEFAULT, p_id, DEFAULT, p_type, p_val, p_desc);

        RETURN;
    ELSIF (curr_balance - p_val) < (curr_overdraft_limit * (-1)) THEN
        RAISE EXCEPTION integrity_constraint_violation;
    ELSE
        UPDATE customers AS c
        SET balance = c.balance - p_val
        WHERE c.id = p_id
        RETURNING c.overdraft_limit, c.balance
        INTO overdraft_limit, balance;

        INSERT INTO transactions
        VALUES (DEFAULT, p_id, DEFAULT, p_type, p_val, p_desc);
    END IF;
END;
$$;


CREATE PROCEDURE get_statement(
    p_id INT,
    OUT balance JSON,
    OUT recent_transactions JSON
) LANGUAGE plpgsql AS $$
BEGIN
    SELECT json_build_object(
        'total', c.balance,
        'stmt_date', now(),
        'overdraft_limit', c.overdraft_limit
    )
    INTO balance
    FROM customers c
    WHERE c.id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION no_data_found;
    END IF;

    SELECT json_agg(to_json(t))
    INTO recent_transactions
    FROM (
        SELECT value
            ,type
            ,description
            ,ts
        FROM transactions
        WHERE customer_id = p_id
        ORDER BY id DESC
        LIMIT 10
    ) AS t;
END;
$$;
