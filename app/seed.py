"""Initialization script (seed).

Creates the tables (if they don't exist), applies schema adjustments for
existing environments (new ``users.company_id`` column and new ``company_admin``
enum value) and creates the initial super admin user.

Usage:
    python -m app.seed            # create/update schema + super admin
    python -m app.seed --reset    # DROP all tables and recreate (deletes data!)
"""

import asyncio
import sys

from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.base import Base  # imports the metadata with all models
from app.db.session import AsyncSessionLocal, engine
from app.models.user import RoleEnum, User

ADMIN_EMAIL = "admin@nomiapp.co"
ADMIN_PASSWORD = "Admin2025*"
ADMIN_NAME = "Super Admin"


async def reset_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("[seed] Tables dropped (--reset).")


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema_updates() -> None:
    """Idempotent adjustments for existing PostgreSQL databases."""
    if not engine.dialect.name.startswith("postgresql"):
        return

    # 1) Add the 'company_admin' value to role_enum (in AUTOCOMMIT).
    async with engine.connect() as conn:
        autocommit = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await autocommit.execute(
            text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_enum') THEN "
                "  IF NOT EXISTS ("
                "    SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "    WHERE t.typname = 'role_enum' AND e.enumlabel = 'company_admin'"
                "  ) THEN ALTER TYPE role_enum ADD VALUE 'company_admin'; END IF; "
                "END IF; END $$;"
            )
        )

    # 2) Add the users.company_id column if the table exists and lacks it.
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE IF EXISTS users "
                "ADD COLUMN IF NOT EXISTS company_id UUID "
                "REFERENCES companies(id) ON DELETE CASCADE"
            )
        )
    print("[seed] Schema adjustments applied (company_id / company_admin).")


async def create_super_admin() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        if existing.scalar_one_or_none() is not None:
            print(f"[seed] User {ADMIN_EMAIL} already exists. Nothing to do.")
            return

        admin = User(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            name=ADMIN_NAME,
            role=RoleEnum.super_admin,
            company_id=None,
            active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"[seed] Super admin created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


async def main() -> None:
    reset = "--reset" in sys.argv

    if reset:
        await reset_tables()

    print("[seed] Creating tables...")
    await create_tables()

    if not reset:
        await ensure_schema_updates()

    print("[seed] Creating super admin...")
    await create_super_admin()

    await engine.dispose()
    print("[seed] Done.")


if __name__ == "__main__":
    asyncio.run(main())
