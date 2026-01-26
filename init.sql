CREATE TABLE customers (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    balance BIGINT DEFAULT 0,
    overdraft_limit INT
);

CREATE TABLE transactions (
    customer_id INT REFERENCES customers,
    ts TIMESTAMPTZ DEFAULT NOW(),
    type CHAR NOT NULL,
    value BIGINT NOT NULL,
    description VARCHAR NOT NULL,
    PRIMARY KEY (customer_id, ts)
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
        VALUES (p_id, DEFAULT, p_type, p_val, p_desc);

        RETURN;
    ELSIF abs(curr_balance - p_val) > curr_overdraft_limit THEN
        RAISE EXCEPTION integrity_constraint_violation;
    ELSE
        UPDATE customers AS c
        SET balance = c.balance - p_val
        WHERE c.id = p_id
        RETURNING c.overdraft_limit, c.balance
        INTO overdraft_limit, balance;

        INSERT INTO transactions
        VALUES (p_id, DEFAULT, p_type, p_val, p_desc);
    END IF;
END;
$$;
