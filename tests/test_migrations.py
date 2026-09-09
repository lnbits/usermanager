import json
import sqlite3
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from lnbits.db import SQLITE, Connection, Filters
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from .. import crud
from ..migrations import (
    m001_initial,
    m002_add_user_attrs_column,
    m003_migrate_email_password_to_extra,
)
from ..models import UpdateUserData, User, UserDetailed, UserFilters


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as connection:
        await connection.execute(text("ATTACH ':memory:' AS usermanager"))
        db = Connection(connection, SQLITE, "ext_usermanager", "usermanager")
        await m001_initial(db)
        await m002_add_user_attrs_column(db)
        yield db
    await engine.dispose()


async def insert_user(db, user_id, email, password, extra):
    # Seed stored values directly, without LNbits' input sanitisation.
    await db.conn.execute(
        text(
            "INSERT INTO usermanager.users (id, name, admin, email, password, extra) "
            "VALUES (:id, :name, :admin, :email, :password, :extra)"
        ),
        {
            "id": user_id,
            "name": f"name-{user_id}",
            "admin": f"admin-{user_id}",
            "email": email,
            "password": password,
            "extra": extra,
        },
    )
    await db.conn.commit()


@pytest.mark.asyncio
async def test_m003_preserves_users_and_wallets(db):
    await insert_user(db, "user-one", "one@example.invalid", "synthetic-one", None)
    await insert_user(db, "user-two", "", None, '{"custom":{"nested":[1,true]}}')
    await db.execute(
        'INSERT INTO usermanager.wallets (id, admin, name, "user", adminkey, inkey) '
        "VALUES ('wallet', 'admin', 'wallet-name', 'user-one', "
        "'dummy-admin', 'dummy-in')"
    )
    wallets = await db.fetchall("SELECT * FROM usermanager.wallets")

    await m003_migrate_email_password_to_extra(db)

    users = await db.fetchall("SELECT * FROM usermanager.users ORDER BY id")
    assert len(users) == 2
    for user in users:
        assert set(user) == {"id", "name", "admin", "extra"}
        assert user["name"] == f"name-{user['id']}"
        assert user["admin"] == f"admin-{user['id']}"
    assert json.loads(users[0]["extra"]) == {
        "extra1": "one@example.invalid",
        "extra2": "synthetic-one",
    }
    assert json.loads(users[1]["extra"]) == {
        "custom": {"nested": [1, True]},
        "extra1": "",
        "extra2": None,
    }
    assert await db.fetchall("SELECT * FROM usermanager.wallets") == wallets


@pytest.mark.asyncio
async def test_m003_preserves_stored_text(db):
    value = '<synthetic> &amp; "unicode: £"'
    await insert_user(db, "user", value, value, json.dumps({"custom": value}))
    await m003_migrate_email_password_to_extra(db)
    user = await db.fetchone("SELECT extra FROM usermanager.users")
    assert json.loads(user["extra"]) == {
        "custom": value,
        "extra1": value,
        "extra2": value,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"custom": None},
        {"custom": {"nested": [1, True, None, {"text": "keep"}]}},
        {"number": 42, "flag": False, "fraction": 1.5},
    ],
)
async def test_m003_metadata_remains_readable_through_crud(db, monkeypatch, metadata):
    await insert_user(db, "user", None, "", json.dumps(metadata))
    await m003_migrate_email_password_to_extra(db)
    expected = {**metadata, "extra1": None, "extra2": ""}
    row = await db.fetchone("SELECT * FROM usermanager.users")
    user = User.from_row(row)
    assert json.dumps(user.extra, sort_keys=True) == json.dumps(
        expected, sort_keys=True
    )

    monkeypatch.setattr(crud, "db", db)
    users = await crud.get_usermanager_users("admin-user", Filters(model=UserFilters))
    assert len(users) == 1
    detailed = await crud.get_usermanager_user("user")
    assert detailed is not None
    assert detailed.wallets == []
    # Exercise both API response models, including their JSON serialisation.
    for response in (
        User.parse_obj(users[0].dict()),
        UserDetailed.parse_obj(detailed.dict()),
    ):
        actual = json.loads(response.json())["extra"]
        assert json.dumps(actual, sort_keys=True) == json.dumps(
            expected, sort_keys=True
        )

    updated = await crud.update_usermanager_user(
        "user", "admin-user", UpdateUserData(user_name="renamed")
    )
    assert updated is not None
    assert updated.name == "renamed"
    assert json.dumps(updated.extra, sort_keys=True) == json.dumps(
        expected, sort_keys=True
    )


@pytest.mark.asyncio
async def test_m003_empty_database(db):
    await m003_migrate_email_password_to_extra(db)
    columns = await db.fetchall("PRAGMA usermanager.table_info(users)")
    assert [column["name"] for column in columns] == ["id", "name", "admin", "extra"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "extra",
    [
        "",
        "not-json",
        "null",
        "[]",
        '"text"',
        "42",
        "true",
        '{"extra1":"conflict"}',
        '{"extra2":"conflict"}',
    ],
)
async def test_m003_rejects_unsafe_extra_before_any_write(db, extra):
    await insert_user(db, "first", "one@example.invalid", "synthetic-one", None)
    await insert_user(db, "second", "two@example.invalid", "synthetic-two", extra)
    before = await db.fetchall("SELECT * FROM usermanager.users ORDER BY id")
    with pytest.raises(ValueError, match="Cannot migrate users:"):
        await m003_migrate_email_password_to_extra(db)
    assert await db.fetchall("SELECT * FROM usermanager.users ORDER BY id") == before
    tables = await db.fetchall(
        "SELECT name FROM usermanager.sqlite_master WHERE name = 'users_new'"
    )
    assert not tables


@pytest.mark.asyncio
async def test_m003_accepts_identical_previous_update(db):
    extra = {"custom": "keep", "extra1": "one@example.invalid", "extra2": None}
    await insert_user(db, "user", "one@example.invalid", None, json.dumps(extra))
    await m003_migrate_email_password_to_extra(db)
    user = await db.fetchone("SELECT extra FROM usermanager.users")
    assert json.loads(user["extra"]) == extra


@pytest.mark.asyncio
async def test_m003_retries_after_interrupted_updates(db, monkeypatch):
    await insert_user(db, "first", "one@example.invalid", None, None)
    await insert_user(db, "second", "two@example.invalid", None, None)
    execute = db.execute
    updates = 0

    async def interrupted_execute(query, values=None):
        nonlocal updates
        if query.startswith("UPDATE"):
            updates += 1
            if updates == 2:
                raise RuntimeError("Synthetic interruption")
        return await execute(query, values)

    monkeypatch.setattr(db, "execute", interrupted_execute)
    with pytest.raises(RuntimeError, match="Synthetic interruption"):
        await m003_migrate_email_password_to_extra(db)
    monkeypatch.setattr(db, "execute", execute)

    await m003_migrate_email_password_to_extra(db)
    users = await db.fetchall("SELECT id, extra FROM usermanager.users ORDER BY id")
    assert [json.loads(user["extra"])["extra1"] for user in users] == [
        "one@example.invalid",
        "two@example.invalid",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("row_type", ["dict", "sqlite_row"])
async def test_m003_named_row_access(row_type):
    values = {"id": "user", "email": None, "password": "", "extra": None}
    if row_type == "sqlite_row":
        with sqlite3.connect(":memory:") as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT :id AS id, :email AS email, "
                ":password AS password, :extra AS extra",
                values,
            ).fetchone()
    else:
        row = values
    db = AsyncMock()
    db.fetchall.return_value = [row]
    await m003_migrate_email_password_to_extra(db)
    update = db.execute.call_args_list[0].args[1]
    assert update["user_id"] == "user"
    assert json.loads(update["extra"]) == {"extra1": None, "extra2": ""}
