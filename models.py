from enum import Enum
from sqlite3 import Row
from typing import Any, Optional, Type

from fastapi.param_functions import Query
from pydantic import BaseModel, ValidationError


class Operator(Enum):
    GT = "gt"
    LT = "lt"
    EQ = "eq"
    NE = "ne"
    INCLUDE = "in"
    EXCLUDE = "ex"

    @property
    def as_sql(self):
        if self == Operator.EQ:
            return "="
        elif self == Operator.NE:
            return "!="
        elif self == Operator.INCLUDE:
            return "IN"
        elif self == Operator.EXCLUDE:
            return "NOT IN"
        elif self == Operator.GT:
            return ">"
        elif self == Operator.LT:
            return "<"
        else:
            raise ValueError('Unknown')


class Filter(BaseModel):
    field: str
    nested: Optional[list[str]]
    op: Operator = Operator.EQ
    values: list[Any]

    @classmethod
    def parse_query(cls, key: str, raw_values: list[Any], model: Type[BaseModel]):
        # Key format:
        # key[operator]
        # e.g. name[eq]
        if key.endswith(']'):
            split = key[:-1].split('[')
            if len(split) != 2:
                raise ValueError('Invalid key')
            field_names = split[0].split('.')
            op = split[1]
        else:
            field_names = key.split('.')
            op = "eq"

        field = field_names[0]
        nested = field_names[1:]

        if field in model.__fields__:
            compare_field = model.__fields__[field]
            values = []
            for raw_value in raw_values:
                # If there is a nested field, pydantic expects a dict, so the raw value is turned into a dict before
                # and the converted value is extracted afterwards
                for name in reversed(nested):
                    raw_value = {name: raw_value}
                validated, errors = compare_field.validate(raw_value, {}, loc='none')
                if errors:
                    raise ValidationError(errors=errors, model=model)
                for name in nested:
                    validated = validated[name]
                values.append(validated)
        else:
            raise ValueError('Unknown field')

        return cls(
            field=field,
            op=op,
            extras=nested,
            values=values
        )

    @property
    def statement(self):
        accessor = self.field
        for name in self.nested:
            accessor = f"({accessor} ->> \'{name}\')"

        if self.op in (Operator.INCLUDE, Operator.EXCLUDE):
            placeholders = ', '.join(['?'] * len(self.values))
            stmt = [f'{accessor} {self.op.as_sql} ({placeholders})']
        else:
            stmt = [f'{accessor} {self.op.as_sql} ?'] * len(self.values)

        return ' OR '.join(stmt)


class CreateUserData(BaseModel):
    user_name: str = Query(...)
    wallet_name: str = Query(...)
    admin_id: str = Query(...)
    email: str = Query("")
    password: str = Query("")
    extra: Optional[dict[str, str]] = Query(default=None)


class CreateUserWallet(BaseModel):
    user_id: str = Query(...)
    wallet_name: str = Query(...)
    admin_id: str = Query(...)


class User(BaseModel):
    id: str
    name: str
    admin: str
    email: Optional[str] = None
    password: Optional[str] = None
    extra: Optional[dict[str, str]]


class UserFilters(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    extra: Optional[dict[str, str]]


class Wallet(BaseModel):
    id: str
    admin: str
    name: str
    user: str
    adminkey: str
    inkey: str

    @classmethod
    def from_row(cls, row: Row) -> "Wallet":
        return cls(**dict(row))
