from typing import Literal, Annotated
from pydantic import BaseModel, PositiveInt, StringConstraints


class Transaction(BaseModel):
    value: PositiveInt
    type: Literal['c', 'd']
    desc: Annotated[str, StringConstraints(min_length=1, max_length=10)]
