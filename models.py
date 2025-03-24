import json
from sqlite3 import Row
from typing import Optional

from fastapi.param_functions import Query
from lnbits.db import FilterModel
from pydantic import BaseModel


class CreateUserData(BaseModel):
    user_name: str = Query(..., description="Name of the user")
    wallet_name: str = Query(..., description="Name of the wallet")
    extra: Optional[dict[str, str]] = Query(default=None)


class UpdateUserData(BaseModel):
    user_name: Optional[str] = Query(default=None, description="Name of the user")
    extra: Optional[dict[str, str]] = Query(
        default=None, description="Partial update for extra field"
    )


class CreateUserWallet(BaseModel):
    user_id: str = Query(..., description="Target user for this new wallet")
    wallet_name: str = Query(..., description="Name of the new wallet to create")


class User(BaseModel):
    id: str
    name: str
    admin: str
    extra: str

    @classmethod
    def from_row(cls, row: Row):
        attrs = dict(row)
        attrs["extra"] = json.loads(attrs["extra"]) if attrs["extra"] else None
        return cls(**attrs)


class UserFilters(FilterModel):
    id: str
    name: str
    email: Optional[str] = None


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


class UserDetailed(User):
    wallets: list[Wallet]
