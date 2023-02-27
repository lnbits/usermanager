from http import HTTPStatus
from typing import Optional, Type

import fastapi
from fastapi import Depends, Query
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from lnbits.core import Payment, update_user_extension
from lnbits.core.crud import get_user
from lnbits.decorators import WalletTypeInfo, get_key_type, require_admin_key

from . import usermanager_ext
from .crud import (
    create_usermanager_user,
    create_usermanager_wallet,
    delete_usermanager_user,
    delete_usermanager_wallet,
    get_usermanager_user,
    get_usermanager_users,
    get_usermanager_users_wallets,
    get_usermanager_wallet,
    get_usermanager_wallet_transactions,
    get_usermanager_wallets,
)
from .models import (
    CreateUserData,
    CreateUserWallet,
    Filter,
    User,
    UserDetailed,
    UserFilters,
    Wallet,
)


def get_filter_dependency(model: Type[BaseModel]):
    def dependency(request: fastapi.Request):
        filters = []
        for key in request.query_params.keys():
            try:
                filters.append(
                    Filter.parse_query(key, request.query_params.getlist(key), model)
                )
            except ValueError:
                continue
        return filters

    return dependency


@usermanager_ext.get(
    "/api/v1/users",
    status_code=HTTPStatus.OK,
    response_model=list[User]
)
async def api_usermanager_users(
    wallet: WalletTypeInfo = Depends(require_admin_key),
    filters: list[Filter] = Depends(get_filter_dependency(UserFilters))
):
    """
    Retrieves all users, supporting flexible filtering (LHS Brackets).

    ### Syntax
    `field[op]=value`

    ### Example Query Strings
    ```
    email[eq]=test@mail.com
    name[ex]=dont-want&name[ex]=dont-want-too
    extra.role[ne]=role-id
    ```
    ### Operators
    - eq, ne
    - gt, lt
    - in (include)
    - ex (exclude)

    Fitlers are AND-combined
    """
    admin_id = wallet.wallet.user
    return await get_usermanager_users(admin_id, *filters)


@usermanager_ext.get(
    "/api/v1/users/{user_id}",
    status_code=HTTPStatus.OK,
    dependencies=[Depends(get_key_type)],
    response_model=UserDetailed
)
async def api_usermanager_user(user_id):
    user = await get_usermanager_user(user_id)
    if not user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')
    return user


@usermanager_ext.post(
    "/api/v1/users",
    status_code=HTTPStatus.CREATED,
    dependencies=[Depends(get_key_type)],
    response_model=UserDetailed
)
async def api_usermanager_users_create(data: CreateUserData):
    return await create_usermanager_user(data)


@usermanager_ext.delete(
    "/api/v1/users/{user_id}", dependencies=[Depends(require_admin_key)]
)
async def api_usermanager_users_delete(
    user_id,
    delete_core: bool = Query(True),
):
    user = await get_usermanager_user(user_id)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="User does not exist."
        )
    await delete_usermanager_user(user_id, delete_core)
    return "", HTTPStatus.NO_CONTENT


# Activate Extension


@usermanager_ext.post("/api/v1/extensions")
async def api_usermanager_activate_extension(
    extension: str = Query(...), userid: str = Query(...), active: bool = Query(...)
):
    user = await get_user(userid)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="User does not exist."
        )
    await update_user_extension(user_id=userid, extension=extension, active=active)
    return {"extension": "updated"}


# Wallets


@usermanager_ext.post(
    "/api/v1/wallets",
    dependencies=[Depends(get_key_type)],
    response_model=Wallet
)
async def api_usermanager_wallets_create(data: CreateUserWallet):
    return await create_usermanager_wallet(
        user_id=data.user_id, wallet_name=data.wallet_name, admin_id=data.admin_id
    )


@usermanager_ext.get("/api/v1/wallets", response_model=list[Wallet])
async def api_usermanager_wallets(
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    admin_id = wallet.wallet.user
    return await get_usermanager_wallets(admin_id)


@usermanager_ext.get(
    "/api/v1/transactions/{wallet_id}",
    dependencies=[Depends(get_key_type)],
    response_model=list[Payment]
)
async def api_usermanager_wallet_transactions(wallet_id):
    return await get_usermanager_wallet_transactions(wallet_id)


@usermanager_ext.get(
    "/api/v1/wallets/{user_id}",
    dependencies=[Depends(require_admin_key)],
    response_model=list[Wallet]
)
async def api_usermanager_users_wallets(user_id):
    return await get_usermanager_users_wallets(user_id)


@usermanager_ext.delete(
    "/api/v1/wallets/{wallet_id}", dependencies=[Depends(require_admin_key)]
)
async def api_usermanager_wallets_delete(wallet_id):
    get_wallet = await get_usermanager_wallet(wallet_id)
    if not get_wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Wallet does not exist."
        )
    await delete_usermanager_wallet(wallet_id, get_wallet.user)
    return "", HTTPStatus.NO_CONTENT
