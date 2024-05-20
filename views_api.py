from http import HTTPStatus
from typing import List

from fastapi import Depends, Query
from pydantic import Json
from starlette.exceptions import HTTPException

from lnbits.core.crud import get_user, update_user_extension
from lnbits.core.models import Payment
from lnbits.db import Filters
from lnbits.decorators import (
    WalletTypeInfo,
    get_key_type,
    parse_filters,
    require_admin_key,
)
from lnbits.helpers import generate_filter_params_openapi

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
    update_usermanager_user,
)
from .models import (
    CreateUserData,
    CreateUserWallet,
    UpdateUserData,
    User,
    UserDetailed,
    UserFilters,
    Wallet,
)


@usermanager_ext.get(
    "/api/v1/users",
    status_code=HTTPStatus.OK,
    name="User List",
    summary="get list of users",
    response_description="list of users",
    response_model=List[User],
    openapi_extra=generate_filter_params_openapi(UserFilters),
)
async def api_usermanager_users(
    wallet: WalletTypeInfo = Depends(require_admin_key),
    filters: Filters[UserFilters] = Depends(parse_filters(UserFilters)),
    extra: Json = Query(None, description="Can be used to filter users by extra fields"),
):
    admin_id = wallet.wallet.user
    users = await get_usermanager_users(admin_id, filters)
    if extra:
        return [
            user for user in users
            if all(
                user.extra and user.extra.get(key) == value
                for key, value in extra.items()
            )
        ]
    return users


@usermanager_ext.get(
    "/api/v1/users/{user_id}",
    name="User Get",
    summary="Get a specific user",
    description="get user",
    response_description="user if user exists",
    dependencies=[Depends(get_key_type)],
    response_model=UserDetailed
)
async def api_usermanager_user(user_id: str) -> UserDetailed:
    user = await get_usermanager_user(user_id)
    if not user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')
    return user


@usermanager_ext.post(
    "/api/v1/users",
    name="User Create",
    summary="Create a new user",
    description="Create a new user",
    response_description="New User",
    response_model=UserDetailed,
)
async def api_usermanager_users_create(
    data: CreateUserData,
    info: WalletTypeInfo = Depends(require_admin_key)
) -> UserDetailed:
    return await create_usermanager_user(info.wallet.user, data)


@usermanager_ext.put(
    "/api/v1/users/{user_id}",
    name="User Update",
    summary="Update a user",
    description="Update a user",
    response_description="Updated user",
    response_model=UserDetailed,
)
async def api_usermanager_users_create(
    user_id: str,
    data: UpdateUserData,
    info: WalletTypeInfo = Depends(require_admin_key)
) -> UserDetailed:
    return await update_usermanager_user(user_id, info.wallet.user, data)


@usermanager_ext.delete(
    "/api/v1/users/{user_id}",
    name="User Delete",
    summary="Delete a user",
    description="Delete a user",
    dependencies=[Depends(require_admin_key)],
    responses={404: {"description": "User does not exist."}},
    status_code=HTTPStatus.OK,
)
async def api_usermanager_users_delete(
    user_id,
    delete_core: bool = Query(True),
) -> None:
    user = await get_usermanager_user(user_id)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="User does not exist."
        )
    await delete_usermanager_user(user_id, delete_core)


# Activate Extension


@usermanager_ext.post(
    "/api/v1/extensions",
    name="Extension Toggle",
    summary="Extension Toggle",
    description="Extension Toggle",
    response_model=dict[str, str],
    responses={404: {"description": "User does not exist."}},
)
async def api_usermanager_activate_extension(
    extension: str = Query(...), userid: str = Query(...), active: bool = Query(...)
) -> dict:
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
    name="Create wallet for user",
    summary="Create wallet for user",
    description="Create wallet for user",
    response_model=Wallet,
    dependencies=[Depends(get_key_type)],
)
async def api_usermanager_wallets_create(
    data: CreateUserWallet, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Wallet:
    return await create_usermanager_wallet(
        user_id=data.user_id, wallet_name=data.wallet_name, admin_id=wallet.wallet.user
    )


@usermanager_ext.get(
    "/api/v1/wallets",
    name="Get all user wallets",
    summary="Get all user wallets",
    description="Get all user wallets",
    response_model=List[Wallet],
)
async def api_usermanager_wallets(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> List[Wallet]:
    admin_id = wallet.wallet.user
    return await get_usermanager_wallets(admin_id)


@usermanager_ext.get(
    "/api/v1/transactions/{wallet_id}",
    name="Get all wallet transactions",
    summary="Get all wallet transactions",
    description="Get all wallet transactions",
    response_model=List[Payment],
    dependencies=[Depends(get_key_type)],
)
async def api_usermanager_wallet_transactions(wallet_id) -> List[Payment]:
    return await get_usermanager_wallet_transactions(wallet_id)


@usermanager_ext.get(
    "/api/v1/wallets/{user_id}",
    name="Get user wallet",
    summary="Get user wallet",
    description="Get user wallet",
    response_model=List[Wallet],
    dependencies=[Depends(require_admin_key)],
)
async def api_usermanager_users_wallets(user_id) -> List[Wallet]:
    return await get_usermanager_users_wallets(user_id)


@usermanager_ext.delete(
    "/api/v1/wallets/{wallet_id}",
    name="Delete wallet by id",
    summary="Delete wallet by id",
    description="Delete wallet by id",
    response_model=str,
    dependencies=[Depends(require_admin_key)],
    status_code=HTTPStatus.OK,
)
async def api_usermanager_wallets_delete(wallet_id) -> None:
    get_wallet = await get_usermanager_wallet(wallet_id)
    if not get_wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Wallet does not exist."
        )
    await delete_usermanager_wallet(wallet_id, get_wallet.user)
