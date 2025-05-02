import json
from sqlite3 import Row
from typing import List, Optional

from lnbits.core.crud import get_payments
from lnbits.core.models import CreateWallet, Payment
from lnbits.core.views.api import api_create_account
from lnbits.core.views.user_api import (  # type: ignore
    api_users_create_user_wallet,
    api_users_delete_user_wallet,
)
from lnbits.db import Database, Filters

from .models import (
    CreateUserData,
    UpdateUserData,
    User,
    UserDetailed,
    UserFilters,
    Wallet,
)

db = Database("ext_usermanager")


async def create_usermanager_user(admin_id: str, data: CreateUserData) -> UserDetailed:
    wallet = await api_create_account(CreateWallet(name=data.user_name))
    assert wallet, "Newly created user couldn't be retrieved"

    user_data = User(
        id=wallet.user,
        name=data.user_name,
        admin=admin_id,
        extra=data.extra,
    )

    await db.execute(
        """
        INSERT INTO usermanager.users (id, name, admin, extra)
        VALUES (:id, :name, :admin, :extra)
        """,
        {
            "id": user_data.id,
            "name": user_data.name,
            "admin": user_data.admin,
            "extra": json.dumps(user_data.extra),  # Needed for adding as json
        },
    )

    wallet_data = Wallet(
        id=wallet.id,
        admin=admin_id,
        name=data.wallet_name,
        user=wallet.user,
        adminkey=wallet.adminkey,
        inkey=wallet.inkey,
    )
    await db.insert("usermanager.wallets", wallet_data)

    user_created = await get_usermanager_user(wallet.user)
    assert user_created, "Newly created user couldn't be retrieved"
    return user_created


async def get_usermanager_user(user_id: str) -> Optional[UserDetailed]:
    row: Row = await db.fetchone(
        "SELECT * FROM usermanager.users WHERE id = :id", {"id": user_id}
    )
    wallets = await get_usermanager_users_wallets(user_id=user_id)
    if row:
        user_data = User.from_row(row)
        return UserDetailed(
            id=user_data.id,
            name=user_data.name,
            admin=user_data.admin,
            extra=user_data.extra,
            wallets=wallets,
        )
    return None


async def get_usermanager_users(
    admin: str, filters: Filters[UserFilters]
) -> list[User]:
    rows: list[Row] = await db.fetchall(
        f"SELECT * FROM usermanager.users WHERE admin = :admin {filters.pagination()}",
        {"admin": admin},
    )
    return [User.from_row(row) for row in rows]


async def delete_usermanager_user(user_id: str, delete_core: bool = True) -> None:
    if delete_core:
        wallets = await get_usermanager_wallets(user_id)
        for wallet in wallets:
            await api_users_delete_user_wallet(user_id=user_id, wallet=wallet.id)
    await db.execute("DELETE FROM usermanager.users WHERE id = :id", {"id": user_id})
    await db.execute(
        "DELETE FROM usermanager.wallets WHERE user = :user", {"user": user_id}
    )


async def create_usermanager_wallet(
    user_id: str, wallet_name: str, admin_id: str
) -> Wallet:
    wallet = await api_users_create_user_wallet(
        user_id=user_id, name=wallet_name, currency=None
    )
    wallet_data = Wallet(
        id=wallet.id,
        admin=admin_id,
        name=wallet_name,
        user=user_id,
        adminkey=wallet.adminkey,
        inkey=wallet.inkey,
    )
    await db.insert("usermanager.wallets", wallet_data)
    wallet_created = await get_usermanager_wallet(wallet.id)
    assert wallet_created, "Newly created wallet couldn't be retrieved"
    return wallet_created


async def get_usermanager_wallet(wallet_id: str) -> Optional[Wallet]:
    return await db.fetchone(
        "SELECT * FROM usermanager.wallets WHERE id = :id",
        {"id": wallet_id},
        Wallet,
    )


async def get_usermanager_wallets(admin_id: str) -> List[Wallet]:
    return await db.fetchall(
        "SELECT * FROM usermanager.wallets WHERE admin = :admin", {"admin": admin_id}
    )


async def get_usermanager_users_wallets(user_id: str) -> List[Wallet]:
    return await db.fetchall(
        "SELECT * FROM usermanager.wallets WHERE user = :user", {"user": user_id}
    )


async def get_usermanager_wallet_transactions(wallet_id: str) -> List[Payment]:
    return await get_payments(
        wallet_id=wallet_id, complete=True, pending=False, outgoing=True, incoming=True
    )


async def delete_usermanager_wallet(wallet_id: str, user_id: str) -> None:
    await api_users_delete_user_wallet(user_id=user_id, wallet=wallet_id)
    return await db.execute(
        "DELETE FROM usermanager.wallets WHERE id = :id", {"id": wallet_id}
    )


async def update_usermanager_user(
    user_id: str, admin_id: str, data: UpdateUserData
) -> Optional[UserDetailed]:
    cols = []
    values = {}
    if data.user_name:
        cols.append("name = :name")
        values["name"] = data.user_name
    if data.extra:
        row: Row = await db.fetchone(
            "SELECT extra FROM usermanager.users WHERE id = :id", {"id": user_id}
        )
        extra = json.loads(row["extra"]) if row["extra"] else {}
        extra.update(data.extra)
        cols.append("extra = :extra")
        values["extra"] = json.dumps(extra)
    values["user_id"] = user_id
    values["admin_id"] = admin_id
    await db.execute(
        f"""
        UPDATE usermanager.users
        SET {", ".join(cols)}
        WHERE id = :user_id AND admin = :admin_id
        """,
        values,
    )
    return await get_usermanager_user(user_id)
