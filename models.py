import json
from sqlite3 import Row
from typing import Optional

from lnbits.db import FilterModel
from pydantic import BaseModel, Field


class CreateUserData(BaseModel):
    user_name: str = Field(..., description="Name of the user")
    wallet_name: str = Field(..., description="Name of the wallet")
    extra: Optional[dict[str, str]] = Field(default=None)


class UpdateUserData(BaseModel):
    user_name: Optional[str] = Field(default=None, description="Name of the user")
    extra: Optional[dict[str, str]] = Field(
        default=None, description="Partial update for extra field"
    )


class CreateUserWallet(BaseModel):
    user_id: str = Field(..., description="Target user for this new wallet")
    wallet_name: str = Field(..., description="Name of the new wallet to create")


class User(BaseModel):
    id: str
    name: str
    admin: str
    extra: Optional[dict[str, str]] = Field(default=None)

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
