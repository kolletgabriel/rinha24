# Rinha de Backend 2024

**TL;DR:** A playful exercise on concurrency by implementing a RESTful API to perform concurrent operations simulating bank transactions, done with an asynchronous Python web framework and PostgreSQL. The official instructions (in portuguese) can be found [here](https://github.com/zanfranceschi/rinha-de-backend-2024-q1#o-que-precisa-ser-feito).

## The Challenge

First and foremost, the word "rinha" stands for "brawl", "cockfight", "cage match", "rumble" *etc*. It's a challenge started in 2023, made for/by the dev community in Brazil, and which constists in delivering a RESTful service easy to implement yet tricky to make it survive the load tests.

This edition consists basically in simulating a banking system that will be tested for consistency and responsiveness under high concurrency workloads. The entity of the **customer** has a **balance** which will be altered by **transactions** adding or subtracting amounts. A **statement** must also be possible to generate, showing the current balance and the last transactions for a given customer.

There must be 5 customers (or *accounts* for that matter) registered in the database, all with an initial balance of U$ 0.00 but each one with a different overdraft limit, exactly as follows:

|id|overdraft_limit|balance|
|--|---------------|-------|
|1 |100000         |0      |
|2 |80000          |0      |
|3 |1000000        |0      |
|4 |10000000       |0      |
|5 |500000         |0      |

The `overdraft_limit` tells how much `balance` can go below 0. That is: customer with `id == 1` can't have `balance < -100000`, for instance.

### Endpoints

The service must provide 2 endpoints: 1 for making transactions, and the other to fetch them. Also, it's worth noting that the original path names for each endpoint were translated to english in this implementation.

#### `POST /customers/<id>/transaction`

Make a transaction for the customer whose id is `<id>`. The request must have a body with the following fields:

- `"value"` which must be a positive integer representing **cents**;
- `"type"` which must be either `"c"` for **credit** or `"d"` for **debit**;
- `"desc"` which must be a string between 1 and 10 characters length representing the **description** of the transaction.

Here's an example of a valid request body:

```json
{
   "value": 10000,
   "type": "c",
   "desc": "desc"
}
```

A `POST` request on `/customers/5/transaction` with the body above would **add** 10000 cents on customer 5's balance. If `"type"` was `"d"`, the request would instead **subtract** the amount from the balance, but only if the resulting value stayed under the customer's `overdraft_limit`.

A successful transaction returns the HTTP status `200 OK`, and the response body contains the `overdraft_limit` and the balance after the transaction. Any failed transaction returns `422 UNPROCESSABLE CONTENT` with no response body.

#### `GET /customers/<id>/statement`

Fetch the customer's bank statement. The statement shows the current *state* of the customer's account and its last 10 registered transactions, sorted from most to least recent. It consists of a json object containing the following fields:

- `"balance"` which is a nested object:
    - `"total"` with the **actual balance**;
    - `"stmt_date"` with the the timestamp for the current statement;
    - `"overdraft_limit"` with the customer's limit for overdraft;
- `"recent_transactions"` which is a list of objects, each one representing a single transaction with all its fields already mentioned in the section above, plus a `"ts"` field for the transaction timestamp.

Here's an example of a valid statement, for a customer with 2 registered transactions:

```json
{
   "balance": {
      "total": 220000,
      "stmt_date": "2024-01-17T02:34:41.217753Z",
      "overdraft_limit": 300000
   },
   "recent_transactions": [
      {
         "value": 2000,
         "type": "d",
         "desc": "foo",
         "ts": "2024-01-17T02:34:38.641918Z"
      },
      { 
         "value": 600000,
         "type": "c",
         "desc": "bar",
         "ts": "2024-01-17T02:34:38.543030Z"
      },
   ]
}
```

The status code for the response is `200 OK`.

### Restrictions

Everything is implemented under the following restrinctions:

- at least 4 services: database, load balancer and 2 instances of the API (more services e.g. for cache were optional);
- maximum of 1.5 CPUs and 550MB of RAM distributed across **all** services;
- json as the representation format.

The orchestration is done via Docker Compose.

### Load Test

The test script is written in Scala, using the framework Gatling. It runs for 4m4s. It performs concurrent calls to the endpoints listed above and checks for any consistency issues.

### Winning Criteria

The **payment** for the API is of U$ 100,000.00 with some possible deductions declared in an **SLA** which demands that at least 98% of all responses happen under the mark of 250ms. The SLA also declares penalties for any inconsistencies found in any customer's account.

For each percentage below 98, a deduction of U$ 1,000.00 is applied. For instance: if only 96.5% of the responses happened under 250ms, the deduction would be of U$ 1,500.00.

For each inconsistency found, a deduction of U$ 803.01 is applied. A customer whose `balance < overdraft_limit * (-1)` is an inconsistency, as well as a customer whose balance isn't the sum of all their related transactions.

## About this Implementation

The entire stack is composed of:

- Python:
    - Starlette as the ASGI framework;
    - Uvicorn as the ASGI server;
    - asyncpg as the database driver;
    - Pydantic as the validation tool;
- PostgreSQL;
- Nginx.

The main strategy was to allocate most of the resources to Postgres and centralize in it all the business logic by using **stored procedures** as the main processing unit for each endpoint. Python's role is just input validation and basic communication with the database just to call the procedures.

This isn't, of course, good practice in real production systems! But, given the nature of the challenge and the size of the project (plus my *taste* for minimalism), it's a valid strategy.

### How to Run it

1. Run the script `scripts/start-benchmark.sh`. It'll set up the `compose` stack and run the Gatling container to perform the tests, placing the results under `benchmarks/results`;
2. Run the script `scripts/calculate-payment.py`. It'll check the reports for nonconformities with the SLA and calculate the final payment. By default, the script finds the last simulation that ran, but any directory containing report files from previous simulations can be passed as an argument.
