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
    users = await db.fetchall("SELECT id, email, password FROM usermanager.users")

    for user in users:
        user_id, email, password = user
        extra = json.dumps({"extra1": email, "extra2": password})
        await db.execute(
            "UPDATE usermanager.users SET extra = :extra WHERE id = :user_id",
            {"extra": extra, "user_id": user_id},
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
        # Step 3: If PRAGMA fails, assume PostgreSQL and drop columns directly
        await db.execute("ALTER TABLE usermanager.users DROP COLUMN email;")
        await db.execute("ALTER TABLE usermanager.users DROP COLUMN password;")
