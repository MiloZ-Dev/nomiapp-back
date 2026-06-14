"""Script de inicialización (seed).

Crea las tablas (si no existen), aplica ajustes de esquema para entornos ya
existentes (nueva columna ``usuarios.empresa_id`` y nuevo valor de enum
``admin_empresa``) y crea el usuario super admin inicial.

Uso:
    python -m app.seed            # crea/actualiza esquema + super admin
    python -m app.seed --reset    # DROP de todas las tablas y recrea (¡borra datos!)
"""

import asyncio
import sys

from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.base import Base  # importa la metadata con todos los modelos
from app.db.session import AsyncSessionLocal, engine
from app.models.usuario import RolEnum, Usuario

ADMIN_EMAIL = "admin@nomiapp.co"
ADMIN_PASSWORD = "Admin2025*"
ADMIN_NOMBRE = "Super Admin"


async def reset_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("[seed] Tablas eliminadas (--reset).")


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema_updates() -> None:
    """Ajustes idempotentes para bases de datos PostgreSQL ya existentes."""
    if not engine.dialect.name.startswith("postgresql"):
        return

    # 1) Agregar valor 'admin_empresa' al enum rol_enum (en AUTOCOMMIT).
    async with engine.connect() as conn:
        autocommit = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await autocommit.execute(
            text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rol_enum') THEN "
                "  IF NOT EXISTS ("
                "    SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "    WHERE t.typname = 'rol_enum' AND e.enumlabel = 'admin_empresa'"
                "  ) THEN ALTER TYPE rol_enum ADD VALUE 'admin_empresa'; END IF; "
                "END IF; END $$;"
            )
        )

    # 2) Agregar columna usuarios.empresa_id si la tabla existe y no la tiene.
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE IF EXISTS usuarios "
                "ADD COLUMN IF NOT EXISTS empresa_id UUID "
                "REFERENCES empresas(id) ON DELETE CASCADE"
            )
        )
    print("[seed] Ajustes de esquema aplicados (empresa_id / admin_empresa).")


async def create_super_admin() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(Usuario).where(Usuario.email == ADMIN_EMAIL)
        )
        if existing.scalar_one_or_none() is not None:
            print(f"[seed] El usuario {ADMIN_EMAIL} ya existe. Nada que hacer.")
            return

        admin = Usuario(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            nombre=ADMIN_NOMBRE,
            rol=RolEnum.super_admin,
            empresa_id=None,
            activo=True,
        )
        db.add(admin)
        await db.commit()
        print(f"[seed] Super admin creado: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


async def main() -> None:
    reset = "--reset" in sys.argv

    if reset:
        await reset_tables()

    print("[seed] Creando tablas...")
    await create_tables()

    if not reset:
        await ensure_schema_updates()

    print("[seed] Creando super admin...")
    await create_super_admin()

    await engine.dispose()
    print("[seed] Listo.")


if __name__ == "__main__":
    asyncio.run(main())
