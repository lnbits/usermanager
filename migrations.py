import json


async def m001_initial(db):
    """
    Initial users table.
    """
    await db.execute(
        """
        CREATE TABLE usermanager.users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            admin TEXT NOT NULL,
            email TEXT,
            password TEXT
        );
    """
    )

    """
    Initial wallets table.
    """
    await db.execute(
        """
        CREATE TABLE usermanager.wallets (
            id TEXT PRIMARY KEY,
            admin TEXT NOT NULL,
            name TEXT NOT NULL,
            "user" TEXT NOT NULL,
            adminkey TEXT NOT NULL,
            inkey TEXT NOT NULL
        );
    """
    )


async def m002_add_user_attrs_column(db):
    """
    Initial users table.
    """
    await db.execute(
        """
        ALTER TABLE usermanager.users ADD COLUMN extra TEXT
    """
    )


async def m003_migrate_email_password_to_extra(db):
    """
    Migrate email and password to 'extra' JSON field, then drop the original columns.
    """

    # Step 1: Migrate email/password to extra column
    users = await db.fetchall(
        "SELECT id, email, password, extra FROM usermanager.users"
    )

    # Validate every row before writing: LNbits commits each execute separately.
    updates = []
    for user in users:
        try:
            extra = json.loads(user["extra"]) if user["extra"] is not None else {}
        except (TypeError, ValueError):
            raise ValueError(
                "Cannot migrate users: extra must be a JSON object"
            ) from None
        if not isinstance(extra, dict):
            raise ValueError("Cannot migrate users: extra must be a JSON object")
        for key, value in (("extra1", user["email"]), ("extra2", user["password"])):
            if key in extra and extra[key] != value:
                raise ValueError(f"Cannot migrate users: conflicting {key} value")
            extra[key] = value
        # Preserve stored text through LNbits' HTML-stripping parameter handling.
        encoded_extra = (
            json.dumps(extra).replace("<", "\\u003c").replace("&", "\\u0026")
        )
        updates.append({"extra": encoded_extra, "user_id": user["id"]})

    for update in updates:
        await db.execute(
            "UPDATE usermanager.users SET extra = :extra WHERE id = :user_id",
            update,
        )

    # Step 2: Attempt SQLite-style migration (table recreation)
    try:
        await db.execute("PRAGMA foreign_keys=off;")
        await db.execute(
            """
            CREATE TABLE usermanager.users_new (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                admin TEXT NOT NULL,
                extra TEXT
            );
            """
        )
        await db.execute(
            """
            INSERT INTO usermanager.users_new (id, name, admin, extra)
            SELECT id, name, admin, extra FROM usermanager.users;
            """
        )
        await db.execute("DROP TABLE usermanager.users;")
        await db.execute("ALTER TABLE usermanager.users_new RENAME TO users;")
        await db.execute("PRAGMA foreign_keys=on;")
    except Exception:
        await db.execute("COMMIT")
        # Step 3: If PRAGMA fails, assume PostgreSQL and drop columns directly
        await db.execute("ALTER TABLE usermanager.users DROP COLUMN email;")
        await db.execute("ALTER TABLE usermanager.users DROP COLUMN password;")
