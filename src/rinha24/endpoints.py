from .models import Transaction

from asyncpg.exceptions import (
    NoDataFoundError,
    IntegrityConstraintViolationError
)

from pydantic import ValidationError

from starlette.requests import Request
from starlette.responses import JSONResponse, Response


async def transaction(request: Request[State]) -> Response:
    customer_id = request.path_params['id']
    request_body = await request.json()
    try:
        new_transaction_request = Transaction(**request_body)
    except ValidationError:
        return Response('', status_code=422)

    pool = request.state.pool
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchrow(
                'CALL do_transaction($1, $2, $3, $4, NULL, NULL);',
                customer_id,
                new_transaction_request.type,
                new_transaction_request.value,
                new_transaction_request.desc
            )
            return JSONResponse(dict(result))
        except NoDataFoundError:
            return Response('', status_code=404)
        except IntegrityConstraintViolationError:
            return Response('', status_code=422)


def statement(request: Request) -> JSONResponse:
    ...
