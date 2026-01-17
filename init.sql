CREATE TABLE customers (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    balance BIGINT DEFAULT 0,
    overdraft_limit INT
);

CREATE TABLE transactions (
    customer_id INT REFERENCES customers,
    ts TIMESTAMPTZ DEFAULT NOW(),
    value BIGINT NOT NULL,
    description VARCHAR NOT NULL,
    type CHAR NOT NULL,
    PRIMARY KEY (customer_id, ts)
);

INSERT INTO customers (overdraft_limit) VALUES
    (1000 * 100),
    (800 * 100),
    (10000 * 100),
    (100000 * 100),
    (5000 * 100);
